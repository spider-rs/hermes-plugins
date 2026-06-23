"""Handlers for the core (REST) Spider tools.

Every handler accepts an args dict plus **kwargs, catches operational errors,
and returns a JSON-encoded string for both success and failure.
"""

from __future__ import annotations

from typing import Any, Callable

from .client import clean, spider_request, spider_result, tool_error


def _require_nonempty_str(args: dict[str, Any], field: str) -> None:
    value = args.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field}' must be a non-empty string")


def _post_handler(path: str, required_field: str) -> Callable[..., str]:
    """Build a handler that validates one required string field and POSTs the args."""

    def handler(args: dict[str, Any], **kwargs: Any) -> str:
        del kwargs
        try:
            _require_nonempty_str(args, required_field)
            return spider_result(spider_request("POST", path, clean(args)))
        except Exception as exc:  # noqa: BLE001 - return structured error, never raise
            return tool_error(exc)

    return handler


handle_scrape = _post_handler("/scrape", "url")
handle_crawl = _post_handler("/crawl", "url")
handle_links = _post_handler("/links", "url")
handle_screenshot = _post_handler("/screenshot", "url")
handle_unblocker = _post_handler("/unblocker", "url")
handle_search = _post_handler("/search", "search")


def handle_transform(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        data = args.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError("'data' must be a non-empty array of {html, url?} objects")
        return spider_result(spider_request("POST", "/transform", clean(args)))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_get_credits(args: dict[str, Any], **kwargs: Any) -> str:
    del args, kwargs
    try:
        return spider_result(spider_request("GET", "/data/credits", None))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)
