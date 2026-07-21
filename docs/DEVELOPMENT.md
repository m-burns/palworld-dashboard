# Development Guide

## Git Workflow

Always work from feature branches.

Example

main

↓

feature/activity-timeline

↓

Pull Request

↓

Merge

Never develop directly on main.

---

## Commits

Prefer small commits.

Good

feat: add activity endpoint

Good

fix: handle missing player profile

Avoid

updated lots of stuff

---

## Pull Requests

Each PR should contain a single logical feature.

---

## Docker

Always rebuild after backend changes.

```
docker compose build
docker compose up -d
```

After frontend changes perform a hard refresh.

Ctrl + F5

---

## Database

SQLite is the source of truth.

Never manually modify production tables unless performing a migration.

---

## Style

Prefer explicit code.

Readable code is preferred over clever code.

Prefer composition over inheritance.

Use type hints.

Keep functions focused.

---

## AI Guidance

When making changes:

- preserve architecture
- avoid unnecessary dependencies
- do not replace vanilla JS with frameworks
- do not perform unrelated refactoring
- keep PRs focused
