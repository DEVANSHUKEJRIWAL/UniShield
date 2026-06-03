# ECR Public mirrors Docker Hub official images — avoids registry-1.docker.io timeouts in CI.
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY unishield/requirements.txt /app/unishield/requirements.txt
RUN pip install --no-cache-dir -r unishield/requirements.txt

COPY openclaw_sdk /app/openclaw_sdk
COPY unishield /app/unishield
COPY skills /app/skills

ENV PYTHONPATH=/app

EXPOSE 8000
