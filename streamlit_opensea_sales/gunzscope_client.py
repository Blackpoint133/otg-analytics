"""Secret-safe client for the GUNZscope free supply API."""
from __future__ import annotations

import os
import time
from typing import Any, Mapping

import requests

BASE_URL = "https://gunzscope.xyz/api/v1/supply"
MAX_BATCH_ITEMS = 100
DEFAULT_TIMEOUT = (5.0, 15.0)
USER_AGENT = "OTG-Analytics/staging gunzscope-supply"


class GunzscopeError(RuntimeError):
    """Provider error without credentials or response-body leakage."""


def _retry_after(response: requests.Response) -> float:
    try:
        return min(max(float(response.headers.get("Retry-After", "2")), 0.0), 60.0)
    except (TypeError, ValueError):
        return 2.0


def _validate_batch_payload(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("results"), Mapping):
        raise GunzscopeError("GUNZscope batch response has invalid shape")
    return payload


def fetch_batch(items: list[dict[str, str]], *, session=None, timeout=DEFAULT_TIMEOUT, max_attempts=3, sleep=time.sleep):
    if not 1 <= len(items) <= MAX_BATCH_ITEMS:
        raise ValueError("batch must contain 1..100 items")
    api_key = os.getenv("API_GUNZSCOPE", "").strip()
    if not api_key:
        raise GunzscopeError("API_GUNZSCOPE is not configured")
    client = session or requests.Session()
    headers = {"X-API-Key": api_key, "User-Agent": USER_AGENT, "Content-Type": "application/json"}
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.post(BASE_URL + "/batch", json={"items": items}, headers=headers, timeout=timeout)
            if response.status_code == 429:
                if attempt == max_attempts:
                    raise GunzscopeError("GUNZscope rate limit exceeded")
                sleep(_retry_after(response))
                continue
            if response.status_code >= 500:
                if attempt == max_attempts:
                    raise GunzscopeError(f"GUNZscope server error HTTP {response.status_code}")
                sleep(min(2 ** (attempt - 1), 8))
                continue
            if response.status_code >= 400:
                raise GunzscopeError(f"GUNZscope request rejected HTTP {response.status_code}")
            try:
                return _validate_batch_payload(response.json())
            except ValueError as exc:
                raise GunzscopeError("GUNZscope returned malformed JSON") from exc
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt == max_attempts:
                raise GunzscopeError("GUNZscope network request failed") from exc
            sleep(min(2 ** (attempt - 1), 8))
    raise GunzscopeError("GUNZscope request failed") from last_error


def fetch_item(name: str, rarity: str | None = None, *, session=None, timeout=DEFAULT_TIMEOUT):
    """Fetch one documented item for a bounded staging sanity check."""
    api_key = os.getenv("API_GUNZSCOPE", "").strip()
    if not api_key:
        raise GunzscopeError("API_GUNZSCOPE is not configured")
    params = {"name": name}
    if rarity:
        params["rarity"] = rarity
    client = session or requests.Session()
    response = client.get(
        BASE_URL + "/item",
        params=params,
        headers={"X-API-Key": api_key, "User-Agent": USER_AGENT},
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise GunzscopeError(f"GUNZscope item request rejected HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise GunzscopeError("GUNZscope returned malformed JSON") from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("items"), list):
        raise GunzscopeError("GUNZscope item response has invalid shape")
    return payload
