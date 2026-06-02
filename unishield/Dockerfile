FROM python:3.11-slim

WORKDIR /app

COPY unishield/requirements.txt /app/unishield/requirements.txt
RUN pip install --no-cache-dir -r unishield/requirements.txt

COPY unishield /app/unishield
COPY pyproject.toml /app/pyproject.toml

ENV PYTHONPATH=/app

EXPOSE 8000
