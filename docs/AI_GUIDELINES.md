# AI Development Guidelines

This document provides guidance for AI coding assistants (Codex, ChatGPT, Copilot, etc.) working on this repository.

The goal is to preserve consistency, code quality, and architecture while allowing rapid development.

---

# Primary Goal

This project is intended to become a production-quality community dashboard for a Palworld server.

It also serves as a long-term software engineering portfolio project.

Code quality, maintainability and readability are more important than implementing features as quickly as possible.

---

# General Principles

Always prefer:

- Small, reviewable changes
- Minimal diffs
- Explicit code
- Readable code
- Consistent architecture
- Incremental improvements

Avoid:

- Large rewrites
- Premature optimisation
- Clever code
- Unnecessary abstractions
- Introducing dependencies without justification

---

# Architecture

Maintain the layered architecture.

Browser

↓

FastAPI Routes

↓

Services

↓

Repositories

↓

SQLite

External systems (Palworld REST API, Netdata, etc.) should be accessed only through dedicated clients or services.

Never bypass these layers.

---

# Responsibilities

Routes

Responsible only for:

- Request validation
- Dependency injection
- Returning responses

Routes should not contain business logic.

---

Services

Responsible for:

- Business logic
- Orchestration
- Combining multiple repositories
- Calling external clients

---

Repositories

Responsible only for:

- Database queries
- Persistence
- SQLAlchemy interaction

Repositories should never make HTTP requests.

---

Clients

Responsible only for:

- Communicating with external APIs

Clients should not contain business logic.

---

# Frontend

Keep the frontend lightweight.

Prefer:

- Vanilla JavaScript
- Vanilla CSS
- HTML templates

Do not introduce React, Vue, Angular or similar frameworks unless explicitly requested.

Prefer progressive enhancement over complete rewrites.

---

# Styling

Maintain the existing visual style.

Avoid introducing entirely new colour palettes or layouts without discussion.

---

# Dependencies

Avoid adding new dependencies unless they provide significant value.

Before introducing a package ask:

- Can this be solved with the standard library?
- Can existing project code solve this?
- Is the dependency actively maintained?
- Is the maintenance burden justified?

Smaller dependency trees are preferred.

---

# Docker

The application must always remain deployable using Docker Compose.

Do not introduce changes that complicate deployment.

Preserve existing volume mappings, environment variables and persistence.

---

# Database

SQLite is currently the source of truth.

Prefer additive schema changes.

Avoid destructive schema changes.

Do not delete or recreate tables unless explicitly instructed.

Where possible, migrations should preserve existing user data.

---

# API Design

Maintain backwards compatibility whenever practical.

Prefer additive API endpoints over changing existing response formats.

Breaking changes should be discussed before implementation.

---

# Performance

Optimise only when there is evidence.

Avoid speculative optimisation.

Prioritise:

- Simplicity
- Readability
- Correctness

---

# Git Workflow

Never modify multiple unrelated features in a single change.

Prefer:

One feature

↓

One branch

↓

One Pull Request

↓

Merge

---

# Code Reviews

Before considering work complete, review:

- Naming
- Readability
- Duplication
- Error handling
- Type hints
- Logging
- Documentation

If something can be simplified without reducing clarity, prefer the simpler solution.

---

# HTML / CSS / JavaScript

When making substantial frontend changes:

Prefer replacing the complete function or complete file rather than providing fragmented snippets.

This reduces merge mistakes and makes reviewing changes easier.

---

# Error Handling

Prefer graceful degradation.

The dashboard should continue functioning even if:

- The Palworld API is unavailable
- Netdata is unavailable
- A backup is missing
- Optional services fail

One failing component should not bring down the application.

---

# Logging

Prefer informative logs.

Log:

- Startup
- Shutdown
- Background task failures
- API failures
- Unexpected exceptions

Avoid excessive logging of routine successful operations.

---

# Security

Never expose secrets.

Never hardcode credentials.

Never commit:

- .env files
- Passwords
- API tokens
- Server secrets

---

# Documentation

When implementing significant features:

Update documentation if appropriate.

Prefer keeping documentation accurate over allowing it to become outdated.

---

# Decision Making

If multiple solutions exist:

Choose the one that is:

1. Easier to understand
2. Easier to maintain
3. Easier to test
4. Easier to review

Do not optimise for cleverness.

---

# AI Behaviour

When proposing changes:

- Explain architectural decisions.
- Preserve existing project structure.
- Avoid unrelated refactoring.
- Minimise code churn.
- Keep commits focused.
- Prefer consistency over novelty.

If an improvement is outside the scope of the current task:

Suggest it, but do not implement it unless explicitly requested.

---

# Long-Term Vision

The long-term goal is to evolve this project into a polished community platform, not simply a server status page.

Future features include:

- Activity timeline
- Hall of Fame
- Guild pages
- Historical graphs
- Discord integration
- Authentication
- Administration panel
- Community voting
- Event management

New features should fit naturally into this vision while preserving the lightweight architecture.

# Working Style

Assume this repository is maintained by a developer who is learning through building.

When making changes:

- Explain _why_ a change is being made, not just _what_ to change.
- Prefer teaching over hiding complexity.
- Use clear, descriptive names.
- Keep implementations approachable.
- Avoid "magic" abstractions unless they provide obvious value.

The objective is to leave the codebase in a state that the maintainer can confidently understand, debug, and extend.
