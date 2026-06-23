"""hermes-spider-tools

Native Hermes Agent tools for the Spider Cloud API (https://spider.cloud):
a stateless Core REST tier and a stateful remote-Browser tier.

Ported from the pi-spider-tools Pi extension. Get a key at
https://spider.cloud/api-keys.
"""

from __future__ import annotations

from typing import Any, Callable

from . import browser, browser_schemas, commands, schemas, tools
from .config import has_api_key
from .constants import TOOLSET_BROWSER, TOOLSET_CORE
from .settings import is_enabled

# (schema, handler) pairs for each tier. The schema's "name" is the tool name.
_CORE_TOOLS: list[tuple[dict, Callable[..., str]]] = [
    (schemas.SCRAPE, tools.handle_scrape),
    (schemas.CRAWL, tools.handle_crawl),
    (schemas.SEARCH, tools.handle_search),
    (schemas.LINKS, tools.handle_links),
    (schemas.SCREENSHOT, tools.handle_screenshot),
    (schemas.UNBLOCKER, tools.handle_unblocker),
    (schemas.TRANSFORM, tools.handle_transform),
    (schemas.GET_CREDITS, tools.handle_get_credits),
]

_BROWSER_TOOLS: list[tuple[dict, Callable[..., str]]] = [
    (browser_schemas.OPEN, browser.handle_open),
    (browser_schemas.NAVIGATE, browser.handle_navigate),
    (browser_schemas.CLICK, browser.handle_click),
    (browser_schemas.FILL, browser.handle_fill),
    (browser_schemas.SCREENSHOT, browser.handle_screenshot),
    (browser_schemas.CONTENT, browser.handle_content),
    (browser_schemas.EVALUATE, browser.handle_evaluate),
    (browser_schemas.WAIT_FOR, browser.handle_wait_for),
    (browser_schemas.CLOSE, browser.handle_close),
]


def _make_check(tool_name: str) -> Callable[..., bool]:
    """A tool is available when the key is set and the user hasn't disabled it.

    Evaluated by Hermes at availability time, so /spider enable|disable is live.
    """

    def check(**kwargs: Any) -> bool:
        del kwargs
        try:
            return has_api_key() and is_enabled(tool_name)
        except Exception:  # noqa: BLE001 - never let availability checks crash Hermes
            return has_api_key()

    return check


def register(ctx: Any) -> None:
    """Register the Spider Cloud tools, commands, and lifecycle hooks."""
    for toolset, entries in ((TOOLSET_CORE, _CORE_TOOLS), (TOOLSET_BROWSER, _BROWSER_TOOLS)):
        for schema, handler in entries:
            ctx.register_tool(
                name=schema["name"],
                toolset=toolset,
                schema=schema,
                handler=handler,
                check_fn=_make_check(schema["name"]),
                description=schema["description"],
                emoji="🕷",
            )

    ctx.register_command(
        "spider",
        handler=commands.handle_spider_command,
        description="Spider Cloud tools: status, enable/disable, and help",
    )
    ctx.register_command(
        "spider-browser",
        handler=commands.handle_browser_command,
        description="Spider browser sessions: status, close all, and help",
    )

    # Close any open remote-browser sessions when a session ends, so we never
    # leak a billing session. atexit covers hard process exits as a backstop.
    ctx.register_hook("on_session_end", _on_session_end)


def _on_session_end(**kwargs: Any) -> None:
    del kwargs
    browser.close_all_sessions()
