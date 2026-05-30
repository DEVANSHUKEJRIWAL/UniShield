"""Compute framework control coverage from findings (Week 8)."""

import json
from pathlib import Path
from typing import Any

_CONTROLS_DIR = Path(__file__).parent / "controls"


def load_framework_controls(framework: str) -> list[dict[str, Any]]:
    """Load control catalog JSON for a framework."""
    key = framework.lower().replace(" ", "_")
    path = _CONTROLS_DIR / f"{key}.json"
    if not path.exists():
        path = _CONTROLS_DIR / "nist_csf_2.json"
    if not path.exists():
        return _default_controls()
    return json.loads(path.read_text())


def _default_controls() -> list[dict[str, Any]]:
    return [
        {"id": "AC-1", "title": "Access Control Policy", "mitre": ["T1078"], "status": "implemented"},
        {"id": "AC-2", "title": "Account Management", "mitre": ["T1078"], "status": "partial"},
        {"id": "IR-4", "title": "Incident Handling", "mitre": ["T1059"], "status": "implemented"},
        {"id": "SI-4", "title": "System Monitoring", "mitre": ["T1046"], "status": "gap"},
    ]


def compute_coverage(
    framework: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive control status from finding MITRE TTPs and severities."""
    controls = load_framework_controls(framework)
    ttps: set[str] = set()
    for f in findings:
        for t in f.get("mitre_ttps", f.get("mitre_ttps_matched", [])):
            ttps.add(str(t).upper())

    scored: list[dict[str, Any]] = []
    implemented = 0
    for ctrl in controls:
        mitre = {str(m).upper() for m in ctrl.get("mitre", [])}
        if mitre & ttps:
            status = "gap" if any(f.get("severity") in ("critical", "high") for f in findings) else "partial"
        else:
            status = ctrl.get("status", "implemented")
        if status == "implemented":
            implemented += 1
        scored.append(
            {
                "id": ctrl["id"],
                "title": ctrl["title"],
                "status": status,
                "mitre": list(mitre),
            }
        )
    coverage_pct = implemented / len(scored) if scored else 0.0
    return {
        "framework": framework,
        "coverage_pct": round(coverage_pct, 2),
        "controls": scored,
        "attck_techniques": sorted(ttps),
    }
