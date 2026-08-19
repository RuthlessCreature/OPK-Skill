#!/usr/bin/env python3
"""Zero-auth OPK REST client for agents.

Uses only Python standard library.
Default API: https://mes.fhkq.best

Bootstrap rule:
- search same/similar projects before first project creation
- if candidates exist, stop and require explicit user choice: create new or overwrite one id
- if no candidates exist, generate a project_id, create the project, and optionally persist .opk.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://mes.fhkq.best"
PROJECT_STATUSES = ["active", "paused", "done", "archived"]
PRIORITIES = ["low", "medium", "high", "urgent"]
MILESTONE_STATUSES = ["planned", "in_progress", "blocked", "done", "skipped"]
ISSUE_STATUSES = ["open", "in_progress", "waiting", "resolved", "closed"]
SEVERITIES = ["low", "medium", "high", "critical"]


class OpkError(RuntimeError):
    pass


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def pretty(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False))


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise OpkError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OpkError(f"Config must be a JSON object: {path}")
    return value


def discover_config(explicit: str | None) -> tuple[dict[str, Any], Path | None]:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise OpkError(f"Config not found: {path}")
        return load_json_file(path), path
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        path = directory / ".opk.json"
        if path.exists():
            return load_json_file(path), path
    return {}, None


def compact_none(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


def data_of(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


class OpkClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(self, path: str, method: str = "GET", body: Any | None = None) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                detail = raw
            raise OpkError(f"HTTP {exc.code} {method.upper()} {path}: {json.dumps(detail, ensure_ascii=False)}") from exc
        except urllib.error.URLError as exc:
            raise OpkError(f"Network error {method.upper()} {path}: {exc.reason}") from exc

    def health(self) -> Any:
        return self.request("/api/health")

    def dashboard(self) -> Any:
        return self.request("/api/v1/dashboard")

    def new_project_id(self) -> Any:
        return self.request("/api/v1/project-ids", "POST")

    def similar_projects(self, name: str, threshold: float = 0.45) -> Any:
        params = urllib.parse.urlencode({"q": name, "threshold": threshold})
        return self.request("/api/v1/projects/similar?" + params)

    def list_projects(self, q: str | None = None, status: str | None = None) -> Any:
        params: dict[str, str] = {}
        if q:
            params["q"] = q
        if status:
            params["status"] = status
        suffix = "?" + urllib.parse.urlencode(params) if params else ""
        return self.request("/api/v1/projects" + suffix)

    def get_project(self, project_id: str) -> Any:
        return self.request(f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}")

    def create_project(self, body: dict[str, Any]) -> Any:
        return self.request("/api/v1/projects", "POST", body)

    def update_project(self, project_id: str, body: dict[str, Any]) -> Any:
        return self.request(f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}", "PATCH", body)

    def delete_project(self, project_id: str) -> Any:
        return self.request(f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}", "DELETE")

    def list_milestones(self, project_id: str | None = None, status: str | None = None) -> Any:
        params: dict[str, str] = {}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        suffix = "?" + urllib.parse.urlencode(params) if params else ""
        return self.request("/api/v1/milestones" + suffix)

    def add_milestone(self, project_id: str, body: dict[str, Any]) -> Any:
        return self.request(f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}/milestones", "POST", body)

    def update_milestone(self, milestone_id: str, body: dict[str, Any]) -> Any:
        return self.request(f"/api/v1/milestones/{urllib.parse.quote(milestone_id, safe='')}", "PATCH", body)

    def delete_milestone(self, milestone_id: str) -> Any:
        return self.request(f"/api/v1/milestones/{urllib.parse.quote(milestone_id, safe='')}", "DELETE")

    def list_issues(self, project_id: str | None = None, status: str | None = None, severity: str | None = None) -> Any:
        params: dict[str, str] = {}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        suffix = "?" + urllib.parse.urlencode(params) if params else ""
        return self.request("/api/v1/issues" + suffix)

    def add_issue(self, project_id: str, body: dict[str, Any]) -> Any:
        return self.request(f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}/issues", "POST", body)

    def update_issue(self, issue_id: str, body: dict[str, Any]) -> Any:
        return self.request(f"/api/v1/issues/{urllib.parse.quote(issue_id, safe='')}", "PATCH", body)

    def delete_issue(self, issue_id: str) -> Any:
        return self.request(f"/api/v1/issues/{urllib.parse.quote(issue_id, safe='')}", "DELETE")


def resolve_project(client: OpkClient, config: dict[str, Any], project_id: str | None, q: str | None) -> dict[str, Any]:
    fixed_id = project_id or os.getenv("OPK_PROJECT_ID") or config.get("project_id")
    if fixed_id:
        project = data_of(client.get_project(str(fixed_id)))
        if not isinstance(project, dict):
            raise OpkError("Unexpected project response")
        return project

    query = q or os.getenv("OPK_PROJECT_NAME") or config.get("project_name")
    if not query:
        raise OpkError("No project mapping. Supply --project-id/--q, OPK_PROJECT_ID/OPK_PROJECT_NAME, or .opk.json")

    similar = data_of(client.similar_projects(str(query)))
    candidates = similar.get("candidates", []) if isinstance(similar, dict) else []
    exact = [p for p in candidates if float(p.get("similarity", 0)) >= 0.9999]
    if len(exact) == 1:
        return data_of(client.get_project(str(exact[0]["id"])))
    if len(candidates) == 1 and float(candidates[0].get("similarity", 0)) >= 0.75:
        return data_of(client.get_project(str(candidates[0]["id"])))
    if not candidates:
        raise OpkError(f"No OPK project matched: {query}")
    names = [f"{p.get('id')} :: {p.get('name')} :: similarity={p.get('similarity')}" for p in candidates]
    raise OpkError("Ambiguous/similar project search. User decision is required before any write:\n  " + "\n  ".join(names))


def add_common_project_fields(parser: argparse.ArgumentParser, require_name: bool = False) -> None:
    parser.add_argument("--name", required=require_name)
    parser.add_argument("--description")
    parser.add_argument("--status", choices=PROJECT_STATUSES)
    parser.add_argument("--priority", choices=PRIORITIES)
    parser.add_argument("--start-date")
    parser.add_argument("--due-date")
    parser.add_argument("--next-action")
    parser.add_argument("--notes")


def project_body(args: argparse.Namespace) -> dict[str, Any]:
    return compact_none({
        "name": getattr(args, "name", None),
        "description": getattr(args, "description", None),
        "status": getattr(args, "status", None),
        "priority": getattr(args, "priority", None),
        "start_date": getattr(args, "start_date", None),
        "due_date": getattr(args, "due_date", None),
        "next_action": getattr(args, "next_action", None),
        "notes": getattr(args, "notes", None),
    })


def milestone_body(args: argparse.Namespace) -> dict[str, Any]:
    return compact_none({
        "title": getattr(args, "title", None),
        "status": getattr(args, "status", None),
        "due_date": getattr(args, "due_date", None),
        "sort_order": getattr(args, "sort_order", None),
        "notes": getattr(args, "notes", None),
    })


def issue_body(args: argparse.Namespace) -> dict[str, Any]:
    return compact_none({
        "title": getattr(args, "title", None),
        "milestone_id": getattr(args, "milestone_id", None),
        "description": getattr(args, "description", None),
        "status": getattr(args, "status", None),
        "severity": getattr(args, "severity", None),
        "next_action": getattr(args, "next_action", None),
        "notes": getattr(args, "notes", None),
    })


def require_nonempty(body: dict[str, Any], label: str) -> None:
    if not body:
        raise OpkError(f"No {label} fields supplied")


def verified_write(client: OpkClient, write_response: Any, project_id: str | None = None) -> dict[str, Any]:
    written = data_of(write_response)
    resolved_project_id = project_id
    if not resolved_project_id and isinstance(written, dict):
        resolved_project_id = written.get("project_id") or written.get("id")
    verify = client.get_project(str(resolved_project_id)) if resolved_project_id else None
    return {"write": write_response, "verify": verify}


def write_project_mapping(path: Path, base_url: str, project: dict[str, Any]) -> None:
    mapping = {"base_url": base_url, "project_id": project.get("id"), "project_name": project.get("name")}
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bootstrap_project(client: OpkClient, base_url: str, args: argparse.Namespace) -> dict[str, Any]:
    body = project_body(args)
    name = str(body.get("name") or "").strip()
    if not name:
        raise OpkError("--name is required")

    similar_data = data_of(client.similar_projects(name, args.threshold))
    candidates = similar_data.get("candidates", []) if isinstance(similar_data, dict) else []

    if candidates and not args.new and not args.overwrite:
        return {
            "ok": False,
            "status": "needs_user_decision",
            "message": "OPK already has same/similar projects. Do not write until the user chooses new or overwrite.",
            "query": name,
            "candidates": candidates,
            "choices": {
                "new": "Create a new project with a new project_id.",
                "overwrite": "Update one selected existing project id; milestones/issues are preserved."
            }
        }

    if args.new and args.overwrite:
        raise OpkError("Choose only one of --new or --overwrite")

    if args.overwrite:
        result = client.update_project(args.overwrite, body)
        project = data_of(client.get_project(args.overwrite))
        action = "overwritten"
    else:
        id_data = data_of(client.new_project_id())
        project_id = id_data.get("project_id") if isinstance(id_data, dict) else None
        if not project_id:
            raise OpkError("project-id API did not return project_id")
        body["project_id"] = project_id
        result = client.create_project(body)
        project = data_of(client.get_project(project_id))
        action = "created"

    if args.config_out:
        write_project_mapping(Path(args.config_out).expanduser(), base_url, project)

    return {
        "ok": True,
        "status": action,
        "project_id": project.get("id"),
        "project": project,
        "write": result,
        "config_written": args.config_out,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OPK zero-auth agent REST client")
    parser.add_argument("--config", help="Path to .opk.json (otherwise auto-discover upward)")
    parser.add_argument("--base-url", help="Override OPK base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("dashboard")
    sub.add_parser("new-project-id")

    p = sub.add_parser("similar")
    p.add_argument("name")
    p.add_argument("--threshold", type=float, default=0.45)

    p = sub.add_parser("projects")
    p.add_argument("--q")
    p.add_argument("--status", choices=PROJECT_STATUSES)

    p = sub.add_parser("context")
    p.add_argument("--project-id")
    p.add_argument("--q")

    p = sub.add_parser("init-project", help="Safe first submission: duplicate check -> user decision if needed -> create/overwrite")
    add_common_project_fields(p, require_name=True)
    p.add_argument("--threshold", type=float, default=0.45)
    p.add_argument("--new", action="store_true", help="Explicit user choice: create a new project even when similar candidates exist")
    p.add_argument("--overwrite", metavar="PROJECT_ID", help="Explicit user choice: update this existing project; preserve milestones/issues")
    p.add_argument("--config-out", default=".opk.json", help="Write project mapping after success; use empty string to disable")

    p = sub.add_parser("create-project", help="Low-level create; skill should prefer init-project")
    add_common_project_fields(p, require_name=True)
    p.add_argument("--project-id")

    p = sub.add_parser("update-project")
    p.add_argument("project_id")
    add_common_project_fields(p)

    p = sub.add_parser("delete-project")
    p.add_argument("project_id")

    p = sub.add_parser("milestones")
    p.add_argument("--project-id")
    p.add_argument("--status", choices=MILESTONE_STATUSES)

    p = sub.add_parser("add-milestone")
    p.add_argument("project_id")
    p.add_argument("--title", required=True)
    p.add_argument("--status", choices=MILESTONE_STATUSES)
    p.add_argument("--due-date")
    p.add_argument("--sort-order", type=int)
    p.add_argument("--notes")

    p = sub.add_parser("update-milestone")
    p.add_argument("milestone_id")
    p.add_argument("--title")
    p.add_argument("--status", choices=MILESTONE_STATUSES)
    p.add_argument("--due-date")
    p.add_argument("--sort-order", type=int)
    p.add_argument("--notes")

    p = sub.add_parser("delete-milestone")
    p.add_argument("milestone_id")

    p = sub.add_parser("issues")
    p.add_argument("--project-id")
    p.add_argument("--status", choices=ISSUE_STATUSES)
    p.add_argument("--severity", choices=SEVERITIES)

    p = sub.add_parser("add-issue")
    p.add_argument("project_id")
    p.add_argument("--title", required=True)
    p.add_argument("--milestone-id")
    p.add_argument("--description")
    p.add_argument("--status", choices=ISSUE_STATUSES)
    p.add_argument("--severity", choices=SEVERITIES)
    p.add_argument("--next-action")
    p.add_argument("--notes")

    p = sub.add_parser("update-issue")
    p.add_argument("issue_id")
    p.add_argument("--title")
    p.add_argument("--milestone-id")
    p.add_argument("--description")
    p.add_argument("--status", choices=ISSUE_STATUSES)
    p.add_argument("--severity", choices=SEVERITIES)
    p.add_argument("--next-action")
    p.add_argument("--notes")

    p = sub.add_parser("delete-issue")
    p.add_argument("issue_id")

    p = sub.add_parser("raw")
    p.add_argument("method", choices=["GET", "POST", "PATCH", "DELETE"])
    p.add_argument("path")
    p.add_argument("--body-json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config, config_path = discover_config(args.config)
    base_url = str(args.base_url or os.getenv("OPK_BASE_URL") or config.get("base_url") or DEFAULT_BASE_URL)
    client = OpkClient(base_url)
    cmd = args.command

    if cmd == "health":
        pretty(client.health())
    elif cmd == "dashboard":
        pretty(client.dashboard())
    elif cmd == "new-project-id":
        pretty(client.new_project_id())
    elif cmd == "similar":
        pretty(client.similar_projects(args.name, args.threshold))
    elif cmd == "projects":
        pretty(client.list_projects(args.q, args.status))
    elif cmd == "context":
        project = resolve_project(client, config, args.project_id, args.q)
        pretty({"config": str(config_path) if config_path else None, "project": project})
    elif cmd == "init-project":
        if args.config_out == "":
            args.config_out = None
        result = bootstrap_project(client, base_url, args)
        pretty(result)
        if result.get("status") == "needs_user_decision":
            return 3
    elif cmd == "create-project":
        body = project_body(args)
        if args.project_id:
            body["project_id"] = args.project_id
        result = client.create_project(body)
        project_id = result.get("project_id") if isinstance(result, dict) else None
        pretty(verified_write(client, result, project_id))
    elif cmd == "update-project":
        body = project_body(args)
        require_nonempty(body, "project update")
        pretty(verified_write(client, client.update_project(args.project_id, body), args.project_id))
    elif cmd == "delete-project":
        pretty(client.delete_project(args.project_id))
    elif cmd == "milestones":
        pretty(client.list_milestones(args.project_id, args.status))
    elif cmd == "add-milestone":
        pretty(verified_write(client, client.add_milestone(args.project_id, milestone_body(args)), args.project_id))
    elif cmd == "update-milestone":
        body = milestone_body(args)
        require_nonempty(body, "milestone update")
        pretty(verified_write(client, client.update_milestone(args.milestone_id, body)))
    elif cmd == "delete-milestone":
        pretty(client.delete_milestone(args.milestone_id))
    elif cmd == "issues":
        pretty(client.list_issues(args.project_id, args.status, args.severity))
    elif cmd == "add-issue":
        pretty(verified_write(client, client.add_issue(args.project_id, issue_body(args)), args.project_id))
    elif cmd == "update-issue":
        body = issue_body(args)
        require_nonempty(body, "issue update")
        pretty(verified_write(client, client.update_issue(args.issue_id, body)))
    elif cmd == "delete-issue":
        pretty(client.delete_issue(args.issue_id))
    elif cmd == "raw":
        body = json.loads(args.body_json) if args.body_json else None
        pretty(client.request(args.path, args.method, body))
    else:
        raise OpkError(f"Unsupported command: {cmd}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OpkError as exc:
        eprint(f"OPK_ERROR: {exc}")
        raise SystemExit(2)
