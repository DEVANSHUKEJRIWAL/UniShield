"""Load OpenClaw agent skill definitions from skills/*."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"

AGENT_SKILL_PATHS: dict[str, Path] = {
    "unishield-orchestrator": _SKILLS_ROOT / "unishield-orchestrator" / "SKILL.md",
    "unishield-scr": _SKILLS_ROOT / "unishield-scr" / "SKILL.md",
    "unishield-cma": _SKILLS_ROOT / "unishield-cma" / "SKILL.md",
    "unishield-reporting": _SKILLS_ROOT / "unishield-reporting" / "SKILL.md",
    "unishield-web": _SKILLS_ROOT / "unishield-web" / "SKILL.md",
    "unishield-asm": _SKILLS_ROOT / "unishield-asm" / "SKILL.md",
    "unishield-cloudsec": _SKILLS_ROOT / "unishield-cloudsec" / "SKILL.md",
}


def load_skill(agent_id: str) -> str:
    """Return SKILL.md body for an agent, or empty string if missing."""
    path = AGENT_SKILL_PATHS.get(agent_id)
    if path is None or not path.is_file():
        logger.warning("Skill file missing for agent %s", agent_id)
        return ""
    return path.read_text(encoding="utf-8")


def load_all_skills() -> dict[str, str]:
    return {agent_id: load_skill(agent_id) for agent_id in AGENT_SKILL_PATHS}
