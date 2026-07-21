# Palworld Dashboard

A lightweight community dashboard and monitoring application for a self-hosted Palworld dedicated server.

This repository contains the web application only. It reads live data from the Palworld REST API, records player activity in SQLite, checks the server's backup directory, and displays host resource usage. The dedicated server itself is deployed separately by the companion `palworld` repository.

## What it provides

- Live server status, version, uptime, world day, FPS, and player count
- Host CPU, memory, swap, and disk usage
- Latest-backup health and age
- Online player tracking with 30-second polling
- Persistent player history and session data
- Player profile pages
- Level and playtime leaderboards
- JSON endpoints for the dashboard data
- Graceful status reporting when the Palworld API is unavailable

The application is currently observational: it monitors and reports on the server but does not expose server administration controls.

## Technology

- FastAPI and Uvicorn
- Async SQLAlchemy with SQLite
- Jinja2 templates
- Vanilla HTML, CSS, and JavaScript
- Docker and Docker Compose

## How it fits together

```text
Browser
  |
  v
Palworld Dashboard (FastAPI)
  |-- Palworld REST API       live server and player data
  |-- SQLite                  player history and sessions
  |-- Palworld backup volume  latest-backup status
  `-- Host mounts             CPU, memory, swap, and disk metrics
```

The Compose configuration joins the existing `palworld_default` Docker network created by the companion server deployment. It also mounts the server backup directory read-only and publishes the dashboard on `127.0.0.1:8000`, making it suitable for use behind a reverse proxy.

## Requirements

- Linux host with Docker Engine and the Docker Compose plugin
- A running Palworld server with its REST API enabled
- The external Docker network `palworld_default`
- Read access to `/opt/palworld/palworld/backups`

## Configuration

Create `/opt/palworld-dashboard/.env` with the REST API credentials configured for the game server:

```dotenv
PALWORLD_API_URL=http://palworld-server:8212
PALWORLD_API_USERNAME=admin
PALWORLD_API_PASSWORD=CHANGE_ME
```

Optional settings and their defaults are:

```dotenv
BACKUP_DIRECTORY=/palworld-backups
BACKUP_MAX_AGE_HOURS=36
DATABASE_URL=sqlite+aiosqlite:////app/data/dashboard.db
```

Keep `.env` out of version control. The API URL must be reachable from the dashboard container; when both repositories use their supplied Compose files, `palworld-server` is the game server container name.

## Run with Docker Compose

Start the companion Palworld server first so its Docker network exists, then run:

```bash
docker compose build
docker compose up -d
```

Open `http://127.0.0.1:8000`, or configure a reverse proxy to expose it. Check the application health with:

```bash
curl http://127.0.0.1:8000/health
```

Useful lifecycle commands:

```bash
docker compose logs -f dashboard
docker compose up -d --build
docker compose down
```

The SQLite database persists in `./data` on the host. Palworld backups and host filesystem mounts are read-only inside the container.

## HTTP routes

| Route | Purpose |
| --- | --- |
| `GET /` | Main dashboard |
| `GET /players/{player_key}` | Player profile page |
| `GET /health` | Application health check |
| `GET /api/status` | Server, infrastructure, and backup status |
| `GET /api/players` | Current online players |
| `GET /api/players/history` | Recorded player history |
| `GET /api/players/{player_key}` | Player profile data |
| `GET /api/leaderboards/levels` | Level leaderboard (`limit` 1-100) |
| `GET /api/leaderboards/playtime` | Playtime leaderboard (`limit` 1-100) |

FastAPI's interactive API documentation is available at `/docs` while the application is running.

## Development

The codebase follows a layered structure:

```text
app/main.py          routes and application lifecycle
app/clients/         external API communication
app/services/        business logic and orchestration
app/repositories/    database access
app/database/        SQLAlchemy models and sessions
app/templates/       server-rendered pages
app/static/          browser JavaScript and CSS
```

See the project documentation for more detail:

- [Project context](docs/PROJECT_CONTEXT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Deployment and recovery](docs/DEPLOYMENT.md)
- [Roadmap](docs/ROADMAP.md)
- [AI development guidelines](docs/AI_GUIDELINES.md)
- [Paldeck snapshot import](docs/PALDECK_IMPORT.md)
