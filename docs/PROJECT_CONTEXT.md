# Palworld Community Dashboard

## Project Overview

This project is a full-stack dashboard for a self-hosted Palworld dedicated server.

The project serves two purposes:

1. Provide a high-quality community dashboard for server players.
2. Act as a portfolio-quality software engineering project.

The goal is not simply to expose the Palworld API. The goal is to build a production-style web application around the server.

---

## Current Technology Stack

Backend

- Python
- FastAPI
- SQLAlchemy (async)
- SQLite

Frontend

- Vanilla HTML
- Vanilla CSS
- Vanilla JavaScript

Infrastructure

- Docker
- Docker Compose
- Ubuntu
- Git / GitHub

External Services

- Palworld REST API
- Netdata

---

## Design Philosophy

The application should remain:

- lightweight
- fast
- understandable
- easy to deploy
- containerised

Avoid unnecessary frameworks.

Vanilla JS is preferred over introducing React/Vue unless there is a compelling reason.

SQLite is preferred until there is a demonstrated need for PostgreSQL.

---

## Coding Philosophy

Prefer:

- readable code
- explicit naming
- small functions
- feature branches
- incremental improvements

Avoid:

- large rewrites
- unnecessary abstractions
- premature optimisation

---

## Project Goals

Short term

- Stable dashboard
- Good monitoring
- Community leaderboards

Medium term

- Player profiles
- Hall of Fame
- Activity timeline
- Admin tools

Long term

- Discord integration
- Authentication
- Voting
- Guild pages
- Interactive statistics
- Production deployment
