from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err


def get_job_details(job_id: str = "", country: str = "us") -> dict[str, Any]:
    key = os.getenv("RAPIDAPI_KEY")
    host = os.getenv("RAPIDAPI_JSEARCH_HOST", "jsearch.p.rapidapi.com")
    if not key:
        raise RuntimeError("Missing RAPIDAPI_KEY env var")
    if not job_id:
        return err("job_details", ValueError("Missing job_id parameter"))

    try:
        response = requests.get(
            f"https://{host}/job-details",
            params={"job_id": job_id, "country": country},
            headers={
                "x-rapidapi-key": key,
                "x-rapidapi-host": host,
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        raw_items = data.get("data") or []
        if raw_items:
            item = raw_items[0]
            city = item.get("job_city") or ""
            country_name = item.get("job_country") or ""
            loc_str = f"{city}, {country_name}".strip(", ")
            details = {
                "job_id": job_id,
                "title": item.get("job_title", ""),
                "employer": item.get("employer_name", ""),
                "employer_website": item.get("employer_website", ""),
                "location": loc_str or item.get("job_location", ""),
                "is_remote": item.get("job_is_remote", False),
                "employment_type": item.get("job_employment_type", ""),
                "salary": item.get("job_salary_string") or item.get("job_salary", ""),
                "description": (item.get("job_description") or "")[:1500],
                "apply_link": item.get("job_apply_link") or item.get("job_google_link") or "",
                "qualifications": (item.get("job_highlights") or {}).get("Qualifications", []),
                "responsibilities": (item.get("job_highlights") or {}).get("Responsibilities", []),
                "benefits": item.get("job_benefits_strings") or (item.get("job_highlights") or {}).get("Benefits", []),
                "source": "JSearch job-details",
            }
            return {"tool": "job_details", "job_id": job_id, "details": details}

        return {"tool": "job_details", "job_id": job_id, "details": None, "message": "No job details found for this job_id"}
    except Exception as exc:
        return err("job_details", exc)
