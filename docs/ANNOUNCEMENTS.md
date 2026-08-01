# Server announcements

Announcements are stored in the dashboard SQLite database and displayed on the
main dashboard. Public HTTP access is read-only; publishing and removal are
limited to commands run inside the dashboard container.

Publish an announcement:

```bash
docker compose exec dashboard \
  python -m app.announcements_cli add \
  "Server event" \
  "Double experience begins Saturday at 19:00."
```

Pin an important announcement:

```bash
docker compose exec dashboard \
  python -m app.announcements_cli add \
  --pinned \
  "Maintenance" \
  "The server will restart at 04:15."
```

Use `--expires-at 2026-08-05T19:00:00+00:00` to hide an announcement
automatically after an ISO-8601 timestamp.

Deactivate an announcement by its numeric ID:

```bash
docker compose exec dashboard \
  python -m app.announcements_cli deactivate 1
```

The public endpoint is `GET /api/announcements?limit=10`. It returns active,
non-expired announcements with pinned items first.
