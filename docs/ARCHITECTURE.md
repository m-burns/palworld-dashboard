# Architecture

The project follows a layered architecture.

```
Browser
        │
        ▼
FastAPI Routes
        │
        ▼
Services
        │
        ▼
Repositories
        │
        ▼
SQLite
```

The Palworld server is treated as an external dependency.

```
Browser
      │
      ▼
FastAPI
      │
      ├── SQLite
      │
      ├── Palworld REST API
      │
      └── Infrastructure Services
```

---

## Folder Structure

app/

clients/

- External APIs

repositories/

- SQLAlchemy
- Database access only

services/

- Business logic

templates/

- HTML

static/

- JS
- CSS

database/

- SQLAlchemy models
- sessions

---

## Rules

Routes

Responsible only for:

- validation
- dependency injection
- returning responses

Services

Responsible for:

- business logic
- orchestration
- combining repositories

Repositories

Responsible only for:

- SQL
- persistence

Clients

Responsible only for:

- communicating with external APIs

Never place SQL inside routes.

Never place HTTP calls inside repositories.
