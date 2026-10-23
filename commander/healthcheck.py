"""Container readiness probe without shell-dependent inline quoting."""

import urllib.request


def main():
    with urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=3) as response:
        if response.status != 200:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
