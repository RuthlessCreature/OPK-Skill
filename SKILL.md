---
name: opk-project-sync
description: Use OPK as the authoritative project-state store. Read current project, milestone, issue, and next-action context before doing project work; after meaningful work, automatically update OPK and verify the write by reading it back.
---

# OPK Project Sync Skill

## Purpose

This skill connects an agent to the OPK project dashboard at `https://mes.fhkq.best`.

OPK is the **project execution source of truth** for:

- projects
- project status and priority
- milestones / planned nodes
- issues / blockers
- issue severity and status
- next actions
- notes / progress summaries

The agent must use OPK as a live operational memory rather than relying only on chat history, repository text, or assumptions.

## Required runtime configuration

The agent needs:

```text
OPK_API_KEY=<Bearer API key>
```

Optional:

```text
OPK_BASE_URL=https://mes.fhkq.best
OPK_PROJECT_ID=<fixed project id>
OPK_PROJECT_NAME=<project name or search hint>
```

A repository may also contain `.opk.json`:

```json
{
  "base_url": "https://mes.fhkq.best",
  "project_id": "...",
  "project_name": "optional human-readable name"
}
```

Never print, commit, persist, or expose `OPK_API_KEY`.

## Tooling

Preferred client:

```bash
python /path/to/OPK-Skill/scripts/opk.py <command>
```

It uses only the Python standard library.

If the helper script is unavailable but HTTP access is available, call the OPK REST API directly with:

```http
Authorization: Bearer <OPK_API_KEY>
Content-Type: application/json
```

## Mandatory execution loop

### 1. Before meaningful project work: READ

Before making a plan, changing code, preparing a delivery, debugging, implementing a feature, or reporting project status, get OPK context first whenever the work can be associated with an OPK project.

Resolution precedence:

1. Explicit project ID from the user/task.
2. `OPK_PROJECT_ID`.
3. `.opk.json` `project_id`.
4. Explicit project name from the user/task.
5. `OPK_PROJECT_NAME` or `.opk.json` `project_name`.
6. Search OPK by the repository/project name.

Use:

```bash
python scripts/opk.py context --project-id <id>
```

or:

```bash
python scripts/opk.py context --q "<name>"
```

Read at minimum:

- project.status
- project.priority
- project.next_action
- project.notes
- milestones and their statuses
- open/in-progress/waiting issues
- issue severity and next_action

### 2. During work: USE THE STATE

Use OPK context to determine:

- what is already done
- what is currently in progress
- the next planned node
- whether a blocker already exists
- which issue is most urgent
- what the last recorded next action was

Do not create duplicate milestones/issues just because the current conversation lacks earlier context.

If new facts conflict with OPK, treat the new verified facts as candidate updates and write them back after execution.

### 3. After meaningful work: WRITE

After completing meaningful work, **automatically synchronize OPK before giving the final completion response**.

A meaningful work result includes any of the following:

- implementation completed
- bug fixed
- deployment completed or failed
- test/validation completed
- customer/internal decision reached
- milestone progressed
- blocker discovered
- blocker resolved
- next action changed
- project paused/resumed/completed
- deliverable produced
- external dependency discovered

Update only fields supported by evidence from the actual work.

Typical mappings:

| Work result | OPK update |
|---|---|
| milestone completed | milestone `status=done`, append concise notes |
| work started but incomplete | milestone `status=in_progress` |
| hard blocker found | create/update issue, `status=open|in_progress`, severity based on impact |
| waiting on external party | issue `status=waiting` |
| blocker fixed | issue `status=resolved` or `closed` |
| project next step changes | project `next_action` |
| important progress | project `notes` |
| project fully complete | project `status=done` only if genuinely complete |

### 4. After every write: VERIFY

A successful PATCH/POST is not enough. Read the affected project/object back from OPK.

Only report "synced to OPK" if:

- HTTP request succeeded, and
- read-back reflects the intended state.

If synchronization fails:

- do not claim success
- keep the actual work result separate from sync status
- report the HTTP/error reason concisely
- do not expose credentials

## Project resolution safety

Never silently update an ambiguous project.

Safe automatic selection is allowed when one of these is true:

- exact project ID is known
- exact case-insensitive project-name match exists
- search returns exactly one plausible result
- `.opk.json` explicitly maps the repository to a project ID

If multiple plausible projects remain and no fixed mapping exists, do not write to a guessed project. Report the ambiguity or create the mapping only if the task explicitly authorizes it.

## Creating missing project state

If work clearly belongs to a new project and no project exists, an agent may create one when the user's instruction implies project creation/tracking.

Recommended defaults:

```json
{
  "status": "active",
  "priority": "medium"
}
```

Set `next_action` to the next concrete executable step, not a vague goal.

Good:

```text
Run hardware-in-loop validation on the revised Modbus retry logic and record 100-cycle error rate.
```

Bad:

```text
Continue working on project.
```

## Notes policy

Notes should be short operational history, not a transcript.

Prefer:

```text
2026-08-19: Production deploy succeeded; D1 migration and /api/health verified. Next: migrate active project backlog.
```

Avoid dumping chain-of-thought, long chat summaries, credentials, or irrelevant details.

## Issue severity

Use OPK severities consistently:

- `critical`: blocks delivery/production or causes severe data/safety/business failure
- `high`: materially blocks a key milestone or requires urgent correction
- `medium`: meaningful issue with workaround or limited scope
- `low`: minor defect, cleanup, or non-blocking improvement

## Status enums

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

## Common commands

### Dashboard

```bash
python scripts/opk.py dashboard
```

### List/search projects

```bash
python scripts/opk.py projects
python scripts/opk.py projects --q "OPK"
python scripts/opk.py projects --status active
```

### Full project context

```bash
python scripts/opk.py context --project-id <id>
python scripts/opk.py context --q "project name"
```

### Update project

```bash
python scripts/opk.py update-project <project-id> \
  --status active \
  --next-action "Run production verification" \
  --notes "Deployment completed; verification pending."
```

### Add/update milestone

```bash
python scripts/opk.py add-milestone <project-id> \
  --title "Production deployment" \
  --status done \
  --notes "Worker and health endpoint verified."

python scripts/opk.py update-milestone <milestone-id> --status done
```

### Add/update issue

```bash
python scripts/opk.py add-issue <project-id> \
  --title "Cloudflare token lacks D1 permission" \
  --severity high \
  --status open \
  --next-action "Regenerate token with D1 Edit permission"

python scripts/opk.py update-issue <issue-id> \
  --status resolved \
  --notes "New token validated in CI."
```

## Final-response contract

For project work with a successful OPK sync, the final response should include a compact sync line such as:

```text
OPK 已同步：里程碑「Production deployment」→ done；下一步 → Run production verification。
```

For a failed sync:

```text
工作本身已完成；OPK 同步失败：HTTP 401。未将状态标记为已同步。
```

The final response must reflect the real API result, never an assumed update.
