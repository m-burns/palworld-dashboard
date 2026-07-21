# Deployment

## Server

Ubuntu VPS

Docker Compose

---

## Components

Palworld Server

Dashboard

Netdata

SQLite

---

## Data

Persistent data

Palworld saves

Palworld backups

Dashboard SQLite

Git repositories

Environment files

---

## Restart Strategy

Preferred

Graceful restart

Save world

↓

Create backup

↓

Restart container

↓

Verify REST API

↓

Resume polling

---

## Backup Strategy

Daily scheduled backups

Manual backups before maintenance

Always verify backup success before restart.

---

## Recovery

To migrate:

1. Provision new VPS
2. Install Docker
3. Clone repositories
4. Copy saves
5. Copy dashboard database
6. Copy environment files
7. Start containers
8. Verify APIs
9. Open server

---

## Monitoring

Dashboard monitors

- Server health
- Players
- Sessions
- Backups
- Infrastructure

Netdata monitors

- VPS health

Future

Prometheus

Grafana
