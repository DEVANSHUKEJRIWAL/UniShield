FROM python:3.11-slim

WORKDIR /app

COPY unishield/requirements.txt /app/unishield/requirements.txt
RUN pip install --no-cache-dir -r unishield/requirements.txt

COPY openclaw_sdk /app/openclaw_sdk
COPY unishield /app/unishield
COPY skills /app/skills

ENV PYTHONPATH=/app

EXPOSE 8000
