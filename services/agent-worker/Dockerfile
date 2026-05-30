FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash unishield && \
    mkdir -p /app/data /tmp/unishield && \
    chown -R unishield:unishield /app /tmp/unishield

COPY pyproject.toml README.md ./
COPY agents ./agents
COPY packages ./packages
COPY services ./services

RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn pydantic pydantic-settings anthropic redis httpx neo4j sqlalchemy asyncpg

USER unishield
ENV PYTHONUNBUFFERED=1

# Default: run all specialist workers; override with --agent for single agent pod
CMD ["python3", "-m", "agents.worker", "--tenant", "meridian-financial"]
