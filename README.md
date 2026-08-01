# Palworld Dashboard

A lightweight community dashboard and monitoring application for a self-hosted Palworld dedicated server.

This repository contains the web application only. It reads live data from the Palworld REST API, records player activity in SQLite, reads sanitized backup metadata exported by the host, and displays host resource usage. The dedicated server itself is deployed separately by the companion `palworld` repository.

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
  |-- Read-only API gateway   allowlisted live server and player data
  |-- SQLite                  player history and sessions
  |-- Sanitized status file   latest-backup age and size only
  `-- /proc read-only         CPU, memory, and swap metrics
```

Only the read-only API gateway joins `palworld_default`; the dashboard cannot reach the game-server network directly. The dashboard publishes only on `127.0.0.1:8000` for use behind a reverse proxy. Its root filesystem is read-only, Linux capabilities are dropped, and raw backup archives and the host root are not mounted.

## Requirements

- Linux host with Docker Engine and the Docker Compose plugin
- A running Palworld server with its REST API enabled
- The external Docker network `palworld_default`
- Host-side read access to `/opt/palworld/palworld/backups` for the metadata exporter

## Configuration

Create `/opt/palworld-dashboard/.env` with the REST API credentials configured for the game server:

```dotenv
PALWORLD_API_URL=http://palworld-api-gateway:8080
PALWORLD_API_USERNAME=admin
PALWORLD_API_PASSWORD=CHANGE_ME
```

Optional settings and their defaults are:

```dotenv
BACKUP_STATUS_FILE=/app/runtime/backup-status.json
BACKUP_MAX_AGE_HOURS=36
DATABASE_URL=sqlite+aiosqlite:////app/data/dashboard.db
ALLOWED_HOSTS=localhost,127.0.0.1
ENABLE_API_DOCS=false
```

Keep `.env` out of version control. For a public deployment, add the exact DNS name to `ALLOWED_HOSTS`. Compose overrides the API URL to the restricted gateway; do not point the dashboard directly at `palworld-server`.

## Run with Docker Compose

Start the companion Palworld server first so its Docker network exists. Export the initial backup metadata, then run:

```bash
./scripts/export-backup-status.sh
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

The SQLite database persists in `./data`. Run `scripts/export-backup-status.sh` every five minutes from host cron; it exports only backup time and size to `./runtime`.

## HTTP routes

| Route | Purpose |
| --- | --- |
| `GET /` | Main dashboard |
| `GET /players/{player_key}` | Player profile page |
| `GET /hall-of-fame` | Community Hall of Fame page |
| `GET /health` | Application health check |
| `GET /api/status` | Server, infrastructure, and backup status |
| `GET /api/players` | Current online players |
| `GET /api/players/history` | Recorded player history |
| `GET /api/activity` | Recent player join and leave activity |
| `GET /api/announcements` | Active server announcements |
| `GET /api/polls` | Active community polls and results |
| `POST /api/polls/{poll_id}/vote` | Cast an anonymous browser vote |
| `GET /api/players/{player_key}` | Player profile data |
| `GET /api/leaderboards/levels` | Level leaderboard (`limit` 1-100) |
| `GET /api/leaderboards/playtime` | Playtime leaderboard (`limit` 1-100) |

FastAPI's interactive API documentation is disabled by default. Set `ENABLE_API_DOCS=true` only for trusted development environments.

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
- [Server announcements](docs/ANNOUNCEMENTS.md)
- [Community voting](docs/VOTING.md)
