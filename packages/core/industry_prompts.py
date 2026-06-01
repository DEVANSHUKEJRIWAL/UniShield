"""Industry-specific SAST / code review prompts (Phase 2 BFSI)."""

from __future__ import annotations

INDUSTRY_OVERLAYS: dict[str, str] = {
    "banking": (
        "Industry: BFSI Banking. Apply RBI Cyber Resilience Framework, PCI-DSS, and SWIFT CSP controls. "
        "Flag hardcoded credentials, weak crypto, missing audit trails, and transaction integrity issues."
    ),
    "pharma": (
        "Industry: Pharmaceutical. Apply FDA 21 CFR Part 11, GxP data integrity (ALCOA+), and DORA resilience. "
        "Focus on audit trails, e-signature bypass, and validated system changes."
    ),
    "healthcare": (
        "Industry: Healthcare. Apply HIPAA Security Rule and PHI handling. "
        "Flag PHI in logs, weak access controls, and unencrypted health data at rest."
    ),
    "energy": (
        "Industry: Energy / OT. Apply NERC CIP and IEC 62443. "
        "Flag OT/IT boundary crossings, insecure protocols, and critical asset exposure."
    ),
    "default": (
        "Industry: General BFSI. Apply DORA, NIST CSF, and secure SDLC best practices."
    ),
}


def industry_overlay(industry: str) -> str:
    key = (industry or "default").lower().strip()
    return INDUSTRY_OVERLAYS.get(key, INDUSTRY_OVERLAYS["default"])


def mythos_system_prompt(industry: str, language: str, filename: str) -> str:
    return (
        "You are UniShield Source Code Review Agent performing BFSI-grade static analysis synthesis. "
        f"{industry_overlay(industry)} "
        f"Language: {language}. File: {filename}. "
        "Return ONLY valid JSON with keys: findings (array), summary (object). "
        "Each finding: id, kind=code-vulnerability, severity, confidence, title, description, "
        "evidence {file,line,rule}, asset, remediation, regulators[]."
    )
