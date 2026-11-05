"""Read-only preflight, then explicit opt-in execution of a known containment probe."""

import argparse
import json
import shutil
import subprocess

from commander.settings import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-probe", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    report = {
        "enabled": settings.sandbox_enabled,
        "docker_cli": bool(shutil.which("docker")),
        "text_model_configured": bool(settings.sandbox_model),
        "vision_model_configured": bool(settings.sandbox_vision_model),
        "runtime": settings.sandbox_runtime,
        "browser_domains": settings.sandbox_browser_domains,
    }
    if report["docker_cli"]:
        result = subprocess.run(
            [
                "docker",
                "--host=unix:///var/run/docker.sock",
                "info",
                "--format",
                "{{json .Runtimes}}",
            ],
            capture_output=True,
            timeout=10,
        )
        report["docker_ready"] = result.returncode == 0
        if result.returncode == 0:
            report["runtime_available"] = settings.sandbox_runtime in json.loads(result.stdout)
    print(json.dumps(report, indent=2))
    if args.execute_probe:
        from commander.sandbox.runner import DockerRunner

        result = DockerRunner(settings).execute(
            "code", "import os; assert os.getuid()==10001; print(6*7)"
        )
        print(json.dumps(result, indent=2))
        if result["receipt"]["exit_code"] != 0 or result["stdout"].strip() != "42":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
