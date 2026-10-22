import json
from pathlib import Path

from cryptography.fernet import Fernet

from commander.api import create_app
from commander.settings import Settings

settings = Settings(
    _env_file=None,
    database_url="postgresql://unused/unused",
    encryption_key=Fernet.generate_key().decode(),
    bootstrap_token="schema-generation-only-no-runtime-token",
)
Path("docs/openapi.json").write_text(json.dumps(create_app(settings).openapi(), indent=2) + "\n")
