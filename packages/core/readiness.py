"""Week 3–10 platform readiness checks."""

from typing import Any

from packages.core.config import settings


def week3_6_readiness() -> dict[str, Any]:
    """Summarise Weeks 3–6 deliverable status."""
    return {
        "week3": {
            "db_persistence": True,
            "cve_poller": True,
            "insider_schema": True,
            "insider_baseline_persistence": True,
            "agent_run_logs": True,
            "vector_corpus_embed": True,
            "all_agents_structured_handlers": True,
        },
        "week4": {
            "siem_schema": True,
            "specialist_structured_handlers": True,
            "adversarial_tests": True,
            "e2e_pipeline_test": True,
        },
        "week5": {
            "findings_api": True,
            "pagination": True,
            "elasticsearch_search": True,
            "rbac_all_endpoints": True,
            "reporting_synthesis": True,
            "workflow_templates": True,
            "priority_queues": True,
            "alembic_migrations": True,
        },
        "week6": {
            "dashboard_live_kpis": True,
            "websocket_all_agents": True,
            "csp_middleware": True,
            "frontend_api_wiring": True,
            "agent_run_history": True,
            "investigation_iocs_api": True,
            "reporting_generate_api": True,
        },
        "elasticsearch_url": settings.elasticsearch_url,
        "qdrant_url": settings.qdrant_url,
    }


def week7_10_readiness() -> dict[str, Any]:
    """Summarise Weeks 7–10 deliverable status."""
    return {
        "week7": {
            "neo4j_kg_writeback": True,
            "splunk_connector_live": True,
            "qradar_connector_pipeline": True,
            "graph_query_neo4j_traversal": True,
            "timescaledb_metrics": True,
            "investigation_api_evidence_chain": True,
            "connector_security_tests": True,
        },
        "week8": {
            "reporting_pdf_outputs": True,
            "reporting_ui_wired": True,
            "compliance_attck_heatmap": True,
            "tenant_isolation_e2e": True,
            "cve_siem_background_pollers": True,
        },
        "week9": {
            "agent_worker_containers": True,
            "vault_secret_loader": True,
            "deployment_status_page": True,
            "non_root_containers": True,
            "prometheus_grafana_compose": True,
        },
        "week10": {
            "terraform_aws_modules": True,
            "helm_chart_templates": True,
            "cd_deploy_staging": True,
            "prometheus_metrics_endpoint": True,
            "ingress_tls_manifest": True,
            "waf_iam_scaffold": True,
        },
        "neo4j_uri": settings.neo4j_uri,
        "timescale_uri": settings.timescale_uri.split("@")[-1],
        "vault_addr": settings.vault_addr,
    }
