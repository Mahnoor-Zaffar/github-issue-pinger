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


def _next_request_timeout(
    request_timeout_seconds: int, deadline_monotonic: float | None
) -> float:
    timeout = max(1, int(request_timeout_seconds))
    if deadline_monotonic is None:
        return float(timeout)
    remaining = deadline_monotonic - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Runtime budget reached")
    return max(1.0, min(float(timeout), remaining))


def _label_text_color(bg_hex: str) -> str:
    """Return black or white text for label background."""
    try:
        r = int(bg_hex[0:2], 16)
        g = int(bg_hex[2:4], 16)
        b = int(bg_hex[4:6], 16)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#1f2328" if lum > 0.5 else "#ffffff"
    except Exception:
        return "#1f2328"


def _format_date(iso_str: str) -> str:
    """Convert ISO date to readable format (e.g. Feb 14, 2 days ago)."""
    import datetime as dt
    try:
        d = dt.datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S")
        now = dt.datetime.now(dt.timezone.utc)
        d = d.replace(tzinfo=dt.timezone.utc)
        delta = now - d
        if delta.days == 0:
            return "Today"
        if delta.days == 1:
            return "Yesterday"
        if delta.days < 7:
            return f"{delta.days}d ago"
        return d.strftime("%b %d")
    except Exception:
        return iso_str[:10]


