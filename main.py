"""Compatibility launcher for the supported FastAPI release.

The original Flask entrypoint is preserved in Git history; see ADR 004.
Use scripts/start.sh for the complete API, PostgreSQL and worker deployment.
"""

import uvicorn

from commander.api import create_app

# Supports `uvicorn main:create_app --factory` without importing legacy modules.
__all__ = ["create_app"]


if __name__ == "__main__":
    uvicorn.run(
        "commander.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        access_log=False,
    )
