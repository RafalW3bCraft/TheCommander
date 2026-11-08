"""Offline adversarial contracts. These tests do not establish live containment."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from commander.errors import DomainError
from commander.providers import Provider
from commander.sandbox.contracts import BrowserPlan, CodePlan, Decision, domain_name, safe_url
from commander.sandbox.runner import DockerRunner
from commander.settings import Settings, inference_endpoint


def config(**overrides):
    return Settings(
        _env_file=None,
        database_url="postgresql://unused/unused",
        encryption_key=Fernet.generate_key().decode(),
        bootstrap_token="unit-test-bootstrap-at-least-32-characters",
        **overrides,
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1",
        "https://169.254.169.254/latest/meta-data",
        "https://user:password@example.com",
        "https://example.com:444",
        "https://example.com.evil.org",
        "https://example.com\\@evil.org",
        "file:///etc/passwd",
        "data:text/html,hi",
        "https://example.com\n.evil.org",
    ],
)
def test_url_policy_denies_ambiguous_or_unapproved_targets(url):
    with pytest.raises(DomainError):
        safe_url(url, ["example.com"])


def test_public_url_and_exact_domain_validation():
    assert safe_url("https://example.com/form?x=1", ["example.com"]).endswith("x=1")
    assert domain_name("docs.vultr.com") == "docs.vultr.com"
    for host in (
        "localhost",
        "example.local",
        "192.0.2.1",
        "*.example.com",
        "EXAMPLE.COM",
        "a..com",
    ):
        with pytest.raises(ValueError):
            domain_name(host)


def test_structured_plans_cannot_inject_execution_parameters():
    with pytest.raises(ValidationError):
        CodePlan(code="print(1)", explanation="hi", mounts=["/"])
    with pytest.raises(ValidationError):
        BrowserPlan(
            explanation="hi",
            steps=[{"action": "evaluate", "selector": "*", "value": "fetch('/secret')"}],
        )
    with pytest.raises(ValidationError):
        BrowserPlan(
            explanation="hi", steps=[{"action": "click", "selector": "button", "value": "payload"}]
        )
    with pytest.raises(ValidationError):
        Decision(digest="wrong", approve=True)


def test_gateway_rejects_mixed_dns_and_pins_public_addresses():
    spec = importlib.util.spec_from_file_location("sandbox_proxy", Path("deploy/sandbox/proxy.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def resolver(addresses):
        return lambda *args, **kw: [(2, 1, 6, "", (ip, 443)) for ip in addresses]

    for values in (
        ["127.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["93.184.216.34", "10.0.0.1"],
        ["::ffff:127.0.0.1"],
        [],
    ):
        with pytest.raises(ValueError):
            module.public_addresses("example.com", resolver(values))
    assert module.public_addresses("example.com", resolver(["93.184.216.34"])) == ["93.184.216.34"]


def test_vultr_is_additive_and_uses_only_its_fixed_endpoint():
    settings = config(inference_provider="vultr", provider_model="account-model")
    assert inference_endpoint(settings) == "https://api.vultrinference.com/v1"
    assert settings.nebius_api_key == ""
    observed = []

    def handle(request):
        observed.append(request)
        assert request.url.host == "api.vultrinference.com"
        assert json.loads(request.content)["model"] == "account-model"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]}
        )

    assert (
        Provider(settings, httpx.MockTransport(handle)).completion(
            "fictional-vultr-secret", [{"role": "user", "content": "hi"}]
        )[0]["content"]
        == "OK"
    )
    assert len(observed) == 1
    with pytest.raises(DomainError):
        Provider(settings).request("GET", "https://evil.example/v1", "key")


def runner_config(**overrides):
    return SimpleNamespace(sandbox_runtime="runsc", sandbox_timeout_seconds=2, **overrides)


def test_no_docker_means_no_execution_fallback(monkeypatch):
    monkeypatch.setattr("commander.sandbox.runner.shutil.which", lambda _: None)
    with pytest.raises(DomainError, match="unavailable"):
        DockerRunner(runner_config())


def test_docker_profile_never_inherits_secrets_or_mounts(monkeypatch):
    monkeypatch.setattr("commander.sandbox.runner.shutil.which", lambda _: "/usr/bin/docker")
    monkeypatch.setenv("VULTR_API_KEY", "fixture-must-never-enter-sandbox")
    monkeypatch.setenv("DOCKER_HOST", "tcp://attacker.invalid:2375")
    runner = DockerRunner(runner_config())
    flags = runner.flags("job", "none")
    assert "--network" in flags and flags[flags.index("--network") + 1] == "none"
    for required in (
        "--read-only",
        "--cap-drop=ALL",
        "--memory=256m",
        "--pids-limit=128",
        "--security-opt=no-new-privileges:true",
    ):
        assert required in flags
    assert not any(
        "mount" in arg or "privileged" in arg or "host" in arg or "fixture" in arg for arg in flags
    )
    assert "VULTR_API_KEY" not in runner._env() and "DOCKER_HOST" not in runner._env()
    assert "--host=unix:///var/run/docker.sock" in runner._base("/tmp/config")
    browser = runner.flags("job", "internal-job-net", True)
    assert any(arg.startswith("--security-opt=seccomp=") for arg in browser)


def test_capture_bounds_output_timeout_and_cancellation(monkeypatch):
    monkeypatch.setattr("commander.sandbox.runner.shutil.which", lambda _: "/usr/bin/docker")
    runner = DockerRunner(runner_config())
    # Only fixed test programs execute here; production task code uses Docker exclusively.
    result, code, reason = runner._capture(
        [sys.executable, "-c", "print('known-test-output')"], "", lambda: False
    )
    assert code == 0 and reason is None and result["stdout"].strip() == "known-test-output"
    result, _, reason = runner._capture(
        [sys.executable, "-c", "print('x'*200000)"], "", lambda: False
    )
    assert reason == "output_limit" and len(result["stdout"]) <= 128000
    _, _, reason = runner._capture(
        [sys.executable, "-c", "import time; time.sleep(10)"], "", lambda: True
    )
    assert reason == "cancelled"
    runner.settings.sandbox_timeout_seconds = 0.1
    _, _, reason = runner._capture(
        [sys.executable, "-c", "import time; time.sleep(10)"], "", lambda: False
    )
    assert reason == "timeout"


def test_runner_inspects_enforced_limits_and_destroys_resources(monkeypatch):
    monkeypatch.setattr("commander.sandbox.runner.shutil.which", lambda _: "/usr/bin/docker")
    runner = DockerRunner(runner_config(sandbox_code_image="trusted:version"))
    commands = []
    actual = {
        "Id": "fixture-container",
        "Image": "sha256:fixture",
        "Mounts": [],
        "HostConfig": {
            "Runtime": "runsc",
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Memory": 268435456,
            "NanoCpus": 1000000000,
            "PidsLimit": 128,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
        },
        "Config": {"User": "10001:10001"},
        "State": {"ExitCode": 0},
    }

    def control(base, args, **kw):
        commands.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps([actual]).encode())

    monkeypatch.setattr(runner, "_control", control)
    monkeypatch.setattr(
        runner,
        "_capture",
        lambda cmd, payload, cancelled: ({"stdout": "42\n", "stderr": ""}, 0, None),
    )
    result = runner.execute("code", "print(42)")
    assert result["receipt"]["destroyed"] and result["receipt"]["memory_bytes"] == 268435456
    assert commands[-1][0:2] == ["rm", "-f"]
    actual["HostConfig"]["Privileged"] = True
    with pytest.raises(DomainError, match="containment"):
        runner.execute("code", "print(42)")
    assert commands[-1][0:2] == ["rm", "-f"]


def test_browser_requires_host_isolated_gateway_and_cleans_up(monkeypatch):
    monkeypatch.setattr("commander.sandbox.runner.shutil.which", lambda _: "/usr/bin/docker")
    runner = DockerRunner(runner_config())
    commands = []

    def control(base, args, **kw):
        commands.append(args)
        if args[0] == "version":
            output = b"28.1.0"
        elif args[:2] == ["network", "inspect"]:
            output = json.dumps([{"Internal": True, "EnableIPv6": False, "Options": {}}]).encode()
        else:
            output = b""
        return subprocess.CompletedProcess(args, 0, stdout=output)

    monkeypatch.setattr(runner, "_control", control)
    with pytest.raises(DomainError, match="network isolation"):
        runner.execute("browser", "{}")
    creation = next(c for c in commands if c[:2] == ["network", "create"])
    assert "--opt=com.docker.network.bridge.gateway_mode_ipv4=isolated" in creation
    assert "--internal" in creation and "--ipv6=false" in creation
    assert commands[-1][:2] == ["network", "rm"]
