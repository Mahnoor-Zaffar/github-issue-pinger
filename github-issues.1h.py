#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime


PYTHON = os.path.expanduser("~/Desktop/job_posting/.venv/bin/python3")
SCRIPT = os.path.expanduser("~/Desktop/job_posting/github_issue_pinger.py")

out = subprocess.check_output([PYTHON, SCRIPT]).decode("utf-8")
data = json.loads(out)


def short_date(iso_str: str) -> str:
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d")
    except Exception:
        return ""


def short_title(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

total = data.get("total_recent", 0)
days_back = data.get("days_back", 7)
print(f"🪼 OSS Issues: {total} (last {days_back}d) | refresh=true")
print("---")
if data.get("error"):
    print(f"Error: {data['error']}")
    print("---")
    print("Open config | open=/Users/saba/Desktop/job_posting/github_issue_config.json")
    print("Run now | bash=/Users/saba/Desktop/job_posting/.venv/bin/python3 param1=/Users/saba/Desktop/job_posting/github_issue_pinger.py terminal=true refresh=true")
elif not data.get("items"):
    print(f"No issues opened in last {days_back} days")
    print("---")
    print("Tip: increase days_back or max_pages_per_repo")
else:
    items = data.get("items", [])
    counts = data.get("per_repo_counts", {})
    max_display = data.get("max_display", 200)

    print("By repo")
    for repo, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"{repo}: {count} | href=https://github.com/{repo}")
    print("---")

    print("Recent issues (last week)")
    for item in items[:max_display]:
        date = short_date(item.get("created_at", ""))
        title = short_title(item.get("title", ""))
        line = f"{date} • {item.get('repo')} #{item.get('number')} {title}"
        print(f"{line} | href={item.get('url')}")
print("---")
print("Open config | open=/Users/saba/Desktop/job_posting/github_issue_config.json")
print("Run now | bash=/Users/saba/Desktop/job_posting/.venv/bin/python3 param1=/Users/saba/Desktop/job_posting/github_issue_pinger.py terminal=true refresh=true")
report_path = data.get("html_report_path")
if report_path:
    print(f"Open full list (browser) | open={report_path}")
print("Open plugin folder | open=/Users/saba/Library/Application Support/SwiftBar/Plugins")
