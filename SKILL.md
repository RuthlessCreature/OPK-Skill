---
name: opk-project-sync
description: Use OPK as the authoritative project-state store. Directly call the zero-auth OPK REST API, resolve or bootstrap the project safely, read current milestones/issues/next action before work, then write and verify progress after meaningful work.
---

# OPK Project Sync Skill

## Purpose

Connect any agent directly to OPK at:

```text
https://mes.fhkq.best
```

OPK is the live project execution source of truth for:

- projects
- project status and priority
- milestones / plan nodes
- issues / blockers
- next actions
- operational notes

The agent should not rely only on chat history or repository text when OPK is available.

## Authentication

**No API key is required.**

All `/api/v1/*` endpoints are intentionally available without Bearer auth for this single-user OPK deployment.

Do not invent or request `OPK_API_KEY`.

Optional runtime variables only:

```text
OPK_BASE_URL=https://mes.fhkq.best
OPK_PROJECT_ID=<fixed project id>
OPK_PROJECT_NAME=<project name/search hint>
```

A project repository may contain `.opk.json`:

```json
{
  "base_url": "https://mes.fhkq.best",
  "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "project_name": "Human readable name"
}
```

## Preferred client

```bash
python /path/to/OPK-Skill/scripts/opk.py <command>
```

It uses only Python standard library. If shell execution is unavailable but HTTP is available, use the REST API directly. See [`API.md`](./API.md).

# Mandatory lifecycle

## Phase 0 — Resolve or bootstrap the project

Before writing project state, resolve the project safely.

Resolution precedence:

1. Explicit project ID from the task/user.
2. `OPK_PROJECT_ID`.
3. `.opk.json` `project_id`.
4. Explicit project name.
5. `OPK_PROJECT_NAME` / `.opk.json` `project_name`.
6. Repository or workspace name.

If an exact project ID is known, read it directly.

If there is no fixed ID and this is the first submission, **never blindly create a project**.

### Mandatory duplicate/similarity check

Call:

```http
GET /api/v1/projects/similar?q=<project-name>
```

or:

```bash
python scripts/opk.py similar "<project-name>"
```

### If no same/similar candidate exists

The agent may automatically initialize a new project:

```bash
python scripts/opk.py init-project \
  --name "<project-name>" \
  --status active \
  --priority medium \
  --next-action "<concrete next action>"
```

`init-project` will:

1. run the similarity check;
2. call `POST /api/v1/project-ids` to get a fresh UUID;
3. create the project using that exact project ID;
4. read the project back;
5. write `.opk.json` by default when filesystem access permits.

### If OPK contains same or similar projects

**STOP before any create/update.**

Show the user the candidate project names, IDs, similarity scores, current status and next action where available.

Ask the user to choose exactly one:

1. **新提交 / Create new** — create a separate project with a fresh project ID.
2. **覆盖 / Overwrite existing** — update the selected existing project.

Do not infer this choice yourself.

After the user chooses **new**:

```bash
python scripts/opk.py init-project --name "<name>" --new ...
```

After the user chooses **overwrite**:

```bash
python scripts/opk.py init-project --name "<name>" --overwrite <project-id> ...
```

In this skill, **overwrite means update the existing project fields while preserving its existing milestones/issues**. It is not delete-and-recreate.

## Phase 1 — READ before meaningful work

Before planning, coding, debugging, deployment, report generation, or project status reporting, read the current project context:

```bash
python scripts/opk.py context --project-id <id>
```

Read at minimum:

- `status`
- `priority`
- `next_action`
- `notes`
- milestones and statuses
- open / in_progress / waiting issues
- issue severity and next actions

Use OPK to determine what is already done and what is blocked. Do not duplicate milestones or issues merely because the current chat lacks history.

## Phase 2 — WORK using current state

Perform the requested work using OPK as operational context.

If verified new facts conflict with OPK, the verified new facts may become updates after execution.

Do not change project state based on speculation.

## Phase 3 — WRITE after meaningful work

Before the final completion response, automatically synchronize meaningful results to OPK.

Meaningful results include:

- implementation completed
- bug fixed
- deployment success/failure
- validation/test result
- deliverable produced
- milestone progressed
- blocker discovered/resolved
- next action changed
- project paused/resumed/completed

Typical mapping:

