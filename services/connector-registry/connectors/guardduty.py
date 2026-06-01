"""AWS GuardDuty / CSPM connector — live API when credentials present."""

import os
from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class GuarddutyConnector(BaseConnector):
    """Integration adapter for AWS GuardDuty CSPM findings."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull GuardDuty findings or synthesize CSPM events from AWS Security Hub."""
        access_key = self.config.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = self.config.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY")
        region = self.config.get("region") or os.getenv("AWS_REGION", "us-east-1")

        if access_key and secret_key:
            try:
                import boto3

                client = boto3.client(
                    "guardduty",
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                )
                detectors = client.list_detectors()
                events: list[dict[str, Any]] = []
                for detector_id in detectors.get("DetectorIds", [])[:1]:
                    findings = client.list_findings(
                        DetectorId=detector_id,
                        FindingCriteria={"Criterion": {"severity": {"Gte": 4}}},
                        MaxResults=25,
                    )
                    ids = findings.get("FindingIds", [])
                    if ids:
                        details = client.get_findings(DetectorId=detector_id, FindingIds=ids[:10])
                        for f in details.get("Findings", []):
                            events.append(
                                {
                                    "source_vendor": "guardduty",
                                    "source_type": "cspm",
                                    "tenant_id": self.tenant_id,
                                    "severity": f.get("Severity", 5),
                                    "title": f.get("Title", "GuardDuty finding"),
                                    "description": f.get("Description", ""),
                                    "resource": f.get("Resource", {}),
                                    "region": region,
                                    "mock": False,
                                }
                            )
                if events:
                    return events
            except Exception as exc:
                return [
                    {
                        "source_vendor": "guardduty",
                        "source_type": "cspm",
                        "tenant_id": self.tenant_id,
                        "mock": True,
                        "error": str(exc)[:200],
                        "message": "AWS GuardDuty API unreachable — using demo CSPM findings",
                    }
                ]

        return [
            {
                "source_vendor": "guardduty",
                "source_type": "cspm",
                "tenant_id": self.tenant_id,
                "mock": True,
                "severity": "high",
                "title": "S3 bucket public read ACL detected",
                "description": "Demo CSPM finding — configure AWS credentials for live GuardDuty ingest",
                "resource": {"type": "S3Bucket", "name": "meridian-backups"},
                "region": region,
            },
            {
                "source_vendor": "guardduty",
                "source_type": "cspm",
                "tenant_id": self.tenant_id,
                "mock": True,
                "severity": "critical",
                "title": "IAM user with admin policy and no MFA",
                "description": "Demo CSPM finding — run connector ingest with AWS keys",
                "resource": {"type": "IAMUser", "name": "legacy-deploy"},
                "region": region,
            },
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound remediation action (HITL-gated)."""
        return {"status": "queued", "connector": "guardduty", "action": action}
