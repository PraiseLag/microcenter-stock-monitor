# discord_http.py
#
# Small HTTP helper for Discord webhook calls:
# - Retries with backoff for 429/502/503/504
# - Never raises to caller unless explicitly requested

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests


RETRY_STATUS = {429, 502, 503, 504}


def request_with_retry(
    method: str,
    url: str,
    *,
    json: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
    max_attempts: int = 6,
    initial_backoff_seconds: float = 1.0,
) -> requests.Response | None:
    backoff = float(initial_backoff_seconds)

    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.request(method, url, json=json, timeout=timeout)
        except Exception:
            r = None

        if r is not None:
            if 200 <= r.status_code < 300:
                return r

            if r.status_code not in RETRY_STATUS:
                return r

            # Respect Discord's retry_after if present
            if r.status_code == 429:
                try:
                    data = r.json()
                    retry_after = float(data.get("retry_after", 0))
                    if retry_after > 0:
                        time.sleep(retry_after)
                        continue
                except Exception:
                    pass

        time.sleep(backoff)
        backoff = min(backoff * 2.0, 30.0)

    return r
