"""Per-task CONNECT gateway. Exact hosts, public addresses and pinned TCP peers only."""

import ipaddress
import select
import socket
import socketserver
import sys
import threading
import time


def public_addresses(host, resolver=socket.getaddrinfo):
    rows = resolver(host, 443, type=socket.SOCK_STREAM)
    addresses = sorted({r[4][0] for r in rows})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("Private, metadata, mixed and non-global DNS answers are denied")
    return addresses


class Gateway(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        line = self.rfile.readline(4097)
        if len(line) > 4096:
            return
        parts = line.decode("ascii", "replace").strip().split()
        if len(parts) != 3 or parts[0] != "CONNECT" or parts[2] != "HTTP/1.1":
            self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            return
        host, sep, port = parts[1].rpartition(":")
        if not sep or port != "443" or host not in self.server.domains:
            self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            return
        size = len(line)
        while True:
            header = self.rfile.readline(4097)
            size += len(header)
            if not header or size > 8192:
                return
            if header == b"\r\n":
                break
        try:
            # Resolve once, validate ALL answers, connect to a numeric address.
            upstream = None
            for address in self.server.pinned_peers[host]:
                try:
                    upstream = socket.create_connection((address, 443), timeout=5)
                    break
                except OSError:
                    continue
            if upstream is None:
                return
            with upstream:
                self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                self.wfile.flush()
                deadline, transferred = time.monotonic() + 120, 0
                while time.monotonic() < deadline and transferred < 16_000_000:
                    ready, _, _ = select.select([self.connection, upstream], [], [], 1)
                    for source in ready:
                        data = source.recv(16384)
                        if not data:
                            return
                        transferred += len(data)
                        (upstream if source is self.connection else self.connection).sendall(data)
        except (OSError, ValueError):
            return


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 16
    slots = threading.BoundedSemaphore(16)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def pinned_peers(arguments):
    """Accept only public numeric peers resolved and reviewed by the trusted runner."""
    result = {}
    for item in arguments:
        domain, separator, address = item.partition("=")
        if not separator or not domain or any(c in domain for c in "/:@\\"):
            raise ValueError("Invalid pinned proxy authority")
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Non-public pinned proxy address")
        result.setdefault(domain, []).append(str(ip))
    if not result:
        raise ValueError("Pinned proxy peers are required")
    return result


if __name__ == "__main__":
    try:
        peers = pinned_peers(sys.argv[1:])
    except ValueError:
        raise SystemExit("Invalid pinned proxy configuration") from None
    with Server(("0.0.0.0", 3128), Gateway) as server:
        server.domains = frozenset(peers)
        server.pinned_peers = peers
        server.serve_forever()