| Work result | OPK action |
|---|---|
| milestone completed | milestone `status=done` + concise notes |
| work started/incomplete | milestone `status=in_progress` |
| hard blocker | create/update issue |
| waiting on external dependency | issue `status=waiting` |
| blocker fixed | issue `status=resolved` or `closed` |
| next step changed | update project `next_action` |
| project genuinely complete | project `status=done` |

## Phase 4 — VERIFY every write

Every POST/PATCH that changes project state must be followed by read-back.

Only say “OPK 已同步” when:

- the write returned success; and
- the affected project/object was read back and reflects the intended state.

The supplied CLI does read-back verification for normal write commands.

If synchronization fails, distinguish:

- work result itself; and
- OPK sync failure.

Never claim sync success based on assumption.

# API contract agents must know

Base URL:

```text
https://mes.fhkq.best
```

No auth header is required.

Core endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | service health |
| GET | `/api/v1/dashboard` | dashboard summary |
| POST | `/api/v1/project-ids` | generate fresh project UUID |
| GET | `/api/v1/projects/similar?q=NAME` | detect same/similar projects |
| GET | `/api/v1/projects` | list/search projects |
| POST | `/api/v1/projects` | create project; accepts `project_id` or `id` |
| GET | `/api/v1/projects/:id` | full project + milestones + issues |
| PATCH | `/api/v1/projects/:id` | update project |
| DELETE | `/api/v1/projects/:id` | delete project |
| GET/POST | `/api/v1/projects/:id/milestones` | list/create milestones |
| PATCH/DELETE | `/api/v1/milestones/:id` | update/delete milestone |
| GET/POST | `/api/v1/projects/:id/issues` | list/create project issues |
| GET | `/api/v1/issues` | list/filter issues |
| PATCH/DELETE | `/api/v1/issues/:id` | update/delete issue |
| GET | `/api/v1/export` | full JSON export |

Machine-readable spec:

```text
https://mes.fhkq.best/openapi.json
```

See [`API.md`](./API.md) for request examples.

# Project creation details

## Generate a project id

```bash
python scripts/opk.py new-project-id
```

Equivalent API:

```http
POST /api/v1/project-ids
```

Example response:

```json
{
  "ok": true,
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Create with a pre-generated ID

```http
POST /api/v1/projects
Content-Type: application/json

{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Example Project",
  "status": "active",
  "priority": "medium"
}
```

The API returns the actual `project_id`.

# Status enums

Project:

```text
active | paused | done | archived
```

Milestone:

```text
planned | in_progress | blocked | done | skipped
```

Issue:

```text
open | in_progress | waiting | resolved | closed
```

Priority:

```text
low | medium | high | urgent
```

Severity:

```text
low | medium | high | critical
```

# Common commands

```bash
# dashboard
python scripts/opk.py dashboard

# detect duplicates before first submit
python scripts/opk.py similar "New Project Name"

# safe bootstrap: auto-create only when no candidate exists
python scripts/opk.py init-project --name "New Project Name" --priority high --next-action "Run first validation"

# explicit user chose create-new despite candidate
python scripts/opk.py init-project --name "New Project Name" --new --priority high

# explicit user chose overwrite candidate
python scripts/opk.py init-project --name "New Project Name" --overwrite <project-id> --next-action "Continue current work"

# context
python scripts/opk.py context --project-id <project-id>

# update project
python scripts/opk.py update-project <project-id> --next-action "Next concrete step" --notes "Progress summary"

# milestone
python scripts/opk.py add-milestone <project-id> --title "Integration" --status in_progress
python scripts/opk.py update-milestone <milestone-id> --status done

# issue
python scripts/opk.py add-issue <project-id> --title "Blocking defect" --severity high --status open
python scripts/opk.py update-issue <issue-id> --status resolved --notes "Fixed and verified"
```

# Final-response contract

Successful sync:

```text
OPK 已同步：项目 <name>；里程碑 <x> → done；下一步 → <next action>。
```

Duplicate decision required:

```text
OPK 查到相同/相似项目：
- <name> (<id>, similarity=...)

请选择：① 新提交，生成新的 project-id；② 覆盖这个已有项目。
```

Failed sync:

```text
工作本身已完成；OPK 同步失败：<actual API error>。未将状态标记为已同步。
```
