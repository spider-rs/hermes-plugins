"""Model-facing JSON schemas for the stateful browser tools.

`spider_browser_open` returns a session_id that the other tools take; close it
with `spider_browser_close`. Open sessions bill until closed.
"""

from __future__ import annotations

_MAX_SESSIONS = 5

_MISSING_KEY = (
    "If SPIDER_API_KEY is missing, report the configuration error instead of retrying."
)

_SESSION_ID = {"type": "string", "description": "Session id from spider_browser_open."}
_TIMEOUT = {"type": "number", "description": "Max ms to wait for the selector. Default 10000."}


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


OPEN = _schema(
    "spider_browser_open",
    "Open a remote browser session on Spider's fleet and return a session_id. Pass that "
    "session_id to the other spider_browser_* tools, and close it with spider_browser_close "
    f"when done (open sessions bill until closed). At most {_MAX_SESSIONS} sessions can be open "
    f"at once. {_MISSING_KEY}",
    {
        "browser": {
            "type": "string",
            "enum": ["auto", "chrome", "firefox"],
            "description": "Browser to use. Defaults to 'auto' (server picks).",
        },
        "stealth": {
            "type": "number",
            "description": "Stealth/proxy tier 1-3. 0 or omitted means auto-escalate.",
        },
    },
    [],
)

NAVIGATE = _schema(
    "spider_browser_navigate",
    f"Navigate an open browser session to a URL and wait for it to load. {_MISSING_KEY}",
    {"session_id": _SESSION_ID, "url": {"type": "string", "description": "The URL to navigate to."}},
    ["session_id", "url"],
)

CLICK = _schema(
    "spider_browser_click",
    f"Click an element matching a CSS selector in an open browser session. {_MISSING_KEY}",
    {
        "session_id": _SESSION_ID,
        "selector": {"type": "string", "description": "CSS selector of the element to click."},
        "timeout": _TIMEOUT,
    },
    ["session_id", "selector"],
)

FILL = _schema(
    "spider_browser_fill",
    "Fill a form field matching a CSS selector with text in an open browser session. "
    f"{_MISSING_KEY}",
    {
        "session_id": _SESSION_ID,
        "selector": {"type": "string", "description": "CSS selector of the input to fill."},
        "value": {"type": "string", "description": "Text to type into the field."},
        "timeout": _TIMEOUT,
    },
    ["session_id", "selector", "value"],
)

SCREENSHOT = _schema(
    "spider_browser_screenshot",
    "Capture a screenshot of the current page in an open browser session. Returns a "
    f"base64-encoded PNG in the payload. {_MISSING_KEY}",
    {"session_id": _SESSION_ID},
    ["session_id"],
)

CONTENT = _schema(
    "spider_browser_content",
    f"Get the current page's HTML or visible text from an open browser session. {_MISSING_KEY}",
    {
        "session_id": _SESSION_ID,
        "format": {
            "type": "string",
            "enum": ["html", "text"],
            "description": "Return raw HTML or visible text. Default 'html'.",
        },
    },
    ["session_id"],
)

EVALUATE = _schema(
    "spider_browser_evaluate",
    "Execute JavaScript in the page context of an open browser session and return its result. "
    f"{_MISSING_KEY}",
    {
        "session_id": _SESSION_ID,
        "expression": {
            "type": "string",
            "description": "JavaScript expression to evaluate in the page.",
        },
    },
    ["session_id", "expression"],
)

WAIT_FOR = _schema(
    "spider_browser_wait_for",
    "Wait for a selector to appear, for navigation to settle, or for network idle in an open "
    "browser session. Provide 'selector' to wait for an element, set 'navigation' to wait for a "
    f"load, or neither to wait for network idle. {_MISSING_KEY}",
    {
        "session_id": _SESSION_ID,
        "selector": {"type": "string", "description": "CSS selector to wait for."},
        "navigation": {
            "type": "boolean",
            "description": "Wait for navigation/page load instead of a selector.",
        },
        "timeout": {"type": "number", "description": "Max ms to wait. Default 30000."},
    },
    ["session_id"],
)

CLOSE = _schema(
    "spider_browser_close",
    "Close a browser session and stop its billing. Returns the number of sessions still open. "
    "Always close sessions when done.",
    {"session_id": _SESSION_ID},
    ["session_id"],
)
