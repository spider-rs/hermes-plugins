"""Stateful remote-browser automation backed by the `spider-browser` package.

The `spider-browser` SDK is async and each session is bound to the event loop
that created it. Hermes tool handlers are synchronous, so this module owns a
single dedicated background event-loop thread; every browser session lives on
that one loop, and the sync handlers block on it via run_coroutine_threadsafe.

Open sessions bill until closed, so sessions auto-close after 5 minutes of
inactivity and are all closed on session end / process exit.

Requires `pip install spider-browser` in Hermes' environment and SPIDER_API_KEY.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import threading
import uuid
from typing import Any

from .config import browser_server_url, get_api_key
from .client import tool_error

SESSION_TIMEOUT_S = 5 * 60
MAX_SESSIONS = 5

# How long a synchronous handler will block waiting on the browser loop.
_OPEN_TIMEOUT_S = 300
_OP_TIMEOUT_S = 180

# ---------------------------------------------------------------------------
# Dedicated event-loop thread
# ---------------------------------------------------------------------------

_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()

# Session state. All mutation happens on the loop thread, so the dict is only
# ever touched single-threaded (status reads of len() are best-effort).
_sessions: dict[str, dict[str, Any]] = {}


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=loop.run_forever, name="spider-browser-loop", daemon=True
            )
            thread.start()
            _loop = loop
    return _loop


def _run(coro: Any, timeout: float) -> Any:
    future = asyncio.run_coroutine_threadsafe(coro, _ensure_loop())
    return future.result(timeout=timeout)


# ---------------------------------------------------------------------------
# Session management (runs on the loop thread)
# ---------------------------------------------------------------------------


def _arm_timer(session_id: str) -> None:
    session = _sessions.get(session_id)
    if session is None:
        return
    timer = session.get("timer")
    if timer is not None:
        timer.cancel()
    loop = asyncio.get_running_loop()
    session["timer"] = loop.call_later(
        SESSION_TIMEOUT_S, lambda: asyncio.ensure_future(_close(session_id))
    )


def _get_session(session_id: str) -> dict[str, Any]:
    session = _sessions.get(session_id)
    if session is None:
        raise ValueError(
            f"No active browser session '{session_id}'. Open one with spider_browser_open. "
            "Sessions expire after 5 minutes of inactivity."
        )
    _arm_timer(session_id)
    return session


async def _open(browser_choice: str | None, stealth: int | None) -> dict[str, Any]:
    if len(_sessions) >= MAX_SESSIONS:
        raise RuntimeError(
            f"Maximum {MAX_SESSIONS} concurrent browser sessions reached. Close one with "
            "spider_browser_close before opening another."
        )
    # Imported lazily so the core tier never pays for the SDK and a missing SDK
    # only fails the browser tools, with a clear message.
    try:
        from spider_browser import SpiderBrowser, SpiderBrowserOptions
    except ImportError as exc:
        raise RuntimeError(
            "The browser tier needs the 'spider-browser' package. Install it in Hermes' "
            "environment: pip install spider-browser"
        ) from exc

    server_url = browser_server_url()
    options = SpiderBrowserOptions(
        api_key=get_api_key(),
        browser=browser_choice or "auto",
        stealth=stealth or 0,
        **({"server_url": server_url} if server_url else {}),
    )
    browser = SpiderBrowser(options)
    await browser.init()

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"browser": browser, "browser_type": browser.browser, "timer": None}
    _arm_timer(session_id)
    return {"session_id": session_id, "browser": browser.browser}


async def _close(session_id: str) -> int:
    session = _sessions.pop(session_id, None)
    if session is not None:
        timer = session.get("timer")
        if timer is not None:
            timer.cancel()
        try:
            await session["browser"].close()
        except Exception:  # noqa: BLE001 - closing must never raise
            pass
    return len(_sessions)


async def _close_all() -> int:
    ids = list(_sessions.keys())
    for session_id in ids:
        await _close(session_id)
    return len(ids)


# ---------------------------------------------------------------------------
# Page operations (run on the loop thread)
# ---------------------------------------------------------------------------


async def _navigate(session_id: str, url: str) -> dict[str, Any]:
    browser = _get_session(session_id)["browser"]
    await browser.goto(url)
    page = browser.page
    return {"url": await page.url(), "title": await page.title()}


async def _click(session_id: str, selector: str, timeout_ms: int) -> dict[str, Any]:
    page = _get_session(session_id)["browser"].page
    await page.wait_for_selector(selector, timeout_ms)
    await page.click(selector)
    return {"clicked": selector, "url": await page.url()}


async def _fill(session_id: str, selector: str, value: str, timeout_ms: int) -> dict[str, Any]:
    page = _get_session(session_id)["browser"].page
    await page.wait_for_selector(selector, timeout_ms)
    await page.fill(selector, value)
    return {"filled": selector, "value_length": len(value)}


async def _screenshot(session_id: str) -> dict[str, Any]:
    page = _get_session(session_id)["browser"].page
    data = await page.screenshot()  # base64 PNG string
    return {"format": "png_base64", "data": data, "length": len(data)}


async def _content(session_id: str, fmt: str) -> dict[str, Any]:
    page = _get_session(session_id)["browser"].page
    if fmt == "text":
        content = str(await page.evaluate("document.body.innerText"))
    else:
        content = await page.raw_content()
    return {
        "url": await page.url(),
        "title": await page.title(),
        "content": content,
        "length": len(content),
    }


async def _evaluate(session_id: str, expression: str) -> dict[str, Any]:
    page = _get_session(session_id)["browser"].page
    return {"result": await page.evaluate(expression)}


async def _wait_for(
    session_id: str, selector: str | None, navigation: bool, timeout_ms: int
) -> dict[str, Any]:
    page = _get_session(session_id)["browser"].page
    if selector:
        await page.wait_for_selector(selector, timeout_ms)
        waited = f"selector {selector}"
    elif navigation:
        await page.wait_for_navigation(timeout_ms)
        waited = "navigation"
    else:
        await page.wait_for_network_idle(timeout_ms)
        waited = "network idle"
    return {"waited_for": waited, "url": await page.url()}


# ---------------------------------------------------------------------------
# Synchronous tool handlers
# ---------------------------------------------------------------------------


def _ok(payload: Any) -> str:
    return json.dumps({"success": True, **payload}, ensure_ascii=False)


def handle_open(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        return _ok(_run(_open(args.get("browser"), args.get("stealth")), _OPEN_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def _require(args: dict[str, Any], field: str) -> Any:
    value = args.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field}' must be a non-empty string")
    return value


def handle_navigate(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        return _ok(_run(_navigate(_require(args, "session_id"), _require(args, "url")), _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_click(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        timeout = int(args.get("timeout") or 10000)
        coro = _click(_require(args, "session_id"), _require(args, "selector"), timeout)
        return _ok(_run(coro, _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_fill(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        timeout = int(args.get("timeout") or 10000)
        value = args.get("value")
        if not isinstance(value, str):
            raise ValueError("'value' must be a string")
        coro = _fill(_require(args, "session_id"), _require(args, "selector"), value, timeout)
        return _ok(_run(coro, _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_screenshot(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        return _ok(_run(_screenshot(_require(args, "session_id")), _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_content(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        fmt = args.get("format") or "html"
        return _ok(_run(_content(_require(args, "session_id"), fmt), _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_evaluate(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        coro = _evaluate(_require(args, "session_id"), _require(args, "expression"))
        return _ok(_run(coro, _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_wait_for(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        timeout = int(args.get("timeout") or 30000)
        coro = _wait_for(
            _require(args, "session_id"),
            args.get("selector"),
            bool(args.get("navigation")),
            timeout,
        )
        return _ok(_run(coro, _OP_TIMEOUT_S))
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


def handle_close(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    try:
        remaining = _run(_close(_require(args, "session_id")), _OP_TIMEOUT_S)
        return _ok({"closed": args["session_id"], "remaining": remaining})
    except Exception as exc:  # noqa: BLE001
        return tool_error(exc)


# ---------------------------------------------------------------------------
# Lifecycle helpers (used by commands / hooks / atexit)
# ---------------------------------------------------------------------------


def session_count() -> int:
    return len(_sessions)


def close_all_sessions() -> int:
    """Close every open session. Safe to call from any thread."""
    if not _sessions:
        return 0
    try:
        return _run(_close_all(), _OP_TIMEOUT_S)
    except Exception:  # noqa: BLE001 - best effort on shutdown
        return 0


# Never leak a billing session if Hermes exits without firing its hook.
atexit.register(close_all_sessions)