def write_html_report(path: str, items: List[Dict[str, Any]], days_back: int) -> None:
    rows = []
    for item in items:
        title = item.get("title", "").replace("<", "&lt;").replace(">", "&gt;")
        repo = item.get("repo", "").replace("<", "&lt;").replace(">", "&gt;")
        created = item.get("created_at", "")
        url = item.get("url", "")
        labels = item.get("labels", [])
        date_str = _format_date(created)
        repo_short = repo.split("/")[-1] if "/" in repo else repo
        label_spans = "".join(
            f'<span class="label" style="background:#{lb.get("color","ededed")};color:{_label_text_color(lb.get("color","ededed"))}">{lb.get("name","")}</span>'
            for lb in labels
        ) or '<span class="label-empty">—</span>'
        rows.append(
            f'<tr><td class="date">{date_str}</td>'
            f'<td class="repo"><a href="https://github.com/{repo}" target="_blank">{repo_short}</a></td>'
            f'<td class="title"><a href="{url}" target="_blank">{title}</a></td>'
            f'<td class="labels">{label_spans}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GitHub Issues (last {days_back} days)</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 24px;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
    }}
    .container {{ max-width: 960px; margin: 0 auto; }}
    h1 {{
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0 0 20px;
      color: #f0f6fc;
    }}
    .meta {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #21262d; }}
    th {{
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #8b949e;
      background: #161b22;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    tr:hover {{ background: #161b22; }}
    .date {{ white-space: nowrap; color: #8b949e; font-size: 0.85rem; width: 90px; }}
    .repo {{ width: 140px; }}
    .repo a {{
      color: #58a6ff;
      text-decoration: none;
      font-size: 0.9rem;
    }}
    .repo a:hover {{ text-decoration: underline; }}
    .title a {{
      color: #e6edf3;
      text-decoration: none;
      font-size: 0.95rem;
      line-height: 1.4;
    }}
    .title a:hover {{ color: #58a6ff; text-decoration: underline; }}
    .labels {{ max-width: 180px; }}
    .label {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 500;
      margin-right: 4px;
      margin-bottom: 2px;
    }}
    .label-empty {{ color: #8b949e; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>GitHub Issues (last {days_back} days)</h1>
    <p class="meta">{len(items)} issues from your forked repos</p>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Repo</th>
          <th>Title</th>
          <th>Labels</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def gh_get(
    url: str,
    token: str | None,
    request_timeout_seconds: int = 20,
    deadline_monotonic: float | None = None,
) -> Any:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    timeout = _next_request_timeout(request_timeout_seconds, deadline_monotonic)
    r = requests.get(url, headers=headers, timeout=timeout)
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


def list_forked_repos(
    username: str,
    token: str | None,
    max_repos: int,
    request_timeout_seconds: int,
    deadline_monotonic: float | None,
) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1
    while len(repos) < max_repos:
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            break
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?per_page=100&page={page}&sort=updated&direction=desc"
        )
        try:
            batch = gh_get(url, token, request_timeout_seconds, deadline_monotonic)
        except TimeoutError:
            break
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
    fork_full_name: str,
    token: str | None,
    use_parent_issues: bool,
    request_timeout_seconds: int,
    deadline_monotonic: float | None,
) -> str:
    if not use_parent_issues:
        return fork_full_name
    url = f"https://api.github.com/repos/{fork_full_name}"
    try:
        repo = gh_get(url, token, request_timeout_seconds, deadline_monotonic)
    except TimeoutError:
        return fork_full_name
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
    request_timeout_seconds: int,
    deadline_monotonic: float | None,
) -> List[Dict[str, Any]]:
    recent: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            break
        url = (
            f"https://api.github.com/repos/{repo_full_name}/issues"
            f"?state=open&per_page={results_per_page}&page={page}&sort=created&direction=desc"
        )
        items = gh_get(url, token, request_timeout_seconds, deadline_monotonic)
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
            "request_timeout_seconds": 15,
            "max_runtime_seconds": 50,
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
    request_timeout_seconds = int(cfg.get("request_timeout_seconds", 15))
    max_runtime_seconds = int(cfg.get("max_runtime_seconds", 50))
    deadline_monotonic = (
        time.monotonic() + max_runtime_seconds if max_runtime_seconds > 0 else None
    )
    now_epoch = int(time.time())
    cutoff_epoch = now_epoch - (days_back * 24 * 60 * 60)

    if not username or username in ("your_github_username", "${GITHUB_USERNAME}"):
        raise SystemExit(
            "Set github_username in github_issue_config.json or GITHUB_USERNAME env var"
        )

    try:
        repos = list_forked_repos(
            username,
            token,
            max_repos,
            request_timeout_seconds,
            deadline_monotonic,
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

    new_items: List[Dict[str, Any]] = []
    total_recent = 0
    per_repo_counts: Dict[str, int] = {}
    processed_repos = 0
    partial = False
    warning = ""

    for repo in repos:
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            partial = True
            warning = (
                f"Runtime budget reached after processing {processed_repos} repos; "
                "results are partial."
            )
            break
        fork_full_name = repo.get("full_name")
        if not fork_full_name:
            continue
        try:
            issue_repo = resolve_issue_repo(
                fork_full_name,
                token,
                use_parent_issues,
                request_timeout_seconds,
                deadline_monotonic,
            )
            issues = fetch_recent_issues(
                issue_repo,
                token,
                include_prs,
                results_per_page,
                max_pages_per_repo,
                cutoff_epoch,
                request_timeout_seconds,
                deadline_monotonic,
            )
        except TimeoutError:
            partial = True
            warning = (
                f"Runtime budget reached after processing {processed_repos} repos; "
                "results are partial."
            )
            break
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
                labels = [
                    {"name": lb.get("name", ""), "color": lb.get("color", "ededed")}
                    for lb in it.get("labels", [])
                ]
                new_items.append(
                    {
                        "repo": issue_repo,
                        "source_repo": fork_full_name,
                        "number": it.get("number"),
                        "title": it.get("title"),
                        "url": it.get("html_url"),
                        "created_at": created_at,
                        "labels": labels,
                    }
                )

        per_repo_counts[issue_repo] = repo_recent
        state["last_seen"][issue_repo] = newest_epoch
        processed_repos += 1

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
        "processed_repos": processed_repos,
        "fetched_fork_repos": len(repos),
        "partial": partial,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if warning:
        output["warning"] = warning
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
