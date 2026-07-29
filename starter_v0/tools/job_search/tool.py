from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err


def search_jobs(
    query: str = "",
    num_pages: int = 1,
    country: str = "us",
    date_posted: str = "all",
) -> dict[str, Any]:
    key = os.getenv("RAPIDAPI_KEY")
    host = os.getenv("RAPIDAPI_JSEARCH_HOST", "jsearch.p.rapidapi.com")
    if not key:
        raise RuntimeError("Missing RAPIDAPI_KEY env var")

    try:
        response = requests.get(
            f"https://{host}/search-v2",
            params={
                "query": query,
                "num_pages": str(num_pages),
                "country": country,
                "date_posted": date_posted,
            },
            headers={
                "x-rapidapi-key": key,
                "x-rapidapi-host": host,
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        raw_jobs = (data.get("data") or {}).get("jobs") or []
        items = []
        for item in raw_jobs[:5]:
            city = item.get("job_city") or ""
            country_name = item.get("job_country") or ""
            loc_str = f"{city}, {country_name}".strip(", ")
            items.append({
                "title": item.get("job_title", ""),
                "employer": item.get("employer_name", ""),
                "location": loc_str or ("Remote" if item.get("job_is_remote") else ""),
                "summary": (item.get("job_description") or "")[:200],
                "url": item.get("job_apply_link") or item.get("job_google_link") or "",
                "source": "JSearch",
            })
        return {"tool": "job_search", "query": query, "items": items}
    except Exception as exc:
        return err("job_search", exc)
