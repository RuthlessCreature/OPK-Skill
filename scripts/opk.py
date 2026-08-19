#!/usr/bin/env python3
"""Minimal OPK REST client for agents.

Uses only Python standard library.
Authentication: Authorization: Bearer $OPK_API_KEY
Default API: https://mes.fhkq.best
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


class OpkError(RuntimeError):
    pass


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


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


def pretty(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False))


class OpkClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def request(self, path: str, method: str = "GET", body: Any | None = None) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
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

    def dashboard(self) -> Any:
        return self.request("/api/v1/dashboard")

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
        return self.request(
            f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}/milestones",
            "POST",
            body,
        )

    def update_milestone(self, milestone_id: str, body: dict[str, Any]) -> Any:
        return self.request(
            f"/api/v1/milestones/{urllib.parse.quote(milestone_id, safe='')}",
            "PATCH",
            body,
        )

    def delete_milestone(self, milestone_id: str) -> Any:
        return self.request(
            f"/api/v1/milestones/{urllib.parse.quote(milestone_id, safe='')}",
            "DELETE",
        )

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
        return self.request(
            f"/api/v1/projects/{urllib.parse.quote(project_id, safe='')}/issues",
            "POST",
            body,
        )

    def update_issue(self, issue_id: str, body: dict[str, Any]) -> Any:
        return self.request(
            f"/api/v1/issues/{urllib.parse.quote(issue_id, safe='')}",
            "PATCH",
            body,
        )

    def delete_issue(self, issue_id: str) -> Any:
        return self.request(
            f"/api/v1/issues/{urllib.parse.quote(issue_id, safe='')}",
            "DELETE",
        )


def data_of(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def resolve_project(
    client: OpkClient,
    config: dict[str, Any],
    project_id: str | None,
    q: str | None,
) -> dict[str, Any]:
    fixed_id = project_id or os.getenv("OPK_PROJECT_ID") or config.get("project_id")
    if fixed_id:
        project = data_of(client.get_project(str(fixed_id)))
        if not isinstance(project, dict):
            raise OpkError("Unexpected project response")
        return project

    query = q or os.getenv("OPK_PROJECT_NAME") or config.get("project_name")
    if not query:
        raise OpkError("No project mapping. Supply --project-id/--q, OPK_PROJECT_ID/OPK_PROJECT_NAME, or .opk.json")

    result = data_of(client.list_projects(q=str(query)))
    if not isinstance(result, list):
        raise OpkError("Unexpected project search response")
    if not result:
        raise OpkError(f"No OPK project matched: {query}")

    exact = [p for p in result if str(p.get("name", "")).casefold() == str(query).casefold()]
    if len(exact) == 1:
        return data_of(client.get_project(str(exact[0]["id"])))
    if len(result) == 1:
        return data_of(client.get_project(str(result[0]["id"])))

    names = [f"{p.get('id')} :: {p.get('name')}" for p in result]
    raise OpkError("Ambiguous project search. Use an exact project id:\n  " + "\n  ".join(names))


def add_common_project_fields(parser: argparse.ArgumentParser, require_name: bool = False) -> None:
    parser.add_argument("--name", required=require_name)
    parser.add_argument("--description")
    parser.add_argument("--status", choices=["active", "paused", "done", "archived"])
    parser.add_argument("--priority", choices=["low", "medium", "high", "urgent"])
    parser.add_argument("--start-date")
    parser.add_argument("--due-date")
    parser.add_argument("--next-action")
    parser.add_argument("--notes")


def project_body(args: argparse.Namespace) -> dict[str, Any]:
    return compact_none(
        {
            "name": getattr(args, "name", None),
            "description": getattr(args, "description", None),
            "status": getattr(args, "status", None),
            "priority": getattr(args, "priority", None),
            "start_date": getattr(args, "start_date", None),
            "due_date": getattr(args, "due_date", None),
            "next_action": getattr(args, "next_action", None),
            "notes": getattr(args, "notes", None),
        }
    )


def milestone_body(args: argparse.Namespace) -> dict[str, Any]:
    return compact_none(
        {
            "title": getattr(args, "title", None),
            "status": getattr(args, "status", None),
            "due_date": getattr(args, "due_date", None),
            "sort_order": getattr(args, "sort_order", None),
            "notes": getattr(args, "notes", None),
        }
    )


def issue_body(args: argparse.Namespace) -> dict[str, Any]:
    return compact_none(
        {
            "title": getattr(args, "title", None),
            "milestone_id": getattr(args, "milestone_id", None),
            "description": getattr(args, "description", None),
            "status": getattr(args, "status", None),
            "severity": getattr(args, "severity", None),
            "next_action": getattr(args, "next_action", None),
            "notes": getattr(args, "notes", None),
        }
    )


def require_nonempty(body: dict[str, Any], label: str) -> None:
    if not body:
        raise OpkError(f"No {label} fields supplied")


def verified_write(client: OpkClient, write_response: Any, project_id: str | None = None) -> dict[str, Any]:
    written = data_of(write_response)
    resolved_project_id = project_id
    if not resolved_project_id and isinstance(written, dict):
        resolved_project_id = written.get("project_id") or written.get("id")
    verify = None
    if resolved_project_id:
        verify = client.get_project(str(resolved_project_id))
    return {"write": write_response, "verify": verify}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OPK agent REST client")
    parser.add_argument("--config", help="Path to .opk.json (otherwise auto-discover upward)")
    parser.add_argument("--base-url", help="Override OPK base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("dashboard")

    p = sub.add_parser("projects")
    p.add_argument("--q")
    p.add_argument("--status", choices=["active", "paused", "done", "archived"])

    p = sub.add_parser("context")
    p.add_argument("--project-id")
    p.add_argument("--q")

    p = sub.add_parser("create-project")
    add_common_project_fields(p, require_name=True)

    p = sub.add_parser("update-project")
    p.add_argument("project_id")
    add_common_project_fields(p)

    p = sub.add_parser("delete-project")
    p.add_argument("project_id")

    p = sub.add_parser("milestones")
    p.add_argument("--project-id")
    p.add_argument("--status", choices=["planned", "in_progress", "blocked", "done", "skipped"])

    p = sub.add_parser("add-milestone")
    p.add_argument("project_id")
    p.add_argument("--title", required=True)
    p.add_argument("--status", choices=["planned", "in_progress", "blocked", "done", "skipped"])
    p.add_argument("--due-date")
    p.add_argument("--sort-order", type=int)
    p.add_argument("--notes")

    p = sub.add_parser("update-milestone")
    p.add_argument("milestone_id")
    p.add_argument("--title")
    p.add_argument("--status", choices=["planned", "in_progress", "blocked", "done", "skipped"])
    p.add_argument("--due-date")
    p.add_argument("--sort-order", type=int)
    p.add_argument("--notes")

    p = sub.add_parser("delete-milestone")
    p.add_argument("milestone_id")

    p = sub.add_parser("issues")
    p.add_argument("--project-id")
    p.add_argument("--status", choices=["open", "in_progress", "waiting", "resolved", "closed"])
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"])

    p = sub.add_parser("add-issue")
    p.add_argument("project_id")
    p.add_argument("--title", required=True)
    p.add_argument("--milestone-id")
    p.add_argument("--description")
    p.add_argument("--status", choices=["open", "in_progress", "waiting", "resolved", "closed"])
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"])
    p.add_argument("--next-action")
    p.add_argument("--notes")

    p = sub.add_parser("update-issue")
    p.add_argument("issue_id")
    p.add_argument("--title")
    p.add_argument("--milestone-id")
    p.add_argument("--description")
    p.add_argument("--status", choices=["open", "in_progress", "waiting", "resolved", "closed"])
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"])
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
    base_url = args.base_url or os.getenv("OPK_BASE_URL") or config.get("base_url") or DEFAULT_BASE_URL
    api_key = os.getenv("OPK_API_KEY")
    if not api_key:
        raise OpkError("OPK_API_KEY is required")

    client = OpkClient(str(base_url), api_key)
    cmd = args.command

    if cmd == "health":
        pretty(client.request("/api/health"))
    elif cmd == "dashboard":
        pretty(client.dashboard())
    elif cmd == "projects":
        pretty(client.list_projects(args.q, args.status))
    elif cmd == "context":
        project = resolve_project(client, config, args.project_id, args.q)
        pretty({"config": str(config_path) if config_path else None, "project": project})
    elif cmd == "create-project":
        body = project_body(args)
        result = client.create_project(body)
        project_id = data_of(result).get("id") if isinstance(data_of(result), dict) else None
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
        body = milestone_body(args)
        pretty(verified_write(client, client.add_milestone(args.project_id, body), args.project_id))
    elif cmd == "update-milestone":
        body = milestone_body(args)
        require_nonempty(body, "milestone update")
        pretty(verified_write(client, client.update_milestone(args.milestone_id, body)))
    elif cmd == "delete-milestone":
        pretty(client.delete_milestone(args.milestone_id))
    elif cmd == "issues":
        pretty(client.list_issues(args.project_id, args.status, args.severity))
    elif cmd == "add-issue":
        body = issue_body(args)
        pretty(verified_write(client, client.add_issue(args.project_id, body), args.project_id))
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
