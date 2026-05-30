# UniShield Architecture

## Overview

UniShield is an AI-native cybersecurity defense platform built on the OpenClaw agent orchestration framework.

## Components

- **Agent Layer**: 13 specialist agents + orchestrator (LangGraph)
- **Application Layer**: FastAPI backend + Next.js 14 frontend
- **Data Layer**: PostgreSQL, Neo4j, Qdrant, Redis, TimescaleDB, Elasticsearch
- **Infrastructure**: Docker Compose (local), Kubernetes (production)

See project specification for full architecture details.
