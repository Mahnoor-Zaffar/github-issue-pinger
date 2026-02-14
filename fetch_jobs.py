#!/usr/bin/env python3
"""
Fetch newest job postings (last 6 months) for React / Frontend / Full Stack roles
using Adzuna Jobs API, and write a frontend-friendly JSON file.

Docs: https://developer.adzuna.com/  (register for APP_ID + APP_KEY)
"""

from __future__ import annotations

import os
import json
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests


ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "ae")  # ae = UAE, gb = UK, us = USA etc.
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

OUTPUT_PATH = os.getenv("OUTPUT_PATH", "jobs.json")

# Job queries you asked for
QUERIES = [
    "full stack web developer react javascript",
    "react js developer",
    "frontend developer react",
    "front end developer react",
]

# Optional filters
WHERE = os.getenv("JOB_LOCATION", "UAE")  # e.g., "UAE", "Ajman", "Dubai", "Remote"
RESULTS_PER_PAGE = 50  # Adzuna supports page size param; keep reasonable
MAX_PAGES_PER_QUERY = 6  # safety cap so you don't burn quota


def iso_to_dt(s: str) -> Optional[datetime]:
    # Adzuna often returns ISO timestamps. Be defensive.
    try:
        # Example: "2025-07-21T12:34:56Z"
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def stable_id(job: Dict[str, Any]) -> str:
    """
    Build a stable ID to dedupe across queries:
    Prefer API job 'id' if present; otherwise hash title+company+location+redirect_url
    """
    if "id" in job and job["id"]:
        return str(job["id"])
    raw = "|".join(
        [
            str(job.get("title", "")),
            str(job.get("company", {}).get("display_name", "")),
            str(job.get("location", {}).get("display_name", "")),
            str(job.get("redirect_url", "")),
        ]
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def fetch_adzuna_page(query: str, page: int) -> Dict[str, Any]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise RuntimeError(
            "Missing ADZUNA_APP_ID / ADZUNA_APP_KEY. "
            "Set them as environment variables after registering on developer.adzuna.com."
        )

    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": query,
        "where": WHERE,
        "content-type": "application/json",
        "sort_by": "date",  # newest first
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def normalize(job: Dict[str, Any]) -> Dict[str, Any]:
    created = iso_to_dt(job.get("created", "") or job.get("created_at", "") or "")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")

    return {
        "id": stable_id(job),
        "title": job.get("title"),
        "company": (job.get("company") or {}).get("display_name"),
        "location": (job.get("location") or {}).get("display_name"),
        "category": (job.get("category") or {}).get("label"),
        "created_at": created.isoformat() if created else None,
        "description_snippet": job.get("description", "")[:400] if job.get("description") else None,
        "contract_type": job.get("contract_type"),
        "contract_time": job.get("contract_time"),  # full_time/part_time
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": job.get("salary_is_predicted") and job.get("salary_is_predicted"),
        "apply_url": job.get("redirect_url"),
        "source": "Adzuna",
    }


def main() -> None:
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=183)

    all_jobs: Dict[str, Dict[str, Any]] = {}
    meta: Dict[str, Any] = {
        "generated_at": now.isoformat(),
        "country": ADZUNA_COUNTRY,
        "where": WHERE,
        "queries": QUERIES,
        "sources": ["Adzuna"],
        "note": "Results filtered to last ~6 months and deduplicated across queries.",
    }

    for q in QUERIES:
        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            data = fetch_adzuna_page(q, page)
            results = data.get("results", []) or []
            if not results:
                break

            # Stop early if results already too old (since sorted by date desc)
            oldest_dt: Optional[datetime] = None

            for job in results:
                norm = normalize(job)
                created_at = iso_to_dt(norm["created_at"]) if norm.get("created_at") else None
                if created_at:
                    if not oldest_dt or created_at < oldest_dt:
                        oldest_dt = created_at
                    if created_at < six_months_ago:
                        continue  # too old

                all_jobs[norm["id"]] = norm

            if oldest_dt and oldest_dt < six_months_ago:
                break

            time.sleep(0.2)  # be gentle on API

    # sort newest first
    jobs_list = list(all_jobs.values())
    jobs_list.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    out = {"meta": meta, "jobs": jobs_list}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(jobs_list)} jobs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
