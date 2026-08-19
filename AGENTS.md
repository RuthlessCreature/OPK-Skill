# Agent Instructions

This repository provides the OPK project-sync skill.

When this repository or skill is loaded by an agent:

1. Read and follow [`SKILL.md`](./SKILL.md).
2. Before meaningful project work, read current OPK project context.
3. After meaningful project work, update OPK automatically.
4. Verify every write by reading the affected project back.
5. Never expose `OPK_API_KEY`.
6. Never claim an OPK sync succeeded unless the API result and read-back confirm it.

Preferred client:

```bash
python scripts/opk.py ...
```

Required secret:

```text
OPK_API_KEY
```
