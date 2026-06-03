# ECR Public mirrors Docker Hub official images — avoids registry-1.docker.io timeouts in CI.
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash unishield

COPY pyproject.toml README.md ./
COPY agents ./agents
COPY packages ./packages
COPY services ./services

# Install full runtime deps (fallback must include langgraph/sqlalchemy/etc., not just fastapi)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && (pip install --no-cache-dir -e . || pip install --no-cache-dir \
        fastapi "uvicorn[standard]" pydantic pydantic-settings anthropic redis httpx \
        neo4j sqlalchemy asyncpg aiosqlite "python-jose[cryptography]" "passlib[bcrypt]" \
        prometheus-client langgraph langchain qdrant-client hvac reportlab)

RUN mkdir -p /app/data && chown -R unishield:unishield /app

ENV UNISHIELD_USE_SQLITE=1 \
    AUTO_SEED=false \
    ENABLE_CONNECTOR_INGEST=0 \
    ENABLE_CVE_POLLER=0

USER unishield

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=25s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
