"""Slash commands: /spider and /spider-browser.

Hermes command handlers receive the raw argument string and return a string to
display (there is no interactive UI object), so the pi extension's interactive
toggle menu becomes explicit text subcommands.
"""

from __future__ import annotations

from . import browser
from .config import api_url, has_api_key
from .constants import BROWSER_TOOL_NAMES, CORE_TOOL_NAMES
from .settings import load_disabled, set_enabled

_SPIDER_HELP = "\n".join(
    [
        "hermes-spider-tools — Spider Cloud scraping & crawling.",
        "",
        "Set SPIDER_API_KEY in your environment (get a key at https://spider.cloud/api-keys).",
        "Optional: SPIDER_API_URL (REST base), SPIDER_BROWSER_URL (browser fleet WS).",
        "",
        "Commands:",
        "  /spider status            show API key status and which tools are enabled",
        "  /spider enable [tool]     enable a tool (or all core tools if omitted)",
        "  /spider disable [tool]    disable a tool (or all core tools if omitted)",
        "  /spider tools             list every tool and whether it is enabled",
        "  /spider help              show this help",
        "",
        "Toggling takes effect immediately — no restart needed.",
    ]
)

_BROWSER_HELP = "\n".join(
    [
        "hermes-spider-tools (browser tier) — remote browser automation via Spider's fleet.",
        "",
        "Set SPIDER_API_KEY and `pip install spider-browser` in Hermes' environment.",
        f"Sessions auto-close after 5 minutes idle; at most {browser.MAX_SESSIONS} open at once.",
        "",
        "Commands:",
        "  /spider-browser status    show API key status and open browser sessions",
        "  /spider-browser close     close all open browser sessions",
        "  /spider-browser help      show this help",
    ]
)


def _tool_lines(names: tuple[str, ...], disabled: set[str]) -> list[str]:
    return [f"  [{'x' if n not in disabled else ' '}] {n}" for n in names]


def handle_spider_command(raw_args: str) -> str:
    argv = raw_args.strip().split()
    action = argv[0].lower() if argv else "help"
    target = argv[1] if len(argv) > 1 else None

    if action in ("help", "-h", "--help", ""):
        return _SPIDER_HELP

    if action == "status":
        disabled = load_disabled()
        enabled = [n for n in CORE_TOOL_NAMES if n not in disabled]
        return "\n".join(
            [
                f"SPIDER_API_KEY: {'set' if has_api_key() else 'MISSING'}",
                f"API URL: {api_url()}",
                f"Enabled core tools ({len(enabled)}/{len(CORE_TOOL_NAMES)}): "
                f"{', '.join(enabled) if enabled else 'none'}",
            ]
        )

    if action == "tools":
        disabled = load_disabled()
        lines = ["Core tools:", *_tool_lines(CORE_TOOL_NAMES, disabled)]
        lines += ["Browser tools:", *_tool_lines(BROWSER_TOOL_NAMES, disabled)]
        return "\n".join(lines)

    if action in ("enable", "on", "disable", "off"):
        enable = action in ("enable", "on")
        if target:
            from .constants import ALL_TOOL_NAMES

            if target not in ALL_TOOL_NAMES:
                return f"Unknown tool '{target}'. Run /spider tools to list them."
            targets = [target]
        else:
            targets = list(CORE_TOOL_NAMES)
        set_enabled(targets, enable)
        verb = "enabled" if enable else "disabled"
        return f"{verb.capitalize()}: {', '.join(targets)}"

    return f"Unknown /spider command '{action}'.\n\n{_SPIDER_HELP}"


def handle_browser_command(raw_args: str) -> str:
    action = raw_args.strip().split()[0].lower() if raw_args.strip() else "help"

    if action in ("help", "-h", "--help", ""):
        return _BROWSER_HELP

    if action == "status":
        return "\n".join(
            [
                f"SPIDER_API_KEY: {'set' if has_api_key() else 'MISSING'}",
                f"Open sessions: {browser.session_count()}/{browser.MAX_SESSIONS}",
            ]
        )

    if action == "close":
        closed = browser.close_all_sessions()
        return f"Closed {closed} browser session(s)."

    return f"Unknown /spider-browser command '{action}'.\n\n{_BROWSER_HELP}"
