import hashlib
import json
from typing import Any

from commander.errors import DomainError

DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "engineering-briefing",
        "name": "Engineering briefing",
        "purpose": "Read selected repository activity and approved research sources; save a cited briefing.",
        "tools": ["github_read", "search", "save_note"],
        "example": "Brief me on project reliability; cite the evidence.",
    },
    {
        "id": "research-to-action",
        "name": "Research to action",
        "purpose": "Research a problem and prepare an exact GitHub issue for your approval.",
        "tools": ["github_read", "search", "propose_issue"],
        "example": "Research safer retry handling and propose an issue.",
    },
    {
        "id": "follow-through",
        "name": "Follow-through",
        "purpose": "Perform a scheduled review using saved preferences and save a persistent next-step note.",
        "tools": ["save_note"],
        "example": "Write my next engineering step using my saved preferences.",
    },
]
for item in DEFINITIONS:
    item.update(
        {
            "version": "1.0.0",
            "input_schema": {"prompt": "nonempty text, max 8000 characters"},
            "output_schema": {
                "result": "text",
                "evidence": "source links",
                "receipt": "note or approved issue",
            },
            "source_restrictions": "Configured repository and connection domain allowlist only",
            "max_steps": 5,
            "max_seconds": 180,
        }
    )
    item["hash"] = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()


def definition(skill):
    if skill == "conversation":
        return {
            "id": "conversation",
            "version": "1.0.0",
            "hash": "conversation-v1",
            "tools": ["github_read", "search", "save_note", "propose_issue"],
        }
    for item in DEFINITIONS:
        if item["id"] == skill:
            return item
    raise DomainError("Unknown or retired skill; choose an available skill", 422, "unknown_skill")
