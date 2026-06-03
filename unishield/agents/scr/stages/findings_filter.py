"""Two-stage false positive filter for SCR findings."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from unishield.infrastructure.model_router import ModelRouter, ProviderUnavailableError


class HardExclusionRules:
    """Pre-compiled regex patterns for fast first-pass false positive removal."""

    DOS_PATTERNS = [
        re.compile(r"\bdenial of service\b", re.IGNORECASE),
        re.compile(r"\bresource exhaustion\b", re.IGNORECASE),
        re.compile(r"\binfinite loop\b", re.IGNORECASE),
    ]
    RATE_LIMIT_PATTERNS = [
        re.compile(r"\bmissing rate limit\b", re.IGNORECASE),
        re.compile(r"\bunlimited requests\b", re.IGNORECASE),
        re.compile(r"\bimplement rate limit\b", re.IGNORECASE),
    ]
    RESOURCE_PATTERNS = [
        re.compile(r"\bresource leak\b", re.IGNORECASE),
        re.compile(r"\bunclosed resource\b", re.IGNORECASE),
        re.compile(r"\bmemory leak\b", re.IGNORECASE),
        re.compile(r"\bconnection leak\b", re.IGNORECASE),
    ]
    OPEN_REDIRECT_PATTERNS = [
        re.compile(r"\bopen redirect\b", re.IGNORECASE),
        re.compile(r"\bunvalidated redirect\b", re.IGNORECASE),
    ]
    REGEX_PATTERNS = [
        re.compile(r"\bregex injection\b", re.IGNORECASE),
        re.compile(r"\bregex denial of service\b", re.IGNORECASE),
        re.compile(r"\breDoS\b", re.IGNORECASE),
    ]
    MEMORY_SAFETY_PATTERNS = [
        re.compile(r"\bbuffer overflow\b", re.IGNORECASE),
        re.compile(r"\bout of bounds\b", re.IGNORECASE),
        re.compile(r"\buse after free\b", re.IGNORECASE),
        re.compile(r"\bnull pointer dereference\b", re.IGNORECASE),
        re.compile(r"\binteger overflow\b", re.IGNORECASE),
    ]
    C_CPP_EXTENSIONS = {".c", ".cc", ".cpp", ".h", ".hpp"}
    SSRF_PATTERNS = [
        re.compile(r"\bssrf\b", re.IGNORECASE),
        re.compile(r"\bserver.?side request forgery\b", re.IGNORECASE),
    ]
    HTML_EXTENSIONS = {".html", ".htm", ".css"}
    BFSI_NOISE_PATTERNS = [
        re.compile(r"\bweak random.*logging\b", re.IGNORECASE),
        re.compile(r"\binsecure deserialization.*test\b", re.IGNORECASE),
        re.compile(r"\bmissing.*csrf.*internal api\b", re.IGNORECASE),
    ]

    @classmethod
    def get_exclusion_reason(cls, finding: dict, file_path: str = "") -> Optional[str]:
        path = file_path or finding.get("file_path", "")
        ext = "." + path.split(".")[-1].lower() if "." in path else ""
        description = (
            f"{finding.get('description', '')} "
            f"{finding.get('title', '')} "
            f"{finding.get('category', '')}"
        ).lower()

        for patterns, reason in [
            (cls.DOS_PATTERNS, "Denial of service / resource exhaustion (excluded)"),
            (cls.RATE_LIMIT_PATTERNS, "Rate limiting recommendation (excluded)"),
            (cls.RESOURCE_PATTERNS, "Resource management finding (not security-critical)"),
            (cls.OPEN_REDIRECT_PATTERNS, "Open redirect (low impact, excluded)"),
            (cls.REGEX_PATTERNS, "Regex injection / ReDoS (excluded)"),
            (cls.BFSI_NOISE_PATTERNS, "BFSI noise pattern (excluded)"),
        ]:
            for pattern in patterns:
                if pattern.search(description):
                    return reason

        if ext == ".md":
            return "Finding in Markdown file (documentation, excluded)"

        if ext not in cls.C_CPP_EXTENSIONS:
            for pattern in cls.MEMORY_SAFETY_PATTERNS:
                if pattern.search(description):
                    return f"Memory safety finding in non-C/C++ file ({ext or 'unknown'}), excluded"

        if ext in cls.HTML_EXTENSIONS:
            for pattern in cls.SSRF_PATTERNS:
                if pattern.search(description):
                    return "SSRF finding in HTML file (client-side, excluded)"

        return None


@dataclass
class FilterResult:
    keep: bool
    confidence_score: float
    justification: str
    excluded_by: Optional[str] = None


@dataclass
class FilterStats:
    total_input: int = 0
    hard_excluded: int = 0
    ai_excluded: int = 0
    kept: int = 0
    ai_filter_failed: int = 0
    runtime_seconds: float = 0.0
    hard_exclusion_reasons: list = field(default_factory=list)


class FindingsFilter:
    """Two-stage false positive filter — hard exclusion then AI confidence scoring."""

    def __init__(
        self,
        model_router: ModelRouter,
        use_hard_exclusions: bool = True,
        use_ai_filtering: bool = True,
        confidence_threshold: float = 0.80,
        custom_instructions: Optional[str] = None,
    ) -> None:
        self.model_router = model_router
        self.use_hard_exclusions = use_hard_exclusions
        self.use_ai_filtering = use_ai_filtering
        self.confidence_threshold = confidence_threshold
        self.custom_instructions = custom_instructions

    async def filter_findings(
        self,
        findings: list[dict],
        scan_id: str,
        client_id: str,
    ) -> tuple[list[dict], FilterStats]:
        stats = FilterStats(total_input=len(findings))
        start = datetime.now(UTC)

        if not findings:
            return [], stats

        after_hard: list[dict] = []
        if self.use_hard_exclusions:
            for finding in findings:
                file_path = finding.get("file_path", "")
                reason = HardExclusionRules.get_exclusion_reason(finding, file_path)
                if reason:
                    finding["_excluded_by"] = "hard_exclusion"
                    finding["_exclusion_reason"] = reason
                    stats.hard_excluded += 1
                    stats.hard_exclusion_reasons.append(reason)
                else:
                    after_hard.append(finding)
        else:
            after_hard = list(findings)

        kept: list[dict] = []
        if self.use_ai_filtering and after_hard:
            semaphore = asyncio.Semaphore(5)

            async def score_one(finding: dict) -> Optional[dict]:
                async with semaphore:
                    try:
                        result = await self._ai_score_finding(finding, client_id)
                        finding["_confidence_score"] = result.confidence_score
                        finding["_ai_justification"] = result.justification
                        if result.keep:
                            finding["false_positive_score"] = 1.0 - result.confidence_score
                            return finding
                        finding["_excluded_by"] = "ai_filter"
                        finding["_exclusion_reason"] = result.justification
                        stats.ai_excluded += 1
                        return None
                    except Exception as exc:
                        stats.ai_filter_failed += 1
                        finding["false_positive_score"] = 0.0
                        finding["_ai_filter_error"] = str(exc)
                        return finding

            results = await asyncio.gather(*[score_one(f) for f in after_hard])
            kept = [r for r in results if r is not None]
        else:
            kept = after_hard

        stats.kept = len(kept)
        stats.runtime_seconds = (datetime.now(UTC) - start).total_seconds()
        return kept, stats

    async def _ai_score_finding(self, finding: dict, client_id: str) -> FilterResult:
        custom = f"\n{self.custom_instructions}" if self.custom_instructions else ""
        prompt = f"""You are a security engineer reviewing a potential vulnerability for BFSI client {client_id}.
Finding: {finding}
Assign confidence 0.0-1.0 of actual exploitability. Respond JSON only:
{{"confidence": 0.0, "keep": true, "reason": ""}}{custom}"""

        try:
            data = await self.model_router.score_json(prompt, client_id)
            confidence = float(data.get("confidence", 0.5))
            keep = data.get("keep", confidence >= self.confidence_threshold)
            if confidence < self.confidence_threshold:
                keep = False
            return FilterResult(
                keep=bool(keep),
                confidence_score=confidence,
                justification=str(data.get("reason", "")),
            )
        except ProviderUnavailableError:
            return FilterResult(keep=True, confidence_score=0.5, justification="AI unavailable — fail-open")
