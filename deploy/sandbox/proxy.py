"""Per-task CONNECT gateway. Exact hosts, public addresses and pinned TCP peers only."""

import ipaddress
import select
import socket
import socketserver
import sys
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
            address = public_addresses(host)[0]
            with socket.create_connection((address, 443), timeout=5) as upstream:
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


if __name__ == "__main__":
    with Server(("0.0.0.0", 3128), Gateway) as server:
        server.domains = frozenset(sys.argv[1:])
        server.serve_forever()
