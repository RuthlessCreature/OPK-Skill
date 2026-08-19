# Agent Instructions

This repository provides the OPK project-sync skill.

When this repository or skill is loaded by an agent:

1. Read and follow [`SKILL.md`](./SKILL.md).
2. OPK `/api/v1/*` requires **no API key**. Do not request `OPK_API_KEY`.
3. Before meaningful project work, resolve and read current OPK context.
4. On first submission with no fixed project ID, call the similarity API first.
5. If same/similar projects exist, stop and ask the user to choose **new submission** or **overwrite one existing project**. Never choose silently.
6. If no candidate exists, generate a project ID and create the project.
7. After meaningful work, update OPK automatically.
8. Verify every write by reading the affected project back.
9. Never claim an OPK sync succeeded unless the API result and read-back confirm it.

Preferred client:

```bash
python scripts/opk.py ...
```

Default API:

```text
https://mes.fhkq.best
```

Machine-readable API:

```text
https://mes.fhkq.best/openapi.json
```

No secret configuration is required for OPK API access.
