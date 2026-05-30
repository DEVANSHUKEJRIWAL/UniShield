"""Risk scoring service."""

import json
from pathlib import Path
from typing import Any

from packages.core.redis_client import publish_risk_score
from services.risk_engine.models import RiskScore


class RiskEngine:
    """12-dimension risk scoring engine."""

    def __init__(self) -> None:
        weights_path = Path(__file__).parent / "config" / "weights.v1.json"
        self.weights: dict[str, float] = json.loads(weights_path.read_text())

    def score_finding(self, finding: dict[str, Any]) -> RiskScore:
        """Compute risk score from agent finding."""
        severity_map = {"critical": 0.95, "high": 0.75, "medium": 0.5, "low": 0.25, "info": 0.1}
        base = severity_map.get(finding.get("severity", "medium"), 0.5)
        confidence = float(finding.get("confidence", 0.8))

        score = RiskScore(
            finding_id=finding.get("finding_id", finding.get("id", "unknown")),
            client_id=finding.get("tenant_id", ""),
            timestamp=finding.get("timestamp", __import__("datetime").datetime.now(__import__("datetime").UTC)),
            exploitability=base * 0.9,
            cvss_base=base,
            business_criticality=base * 0.85,
            regulatory_obligation=0.6 if "compliance" in finding.get("type", "") else 0.4,
            blast_radius=base * 0.7,
            data_sensitivity=0.65,
            time_to_exploit=base * 0.8,
            detection_confidence=confidence,
            remediation_complexity=0.4,
            compensating_controls=0.3,
            active_exploitation=0.5 if base > 0.7 else 0.2,
            compliance_deadline=0.45,
            regulatory_exposure=["RBI", "DPDP"] if base > 0.6 else [],
            recommended_actions=finding.get("recommended_actions", ["Investigate", "Contain"]),
        )
        score.compute_composite(self.weights)
        return score

    async def score_and_publish(self, finding: dict[str, Any]) -> RiskScore:
        """Score finding and publish to Redis."""
        score = self.score_finding(finding)
        await publish_risk_score(score.model_dump(mode="json"))
        return score


risk_engine = RiskEngine()
