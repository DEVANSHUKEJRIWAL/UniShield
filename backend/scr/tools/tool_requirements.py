"""Required external tools for full SCR pipeline."""

from __future__ import annotations

import logging
import shutil

logger = logging.getLogger(__name__)

REQUIRED_TOOLS = ("gitleaks", "syft", "grype")
INSTALL_HINT = "Run: ./scripts/install-scr-tools.sh"


def validate_required_tools(*, strict: bool = True) -> None:
    """Fail loudly if mandatory scan tools are missing from PATH."""
    missing = [name for name in REQUIRED_TOOLS if not shutil.which(name)]
    if missing and strict:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"{joined} not found — install before running scan. {INSTALL_HINT}"
        )
    if missing:
        logger.warning("SCR tools missing (non-strict): %s", ", ".join(missing))
    else:
        logger.info("SCR tool check passed: %s", ", ".join(REQUIRED_TOOLS))


def check_tool(name: str) -> bool:
    return bool(shutil.which(name))
