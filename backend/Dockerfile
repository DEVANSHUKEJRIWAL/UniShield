# Orchestrator + SCR engine
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY openclaw_sdk /app/openclaw_sdk
COPY backend /app/backend
COPY skills /app/skills

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
