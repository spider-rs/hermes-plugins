"""HTTP client and result shaping for the core (REST) Spider tools.

Uses only the standard library so the plugin has zero runtime dependencies for
the core tier — important for code that runs in-process inside Hermes.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import api_url, get_api_key, max_results

# Every external request gets a timeout so a hung endpoint can't wedge Hermes.
REQUEST_TIMEOUT_S = 120


class SpiderError(RuntimeError):
    """Raised for non-2xx responses or transport failures."""


def spider_request(method: str, path: str, body: Any | None = None) -> Any:
    """Call the Spider Cloud REST API and return the parsed JSON (or raw text)."""
    url = f"{api_url()}{path}"
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
            text = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SpiderError(
            f"Spider {method} {path} returned {exc.code} {exc.reason}: {detail or '(no body)'}"
        ) from None
    except urllib.error.URLError as exc:
        raise SpiderError(f"Spider {method} {path} failed: {exc.reason}") from None
    except TimeoutError:
        raise SpiderError(
            f"Spider {method} {path} timed out after {REQUEST_TIMEOUT_S}s"
        ) from None

    return _parse_body(text)


def _parse_body(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def clean(params: dict[str, Any]) -> dict[str, Any]:
    """Drop None values so we only send parameters the caller actually set."""
    return {key: value for key, value in params.items() if value is not None}


def _result_list(payload: Any) -> list[Any] | None:
    """Find the primary results array in a Spider payload (root array or `.content`)."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("content"), list):
        return payload["content"]
    return None


def _cap_payload(payload: Any) -> tuple[Any, dict[str, Any]]:
    """Cap the primary results array to max_results(), preserving payload shape."""
    limit = max_results()
    if isinstance(payload, list):
        total = len(payload)
        capped = total > limit
        shown = min(total, limit)
        return (payload[:limit] if capped else payload), {
            "total": total,
            "shown": shown,
            "capped": capped,
        }
    if isinstance(payload, dict) and isinstance(payload.get("content"), list):
        total = len(payload["content"])
        capped = total > limit
        shown = min(total, limit)
        if capped:
            payload = {**payload, "content": payload["content"][:limit]}
        return payload, {"total": total, "shown": shown, "capped": capped}
    return payload, {"capped": False}


def spider_result(payload: Any) -> str:
    """Cap the payload and JSON-encode a success envelope for the model."""
    capped, meta = _cap_payload(payload)
    out: dict[str, Any] = {"success": True, "result": capped}
    if meta.get("capped"):
        out["truncated"] = {
            "shown": meta["shown"],
            "total": meta["total"],
            "note": f"processed first {meta['shown']} of {meta['total']} results",
        }
    return json.dumps(out, ensure_ascii=False)


def tool_error(exc: Exception) -> str:
    """Structured error envelope. Handlers return this instead of raising."""
    return json.dumps(
        {"success": False, "error": f"{type(exc).__name__}: {exc}"},
        ensure_ascii=False,
    )
