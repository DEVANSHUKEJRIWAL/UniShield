FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sSL https://github.com/gitleaks/gitleaks/releases/download/v8.18.4/gitleaks_8.18.4_linux_x64.tar.gz \
        | tar xz -C /usr/local/bin gitleaks \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
        | sh -s -- -b /usr/local/bin \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash unishield && \
    mkdir -p /app/data /tmp/unishield && \
    chown -R unishield:unishield /app /tmp/unishield

COPY pyproject.toml README.md ./
COPY agents ./agents
COPY packages ./packages
COPY services ./services

RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn pydantic pydantic-settings anthropic redis httpx neo4j sqlalchemy asyncpg \
    && pip install --no-cache-dir semgrep bandit pip-audit

USER unishield
ENV PYTHONUNBUFFERED=1

# Default: run all specialist workers; override with --agent for single agent pod
CMD ["python3", "-m", "agents.worker", "--tenant", "meridian-financial"]
