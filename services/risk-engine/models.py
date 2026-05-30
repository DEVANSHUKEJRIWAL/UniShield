"""12-dimension risk scoring engine."""

from datetime import datetime

from pydantic import BaseModel, Field


class RiskScore(BaseModel):
    """Multi-dimensional risk score for a security finding."""

    finding_id: str
    client_id: str
    timestamp: datetime

    # 12 dimensions (0.0 – 1.0 each)
    exploitability: float = Field(ge=0.0, le=1.0)
    cvss_base: float = Field(ge=0.0, le=1.0)
    business_criticality: float = Field(ge=0.0, le=1.0)
    regulatory_obligation: float = Field(ge=0.0, le=1.0)
    blast_radius: float = Field(ge=0.0, le=1.0)
    data_sensitivity: float = Field(ge=0.0, le=1.0)
    time_to_exploit: float = Field(ge=0.0, le=1.0)
    detection_confidence: float = Field(ge=0.0, le=1.0)
    remediation_complexity: float = Field(ge=0.0, le=1.0)
    compensating_controls: float = Field(ge=0.0, le=1.0)
    active_exploitation: float = Field(ge=0.0, le=1.0)
    compliance_deadline: float = Field(ge=0.0, le=1.0)

    # Computed outputs
    composite_score: float = Field(default=0.0, ge=0.0, le=1.0)
    business_risk_label: str = "Low"
    regulatory_exposure: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)

    model_config = {"strict": True}

    def compute_composite(self, weights: dict[str, float]) -> float:
        """Compute weighted composite score from dimension weights."""
        dimensions = {
            "exploitability": self.exploitability,
            "cvss_base": self.cvss_base,
            "business_criticality": self.business_criticality,
            "regulatory_obligation": self.regulatory_obligation,
            "blast_radius": self.blast_radius,
            "data_sensitivity": self.data_sensitivity,
            "time_to_exploit": self.time_to_exploit,
            "detection_confidence": self.detection_confidence,
            "remediation_complexity": self.remediation_complexity,
            "compensating_controls": self.compensating_controls,
            "active_exploitation": self.active_exploitation,
            "compliance_deadline": self.compliance_deadline,
        }
        total_weight = sum(weights.values()) or 1.0
        score = sum(dimensions[k] * weights.get(k, 0.0) for k in dimensions) / total_weight
        self.composite_score = round(score, 4)
        self.business_risk_label = self._label_from_score(score)
        return self.composite_score

    @staticmethod
    def _label_from_score(score: float) -> str:
        """Map composite score to business risk label."""
        if score >= 0.85:
            return "Critical"
        if score >= 0.65:
            return "High"
        if score >= 0.40:
            return "Medium"
        return "Low"
