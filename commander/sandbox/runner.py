"""Docker-only boundary. No shell, host task execution, mounts or fallback runtime."""

import hashlib
import json
import os
import selectors
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from commander.errors import DomainError


class DockerRunner:
    def __init__(self, settings):
        self.settings = settings
        self.docker = shutil.which("docker")
        if not self.docker:
            raise DomainError("Docker execution is unavailable", 503, "sandbox_unavailable")

    def _env(self):
        # No inherited provider keys, CLI endpoint selectors or proxy credentials.
        return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/tmp", "LANG": "C.UTF-8"}

    def _base(self, config):
        return [self.docker, "--host=unix:///var/run/docker.sock", "--config", config]

    def _control(self, base, args, *, check=True):
        result = subprocess.run(base + args, env=self._env(), capture_output=True, timeout=15)
        if check and result.returncode:
            raise DomainError(
                "Docker control operation failed; inspect runner diagnostics",
                503,
                "sandbox_unavailable",
            )
        return result

    def flags(self, name, network, browser=False):
        flags = [
            "--name",
            name,
            "--label",
            "commander.sandbox=true",
            "--runtime",
            self.settings.sandbox_runtime,
            "--network",
            network,
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--user=10001:10001",
            "--memory=" + ("768m" if browser else "256m"),
            "--memory-swap=" + ("768m" if browser else "256m"),
            "--cpus=1",
            "--pids-limit=128",
            "--ulimit=nofile=256:256",
            "--ulimit=fsize=8388608:8388608",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777",
            "--shm-size=64m",
            "--workdir=/tmp",
            "--log-driver=none",
            "--env=HOME=/tmp",
            "--env=PYTHONDONTWRITEBYTECODE=1",
        ]

        if browser:
            profile = Path(__file__).resolve().parents[2] / "deploy/sandbox/seccomp-browser.json"
            flags.append("--security-opt=seccomp=" + str(profile))
        return flags

    def reap(self):
        """Remove only labelled stale resources; never replay a recovered task."""
        with tempfile.TemporaryDirectory(prefix="commander-reap-") as config:
            base = self._base(config)
            for resource in ("container", "network"):
                args = ["ps", "-aq"] if resource == "container" else ["network", "ls", "-q"]
                found = self._control(base, args + ["--filter", "label=commander.sandbox=true"])
                for identifier in found.stdout.decode().split():
                    result = self._control(base, [resource, "inspect", identifier], check=False)
                    if result.returncode:
                        continue
                    created = json.loads(result.stdout)[0]["Created"]
                    age = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(created.replace("Z", "+00:00"))
                    ).total_seconds()
                    if age > 600:
                        command = (
                            ["rm", "-f", identifier]
                            if resource == "container"
                            else ["network", "rm", identifier]
                        )
                        self._control(base, command, check=False)

    def _capture(self, cmd, payload, cancelled):
        # Bound bytes while streaming, rather than communicate() with unbounded output.
        input_file = tempfile.TemporaryFile()
        input_file.write(payload.encode())
        input_file.seek(0)
        proc = subprocess.Popen(
            cmd, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self._env()
        )
        output = {"stdout": bytearray(), "stderr": bytearray()}
        deadline = time.monotonic() + self.settings.sandbox_timeout_seconds
        reason = None
        try:
            assert proc.stdout and proc.stderr
            with selectors.DefaultSelector() as selector:
                for stream, label in ((proc.stdout, "stdout"), (proc.stderr, "stderr")):
                    selector.register(stream, selectors.EVENT_READ, label)
                while selector.get_map():
                    if time.monotonic() >= deadline or cancelled():
                        reason = "cancelled" if cancelled() else "timeout"
                        break
                    for selected, _ in selector.select(0.1):
                        data = os.read(selected.fd, 8192)
                        if not data:
                            selector.unregister(selected.fileobj)
                            continue
                        output[selected.data].extend(data)
                        if sum(map(len, output.values())) > 128000:
                            reason = "output_limit"
                            break
                    if reason:
                        break
            if not reason:
                proc.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            reason = "timeout"
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
            input_file.close()
            for output_stream in (proc.stdout, proc.stderr):
                if output_stream:
                    output_stream.close()
        return (
            {k: bytes(v[:128000]).decode("utf-8", "replace") for k, v in output.items()},
            proc.returncode,
            reason,
        )

    def execute(self, kind, payload, *, cancelled=lambda: False):
        name = "commander-job-" + uuid.uuid4().hex
        network = name + "-net"
        proxy = name + "-proxy"
        started = time.monotonic()
        cleanup = False
        result = None
        with tempfile.TemporaryDirectory(prefix="commander-docker-") as config:
            base = self._base(config)
            try:
                net = "none"
                network_policy = None
                if kind == "browser":
                    version = self._control(base, ["version", "--format", "{{.Server.Version}}"])
                    if int(version.stdout.decode().strip().split(".")[0]) < 28:
                        raise DomainError(
                            "Browser isolation requires Docker Engine 28 or newer",
                            503,
                            "sandbox_unavailable",
                        )
                    self._control(
                        base,
                        [
                            "network",
                            "create",
                            "--internal",
                            "--ipv6=false",
                            "--opt=com.docker.network.bridge.gateway_mode_ipv4=isolated",
                            "--label",
                            "commander.sandbox=true",
                            network,
                        ],
                    )
                    network_policy = json.loads(
                        self._control(base, ["network", "inspect", network]).stdout
                    )[0]
                    if (
                        not network_policy["Internal"]
                        or network_policy["EnableIPv6"]
                        or network_policy["Options"].get(
                            "com.docker.network.bridge.gateway_mode_ipv4"
                        )
                        != "isolated"
                    ):
                        raise DomainError(
                            "Browser network isolation was not enforced", 503, "containment_failed"
                        )
                    net = network
                    self._control(
                        base,
                        [
                            "create",
                            "--pull=never",
                            *self.flags(proxy, "bridge"),
                            self.settings.sandbox_proxy_image,
                            *self.settings.sandbox_browser_domains,
                        ],
                    )
                    self._control(base, ["network", "connect", "--alias", "egress", network, proxy])
                    self._control(base, ["start", proxy])
                image = (
                    self.settings.sandbox_browser_image
                    if kind == "browser"
                    else self.settings.sandbox_code_image
                )
                program = (
                    ["python", "/opt/commander/browser.py"]
                    if kind == "browser"
                    else ["python", "-I", "-"]
                )
                cmd = base + [
                    "run",
                    "--pull=never",
                    "-i",
                    *self.flags(name, net, kind == "browser"),
                    image,
                    "timeout",
                    "--signal=KILL",
                    str(self.settings.sandbox_timeout_seconds),
                    *program,
                ]
                streams, exit_code, reason = self._capture(cmd, payload, cancelled)
                inspect = self._control(base, ["inspect", name], check=False)
                actual = json.loads(inspect.stdout)[0] if inspect.returncode == 0 else None
                if not actual:
                    raise DomainError(
                        "Sandbox did not start; verify image and runtime",
                        503,
                        "sandbox_unavailable",
                    )
                host = actual["HostConfig"]
                state = actual["State"]
                receipt = {
                    "container_id": actual["Id"],
                    "image_id": actual["Image"],
                    "runtime": host["Runtime"],
                    "network": host["NetworkMode"],
                    "network_policy": None
                    if network_policy is None
                    else {
                        "internal": network_policy["Internal"],
                        "ipv6": network_policy["EnableIPv6"],
                        "gateway_mode": network_policy["Options"].get(
                            "com.docker.network.bridge.gateway_mode_ipv4"
                        ),
                    },
                    "read_only": host["ReadonlyRootfs"],
                    "memory_bytes": host["Memory"],
                    "nano_cpus": host["NanoCpus"],
                    "pids_limit": host["PidsLimit"],
                    "cap_drop": host["CapDrop"],
                    "security_opt": host["SecurityOpt"],
                    "mounts": actual.get("Mounts", []),
                    "user": actual["Config"]["User"],
                    "oom_killed": state.get("OOMKilled", False),
                    "exit_code": state.get("ExitCode", exit_code),
                    "stop_reason": reason,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "stdout_sha256": hashlib.sha256(streams["stdout"].encode()).hexdigest(),
                    "stderr_sha256": hashlib.sha256(streams["stderr"].encode()).hexdigest(),
                }
                if (
                    not receipt["read_only"]
                    or host.get("Binds")
                    or host.get("Privileged")
                    or any(m.get("Type") != "tmpfs" for m in receipt["mounts"])
                    or receipt["memory_bytes"] != (805306368 if kind == "browser" else 268435456)
                    or receipt["runtime"] != self.settings.sandbox_runtime
                    or receipt["network"] != net
                    or receipt["nano_cpus"] != 1000000000
                    or receipt["pids_limit"] != 128
                    or receipt["user"] != "10001:10001"
                    or "ALL" not in [c.upper() for c in (receipt["cap_drop"] or [])]
                    or "no-new-privileges:true" not in receipt["security_opt"]
                ):
                    raise DomainError(
                        "Docker did not enforce containment policy", 503, "containment_failed"
                    )
                result = {**streams, "receipt": receipt}
            finally:
                removed = self._control(base, ["rm", "-f", name], check=False)
                cleanup = removed.returncode == 0
                if kind == "browser":
                    p = self._control(base, ["rm", "-f", proxy], check=False)
                    n = self._control(base, ["network", "rm", network], check=False)
                    cleanup = cleanup and p.returncode == 0 and n.returncode == 0
            if result is not None:
                result["receipt"]["destroyed"] = cleanup
                if not cleanup:
                    raise DomainError(
                        "Sandbox cleanup failed; operator intervention required",
                        503,
                        "cleanup_failed",
                    )
                return result
        raise DomainError("Sandbox execution failed", 503, "sandbox_unavailable")
