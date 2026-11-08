"""Modes restrict skill permissions; choosing a mode never grants a new tool."""

from commander.errors import DomainError
from commander.skills import definition

MODE_TOOLS = {
    "ask": frozenset(),
    "plan": frozenset({"github_read", "search"}),
    "research": frozenset({"github_read", "search"}),
    "build": frozenset(),
    "review": frozenset(),
    "automate": frozenset({"github_read", "search", "save_note", "propose_issue"}),
}


def validate(mode, skill):
    if mode in ("build", "review"):
        raise DomainError(
            "Isolated coding execution is not configured and verified",
            409,
            "capability_unavailable",
        )
    if mode not in MODE_TOOLS:
        raise DomainError("Unsupported execution mode", 422, "invalid_mode")
    if mode != "automate" and skill != "conversation":
        raise DomainError(
            "Choose Automate to run a workflow; other modes use conversation", 422, "invalid_mode"
        )


def permitted(skill, mode="automate"):
    validate(mode, skill)
    return [name for name in definition(skill)["tools"] if name in MODE_TOOLS[mode]]
