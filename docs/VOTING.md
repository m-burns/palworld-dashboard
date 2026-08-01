# Community voting

Polls are stored in SQLite and managed from inside the dashboard container.
Public users can list active polls and cast votes, but cannot create or close
polls.

Create a poll with at least two options:

```bash
docker compose exec dashboard \
  python -m app.voting_cli create \
  "Which event should run next?" \
  "Boss hunt" "Building contest" "Pal races"
```

Optionally add an ISO-8601 closing time:

```bash
docker compose exec dashboard \
  python -m app.voting_cli create \
  --closes-at 2026-08-08T19:00:00+00:00 \
  "Choose the event" "Boss hunt" "Pal races"
```

Close a poll manually:

```bash
docker compose exec dashboard python -m app.voting_cli close 1
```

The public endpoints are `GET /api/polls` and
`POST /api/polls/{poll_id}/vote`.

A random token is stored in an HTTP-only browser cookie, while only its SHA-256
hash is stored with a vote. This provides one vote per browser without recording
IP addresses or player identifiers. It is a lightweight safeguard, not strong
identity verification: clearing browser storage permits another vote. Discord
or player authentication should replace it when authentication is implemented.
