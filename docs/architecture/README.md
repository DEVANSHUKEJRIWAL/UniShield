# UniShield Architecture

## Overview

UniShield is an AI-native cybersecurity defense platform built on the OpenClaw agent orchestration framework.

## Week 1 foundation docs

- [Agent roster](../week1/agent-roster.md)
- [Orchestrator design](../week1/orchestrator-design.md)
- [Local dev stack](../week1/local-dev-stack.md)

## Components

- **Agent Layer**: 13 specialist agents + orchestrator (LangGraph)
- **Application Layer**: FastAPI backend + Next.js 14 frontend
- **Data Layer**: PostgreSQL, Neo4j, Qdrant, Redis, TimescaleDB, Elasticsearch
- **Infrastructure**: Docker Compose (local), Kubernetes (production)

See project specification for full architecture details.
