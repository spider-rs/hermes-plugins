"""Offline smoke test for the Hermes plugins.

Loads each plugin the way Hermes does (as a package, so relative imports work),
exercises register(ctx) with a fake context, validates every tool schema, and
confirms handlers/commands return well-formed JSON / strings without any network
access or a configured API key.

Run with: uv run python tests/smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO / "plugins" / "hermes-spider-tools"

# Deterministic environment: no key, isolated settings dir.
os.environ.pop("SPIDER_API_KEY", None)
os.environ["HERMES_DIR"] = tempfile.mkdtemp(prefix="hermes-smoke-")


class FakeCtx:
    """Records everything a plugin registers."""

    def __init__(self) -> None:
        self.tools: dict[str, dict] = {}
        self.commands: dict[str, dict] = {}
        self.hooks: list[str] = []

    def register_tool(self, *, name, toolset, schema, handler, **kwargs):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **kwargs}

    def register_command(self, name, handler, description=""):
        self.commands[name] = {"handler": handler, "description": description}

    def register_hook(self, hook_name, callback):
        self.hooks.append(hook_name)


def load_plugin(directory: Path):
    name = f"hermes_plugins_{directory.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(
        name, directory / "__init__.py", submodule_search_locations=[str(directory)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_schema(name: str, schema: dict) -> None:
    check(schema.get("name") == name, f"{name}: schema.name mismatch ({schema.get('name')})")
    check(isinstance(schema.get("description"), str) and schema["description"], f"{name}: no description")
    params = schema.get("parameters")
    check(isinstance(params, dict) and params.get("type") == "object", f"{name}: bad parameters")
    check(isinstance(params.get("properties"), dict), f"{name}: properties missing")
    check(isinstance(params.get("required"), list), f"{name}: required missing")
    for field in params["required"]:
        check(field in params["properties"], f"{name}: required '{field}' not in properties")


def assert_json_error(raw: str, label: str) -> None:
    data = json.loads(raw)  # raises if not valid JSON
    check(data.get("success") is False, f"{label}: expected success=false, got {data}")
    check(isinstance(data.get("error"), str) and data["error"], f"{label}: no error message")


def main() -> int:
    plugin = load_plugin(PLUGIN_DIR)
    ctx = FakeCtx()
    plugin.register(ctx)

    from importlib import import_module

    constants = import_module(f"{plugin.__name__}.constants")
    expected = set(constants.ALL_TOOL_NAMES)

    # 1) Registration surface
    check(set(ctx.tools) == expected, f"tool set mismatch: {set(ctx.tools) ^ expected}")
    check(set(ctx.commands) == {"spider", "spider-browser"}, f"commands: {set(ctx.commands)}")
    check("on_session_end" in ctx.hooks, f"hooks: {ctx.hooks}")
    print(f"✓ registered {len(ctx.tools)} tools, {len(ctx.commands)} commands, {len(ctx.hooks)} hook(s)")

    # 2) Schemas
    for name, entry in ctx.tools.items():
        validate_schema(name, entry["schema"])
    print("✓ all tool schemas valid")

    # 3) check_fn hides tools when the key is missing
    for name, entry in ctx.tools.items():
        check(entry["check_fn"]() is False, f"{name}: check_fn should be False without a key")
    print("✓ check_fn gates every tool on a missing key")

    # 4) Handlers return JSON error envelopes (no key / bad args, no network)
    assert_json_error(ctx.tools["spider_get_credits"]["handler"]({}), "spider_get_credits")
    assert_json_error(ctx.tools["spider_scrape"]["handler"]({}), "spider_scrape (missing url)")
    assert_json_error(ctx.tools["spider_transform"]["handler"]({"data": []}), "spider_transform (empty)")
    assert_json_error(
        ctx.tools["spider_browser_navigate"]["handler"]({"session_id": "nope", "url": "https://x"}),
        "spider_browser_navigate (no session)",
    )
    assert_json_error(ctx.tools["spider_browser_open"]["handler"]({}), "spider_browser_open (no key)")
    print("✓ handlers return structured JSON errors")

    # 5) Commands return strings; settings round-trip live
    spider_cmd = ctx.commands["spider"]["handler"]
    check("Spider Cloud" in spider_cmd("help"), "spider help text")
    check("MISSING" in spider_cmd("status"), "spider status reports missing key")
    spider_cmd("disable spider_crawl")
    settings = import_module(f"{plugin.__name__}.settings")
    check("spider_crawl" in settings.load_disabled(), "disable did not persist")
    spider_cmd("enable spider_crawl")
    check("spider_crawl" not in settings.load_disabled(), "enable did not persist")
    check("Open sessions: 0" in ctx.commands["spider-browser"]["handler"]("status"), "browser status")
    print("✓ commands respond and settings persist")

    # 6) config.yaml is primary; env is the fallback
    config = import_module(f"{plugin.__name__}.config")
    config_path = Path(os.environ["HERMES_DIR"]) / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "api_key: sk-from-config",
                "api_url: https://config.example.com/",
                "max_results: 3",
                "disabled_tools:",
                "  - spider_links",
            ]
        ),
        "utf-8",
    )
    os.environ["HERMES_SPIDER_TOOLS_CONFIG"] = str(config_path)
    config._config_cache.clear()

    check(config.has_api_key() is True, "config api_key not picked up")
    check(config.get_api_key() == "sk-from-config", "config api_key value wrong")
    check(config.api_url() == "https://config.example.com", "config api_url not primary")
    check(config.max_results() == 3, "config max_results not applied")
    check(config.config_disabled_tools() == {"spider_links"}, "config disabled_tools wrong")
    # config baseline applies only when the user hasn't toggled at runtime yet
    settings._settings_path().unlink(missing_ok=True)
    check("spider_links" in settings.load_disabled(), "config baseline disable not honored")
    # ...and a runtime toggle overrides the config baseline
    spider_cmd("enable spider_links")
    check("spider_links" not in settings.load_disabled(), "runtime toggle should override config")
    # env is the fallback when config omits a key
    os.environ["SPIDER_BROWSER_URL"] = "wss://env.example.com"
    check(config.browser_server_url() == "wss://env.example.com", "env fallback not used")
    print("✓ config.yaml is primary, env is fallback")

    print("\nALL SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
