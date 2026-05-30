-- TimescaleDB metrics hypertables (Week 7)
CREATE TABLE IF NOT EXISTS agent_run_metrics (
    time TIMESTAMPTZ NOT NULL,
    tenant_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alert_volume_metrics (
    time TIMESTAMPTZ NOT NULL,
    tenant_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS api_latency_metrics (
    time TIMESTAMPTZ NOT NULL,
    route TEXT NOT NULL,
    method TEXT NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    status_code INTEGER NOT NULL
);

SELECT create_hypertable('agent_run_metrics', 'time', if_not_exists => TRUE);
SELECT create_hypertable('alert_volume_metrics', 'time', if_not_exists => TRUE);
SELECT create_hypertable('api_latency_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_agent_run_tenant ON agent_run_metrics (tenant_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_alert_volume_tenant ON alert_volume_metrics (tenant_id, time DESC);
