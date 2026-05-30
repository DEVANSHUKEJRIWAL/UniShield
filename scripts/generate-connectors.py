#!/usr/bin/env python3
"""Generate all connector stub implementations."""

from pathlib import Path

CONNECTORS = [
    "splunk", "qradar", "sentinel", "crowdstrike", "sentinelone", "defender",
    "okta", "active_directory", "entra_id", "guardduty", "azure_defender", "gcp_scc",
    "virustotal", "shodan", "dark_web_scraper", "misp", "taxii_client",
    "github", "gitlab", "bitbucket", "nvd_poller", "oracle_av", "sqlserver_audit",
    "pgaudit", "servicenow", "jira", "slack", "pagerduty", "email",
    "splunk_soar", "xsoar", "archer", "metricstream",
]

TEMPLATE = '''"""{name} connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class {cls}(BaseConnector):
    """Integration adapter for {name}."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from {name}."""
        return [
            {{
                "source_vendor": "{name}",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from {name}",
            }}
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {{"status": "queued", "connector": "{name}", "action": action}}
'''


def main() -> None:
    root = Path(__file__).parent.parent / "services" / "connector-registry" / "connectors"
    for name in CONNECTORS:
        cls = "".join(w.capitalize() for w in name.split("_")) + "Connector"
        path = root / f"{name}.py"
        path.write_text(TEMPLATE.format(name=name, cls=cls))
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
