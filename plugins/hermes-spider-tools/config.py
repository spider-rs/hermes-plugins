"""Configuration for hermes-spider-tools.

Settings come from a plugin-local ``config.yaml`` first, then the environment,
then built-in defaults — in that order. Hermes auto-copies ``config.yaml.example``
to ``config.yaml`` on ``hermes plugins install``; the real file is gitignored.

Secrets may be given two ways in config.yaml:
  * ``api_key: "sk-..."``        store it directly (the file is gitignored), or
  * ``api_key_env: SPIDER_API_KEY``  name an env var to read it from.
Either way the value can also just live in the environment (the fallback).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.spider.cloud"
DEFAULT_MAX_RESULTS = 10

_MISSING_KEY_MESSAGE = (
    "No Spider Cloud API key configured. Set 'api_key' (or 'api_key_env') in this "
    "plugin's config.yaml, or export SPIDER_API_KEY (also declared in plugin.yaml "
    "requires_env, so `hermes plugins install` can prompt for it). Get a key at "
    "https://spider.cloud/api-keys."
)

# config.yaml is parsed once per path and cached for the process.
_config_cache: dict[str, dict[str, Any]] = {}


def _config_path() -> Path:
    override = (os.environ.get("HERMES_SPIDER_TOOLS_CONFIG") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "config.yaml"


def load_config() -> dict[str, Any]:
    """Parse config.yaml (cached). Missing/invalid file -> {} and fall back to env."""
    path = _config_path()
    key = str(path)
    if key in _config_cache:
        return _config_cache[key]

    data: dict[str, Any] = {}
    if path.exists():
        try:
            import yaml

            loaded = yaml.safe_load(path.read_text("utf-8"))
            if isinstance(loaded, dict):
                data = loaded
            elif loaded is not None:
                logger.warning("%s is not a mapping; ignoring it", path)
        except Exception as exc:  # noqa: BLE001 - bad config must not break plugin load
            logger.warning("Failed to parse %s: %s; falling back to environment", path, exc)

    _config_cache[key] = data
    return data


def _cfg_str(key: str) -> str | None:
    value = load_config().get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def api_url() -> str:
    """Core REST base URL: config.yaml `api_url` -> SPIDER_API_URL -> default."""
    cfg = _cfg_str("api_url")
    if cfg:
        return cfg.rstrip("/")
    env = (os.environ.get("SPIDER_API_URL") or os.environ.get("SPIDER_BASE_URL") or "").strip()
    return (env or DEFAULT_API_URL).rstrip("/")


def browser_server_url() -> str | None:
    """Browser fleet WebSocket: config.yaml -> SPIDER_BROWSER_URL -> None (SDK default)."""
    cfg = _cfg_str("browser_server_url")
    if cfg:
        return cfg
    return (os.environ.get("SPIDER_BROWSER_URL") or "").strip() or None


def max_results() -> int:
    """Cap on results returned to the model: config.yaml `max_results` -> default."""
    value = load_config().get("max_results")
    if isinstance(value, int) and value > 0:
        return value
    return DEFAULT_MAX_RESULTS


def config_disabled_tools() -> set[str]:
    """Tools disabled by default in config.yaml (runtime /spider toggles override)."""
    value = load_config().get("disabled_tools")
    if isinstance(value, list):
        return {name for name in value if isinstance(name, str)}
    return set()


def _resolve_api_key() -> str | None:
    cfg = load_config()
    direct = cfg.get("api_key")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    env_name = cfg.get("api_key_env")
    if isinstance(env_name, str) and env_name.strip():
        value = (os.environ.get(env_name.strip()) or "").strip()
        if value:
            return value
    return (os.environ.get("SPIDER_API_KEY") or "").strip() or None


def has_api_key() -> bool:
    return _resolve_api_key() is not None


def get_api_key() -> str:
    """Return the resolved API key or raise a descriptive error (fail fast)."""
    key = _resolve_api_key()
    if not key:
        raise RuntimeError(_MISSING_KEY_MESSAGE)
    return key
