#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.getenv("GITHUB_ISSUE_CONFIG", os.path.join(BASE_DIR, "github_issue_config.json"))
STATE_PATH = os.getenv("GITHUB_ISSUE_STATE", os.path.join(BASE_DIR, "github_issue_state.json"))
HTML_REPORT_PATH = os.getenv("GITHUB_ISSUE_HTML", os.path.join(BASE_DIR, "github_issues_report.html"))


def load_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_html_report(path: str, items: List[Dict[str, Any]], days_back: int) -> None:
    rows = []
    for item in items:
        title = item.get("title", "")
        repo = item.get("repo", "")
        created = item.get("created_at", "")
        url = item.get("url", "")
        rows.append(
            f"<tr>"
            f"<td>{created}</td>"
            f"<td>{repo}</td>"
            f"<td><a href=\"{url}\" target=\"_blank\">{title}</a></td>"
            f"</tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GitHub Issues (last {days_back} days)</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; margin: 24px; }}
    h1 {{ margin: 0 0 12px; font-size: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
    th {{ background: #f7f7f7; position: sticky; top: 0; }}
    a {{ color: #0a58ca; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Issues opened in last {days_back} days</h1>
  <table>
    <thead>
      <tr>
        <th>Created</th>
        <th>Repo</th>
        <th>Title</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def gh_get(url: str, token: str | None) -> Any:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
        reset = r.headers.get("X-RateLimit-Reset")
        reset_note = f" (resets at {reset})" if reset else ""
        raise RuntimeError(f"GitHub rate limit exceeded{reset_note}. Add GITHUB_TOKEN.")
    r.raise_for_status()
    return r.json()


def iso_to_epoch(iso_str: str) -> int:
    try:
        return int(time.mktime(time.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")))
    except Exception:
        return 0


def list_forked_repos(username: str, token: str | None, max_repos: int) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1
    while len(repos) < max_repos:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?per_page=100&page={page}&sort=updated&direction=desc"
        )
        batch = gh_get(url, token)
        if not batch:
            break
        for repo in batch:
            if repo.get("fork"):
                repos.append(repo)
                if len(repos) >= max_repos:
                    break
        page += 1
    return repos


def resolve_issue_repo(
    fork_full_name: str, token: str | None, use_parent_issues: bool
) -> str:
    if not use_parent_issues:
        return fork_full_name
    url = f"https://api.github.com/repos/{fork_full_name}"
    repo = gh_get(url, token)
    parent = repo.get("parent") or repo.get("source")
    if parent and parent.get("full_name"):
        return parent["full_name"]
    return fork_full_name


def fetch_open_issues(
    repo_full_name: str, token: str | None, include_prs: bool, max_issues: int
) -> List[Dict[str, Any]]:
    url = (
        f"https://api.github.com/repos/{repo_full_name}/issues"
        f"?state=open&per_page={max_issues}&sort=created&direction=desc"
    )
    items = gh_get(url, token)
    if include_prs:
        return items
    return [it for it in items if "pull_request" not in it]


def fetch_recent_issues(
    repo_full_name: str,
    token: str | None,
    include_prs: bool,
    results_per_page: int,
    max_pages: int,
    cutoff_epoch: int,
) -> List[Dict[str, Any]]:
    recent: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        url = (
            f"https://api.github.com/repos/{repo_full_name}/issues"
            f"?state=open&per_page={results_per_page}&page={page}&sort=created&direction=desc"
        )
        items = gh_get(url, token)
        if not items:
            break
        if not include_prs:
            items = [it for it in items if "pull_request" not in it]

        oldest_epoch = None
        for it in items:
            created_at = it.get("created_at", "")
            created_epoch = iso_to_epoch(created_at)
            if oldest_epoch is None or created_epoch < oldest_epoch:
                oldest_epoch = created_epoch
            if created_epoch >= cutoff_epoch:
                recent.append(it)

        if oldest_epoch is not None and oldest_epoch < cutoff_epoch:
            break
    return recent


def main() -> None:
    cfg = load_json(
        CONFIG_PATH,
        {
            "github_username": "your_github_username",
            "github_token": "",
            "include_prs": False,
            "max_issues_per_repo": 10,
            "max_repos": 50,
            "days_back": 7,
            "results_per_page": 100,
            "max_pages_per_repo": 3,
            "use_parent_issues": True,
        },
    )
    state = load_json(STATE_PATH, {"last_seen": {}})

    token = os.getenv("GITHUB_TOKEN") or cfg.get("github_token") or None
    username = (
        os.getenv("GITHUB_USERNAME")
        or cfg.get("github_username")
        or ""
    )
    include_prs = bool(cfg.get("include_prs", False))
    max_issues = int(cfg.get("max_issues_per_repo", 10))
    max_repos = int(cfg.get("max_repos", 50))
    days_back = int(cfg.get("days_back", 7))
    results_per_page = int(cfg.get("results_per_page", 100))
    max_pages_per_repo = int(cfg.get("max_pages_per_repo", 3))
    use_parent_issues = bool(cfg.get("use_parent_issues", True))
    now_epoch = int(time.time())
    cutoff_epoch = now_epoch - (days_back * 24 * 60 * 60)

    if not username or username in ("your_github_username", "${GITHUB_USERNAME}"):
        raise SystemExit(
            "Set github_username in github_issue_config.json or GITHUB_USERNAME env var"
        )

    try:
        repos = list_forked_repos(username, token, max_repos)
    except Exception as exc:
        output = {
            "total_new": 0,
            "items": [],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": str(exc),
        }
        print(json.dumps(output, indent=2))
        return

    new_items: List[Dict[str, Any]] = []
    total_recent = 0
    per_repo_counts: Dict[str, int] = {}

    for repo in repos:
        fork_full_name = repo.get("full_name")
        if not fork_full_name:
            continue
        try:
            issue_repo = resolve_issue_repo(fork_full_name, token, use_parent_issues)
            issues = fetch_recent_issues(
                issue_repo,
                token,
                include_prs,
                results_per_page,
                max_pages_per_repo,
                cutoff_epoch,
            )
        except Exception as exc:
            output = {
                "total_new": 0,
                "items": [],
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": str(exc),
            }
            print(json.dumps(output, indent=2))
            return

        newest_epoch = 0
        repo_recent = 0
        for it in issues:
            created_at = it.get("created_at", "")
            created_epoch = iso_to_epoch(created_at)
            if created_epoch > newest_epoch:
                newest_epoch = created_epoch
            if created_epoch >= cutoff_epoch:
                repo_recent += 1
                total_recent += 1
                new_items.append(
                    {
                        "repo": issue_repo,
                        "source_repo": fork_full_name,
                        "number": it.get("number"),
                        "title": it.get("title"),
                        "url": it.get("html_url"),
                        "created_at": created_at,
                    }
                )

        per_repo_counts[issue_repo] = repo_recent
        state["last_seen"][issue_repo] = newest_epoch

    save_json(STATE_PATH, state)
    write_html_report(HTML_REPORT_PATH, new_items, days_back)

    new_items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    output = {
        "total_recent": total_recent,
        "per_repo_counts": per_repo_counts,
        "days_back": days_back,
        "max_display": int(cfg.get("max_display", 200)),
        "html_report_path": HTML_REPORT_PATH,
        "items": new_items,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
