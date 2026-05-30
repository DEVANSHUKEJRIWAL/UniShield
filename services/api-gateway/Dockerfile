FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash unishield

COPY pyproject.toml README.md ./
COPY agents ./agents
COPY packages ./packages
COPY services ./services

RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn pydantic pydantic-settings anthropic redis httpx

USER unishield

EXPOSE 8000

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
