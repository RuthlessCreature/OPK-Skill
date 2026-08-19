# OPK API Reference for Agents

Base URL:

```text
https://mes.fhkq.best
```

Authentication:

```text
None for /api/v1/*
```

All requests and responses use JSON unless noted.

## Health

```http
GET /api/health
```

## Dashboard

```http
GET /api/v1/dashboard
```

Returns project counts, milestone counts, issue counts, active projects, overdue milestones and priority issues.

## Generate a project ID

```http
POST /api/v1/project-ids
```

Example response:

```json
{
  "ok": true,
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "generated_at": "2026-08-20T00:00:00.000Z"
  }
}
```

The ID is generated but not reserved. Use it immediately in project creation.

## Find same/similar projects

```http
GET /api/v1/projects/similar?q=Project%20Name
```

Optional:

```text
threshold=0.45
```

Example response shape:

```json
{
  "ok": true,
  "data": {
    "query": "OPK Skill",
    "threshold": 0.45,
    "has_candidates": true,
    "candidates": [
      {
        "id": "...",
        "name": "OPK Skill",
        "status": "active",
        "next_action": "...",
        "similarity": 1.0
      }
    ]
  }
}
```

Agent rule: if candidates exist during first submission, do not write until the user explicitly chooses create-new or overwrite-existing.

## List/search projects

```http
GET /api/v1/projects
GET /api/v1/projects?q=OPK
GET /api/v1/projects?status=active
```

## Create project

```http
POST /api/v1/projects
Content-Type: application/json
```

Body:

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Example Project",
  "description": "Optional description",
  "status": "active",
  "priority": "medium",
  "start_date": "2026-08-20",
  "due_date": null,
  "next_action": "Run first validation",
  "notes": "Initial submission"
}
```

`id` may be used instead of `project_id`. If neither is supplied, the API generates one automatically.

Successful response includes the actual `project_id`.

## Project context

```http
GET /api/v1/projects/:id
```

Returns the project plus its milestones and issues.

## Update project

```http
PATCH /api/v1/projects/:id
Content-Type: application/json
```

Example:

```json
{
  "status": "active",
  "next_action": "Run production verification",
  "notes": "Deployment completed"
}
```

## Delete project

```http
DELETE /api/v1/projects/:id
```

This cascades project-owned milestones/issues according to OPK storage rules. Agents should not delete unless the user explicitly intends deletion.

## Milestones

List for project:

```http
GET /api/v1/projects/:id/milestones
```

Create:

```http
POST /api/v1/projects/:id/milestones
Content-Type: application/json

{
  "title": "Production deployment",
  "status": "in_progress",
  "due_date": null,
  "sort_order": 20,
  "notes": "Optional"
}
```

List globally/filter:

```http
GET /api/v1/milestones
GET /api/v1/milestones?project_id=:id
GET /api/v1/milestones?status=in_progress
```

Update/delete:

```http
PATCH /api/v1/milestones/:id
DELETE /api/v1/milestones/:id
```

## Issues

List/create under project:

```http
GET /api/v1/projects/:id/issues
POST /api/v1/projects/:id/issues
```

Create example:

```json
{
  "title": "Blocking dependency",
  "status": "open",
  "severity": "high",
  "next_action": "Contact upstream owner",
  "notes": "Optional"
}
```

Global/filter:

```http
GET /api/v1/issues
GET /api/v1/issues?project_id=:id
GET /api/v1/issues?status=open
GET /api/v1/issues?severity=high
```

Update/delete:

```http
PATCH /api/v1/issues/:id
DELETE /api/v1/issues/:id
```

## Export

```http
GET /api/v1/export
```

Returns all projects, milestones and issues as JSON.

## Enums

Project status:

```text
active | paused | done | archived
```

Priority:

```text
low | medium | high | urgent
```

Milestone status:

```text
planned | in_progress | blocked | done | skipped
```

Issue status:

```text
open | in_progress | waiting | resolved | closed
```

Severity:

```text
low | medium | high | critical
```

## Mandatory agent bootstrap sequence

```text
No fixed project_id
  ↓
GET /api/v1/projects/similar?q=<name>
  ↓
Candidates?
  ├─ No → POST /api/v1/project-ids → POST /api/v1/projects → read back → save mapping
  └─ Yes → show candidates to user and STOP
             ↓
             user chooses
             ├─ New → new project-id → create → read back → save mapping
             └─ Overwrite → PATCH selected project → read back → save mapping
```

Machine-readable OpenAPI:

```text
https://mes.fhkq.best/openapi.json
```
