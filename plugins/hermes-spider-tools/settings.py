"""Per-tool enable/disable state.

Two layers: config.yaml's `disabled_tools` provides the baseline, and a runtime
settings file (toggled live by the /spider command) overrides it once the user
touches it. Because Hermes evaluates each tool's `check_fn` for availability,
toggling takes effect without restarting Hermes.

State is the set of DISABLED tool names. Writes are atomic (temp file + rename).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .config import config_disabled_tools
from .constants import ALL_TOOL_NAMES


def _settings_path() -> Path:
    base = os.environ.get("HERMES_DIR") or os.path.join(os.path.expanduser("~"), ".hermes")
    return Path(base) / "hermes-spider-tools-settings.json"


def _runtime_disabled() -> set[str] | None:
    """Disabled set from the runtime file, or None if the user hasn't toggled yet."""
    try:
        raw = json.loads(_settings_path().read_text("utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        return None
    disabled = raw.get("disabled") if isinstance(raw, dict) else None
    if not isinstance(disabled, list):
        return None
    return {name for name in disabled if name in ALL_TOOL_NAMES}


def load_disabled() -> set[str]:
    """Effective disabled set: runtime overrides if present, else config baseline."""
    runtime = _runtime_disabled()
    if runtime is not None:
        return runtime
    return {name for name in config_disabled_tools() if name in ALL_TOOL_NAMES}


def is_enabled(tool_name: str) -> bool:
    return tool_name not in load_disabled()


def save_disabled(disabled: set[str]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"disabled": sorted(name for name in disabled if name in ALL_TOOL_NAMES)}
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2) + "\n", "utf-8")
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def set_enabled(tool_names: list[str], enabled: bool) -> None:
    """Enable or disable the given tools and persist the change."""
    disabled = load_disabled()
    for name in tool_names:
        if name not in ALL_TOOL_NAMES:
            continue
        if enabled:
            disabled.discard(name)
        else:
            disabled.add(name)
    save_disabled(disabled)
