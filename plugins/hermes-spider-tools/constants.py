"""Canonical names shared across the plugin.

Kept in one tiny module so the schema, handler, settings, and command layers all
agree on tool names without importing each other (avoids circular imports).
"""

from __future__ import annotations

# Toolsets group tools in Hermes' UI / tool listing.
TOOLSET_CORE = "spider"
TOOLSET_BROWSER = "spider_browser"

CORE_TOOL_NAMES: tuple[str, ...] = (
    "spider_scrape",
    "spider_crawl",
    "spider_search",
    "spider_links",
    "spider_screenshot",
    "spider_unblocker",
    "spider_transform",
    "spider_get_credits",
)

BROWSER_TOOL_NAMES: tuple[str, ...] = (
    "spider_browser_open",
    "spider_browser_navigate",
    "spider_browser_click",
    "spider_browser_fill",
    "spider_browser_screenshot",
    "spider_browser_content",
    "spider_browser_evaluate",
    "spider_browser_wait_for",
    "spider_browser_close",
)

ALL_TOOL_NAMES: tuple[str, ...] = CORE_TOOL_NAMES + BROWSER_TOOL_NAMES
