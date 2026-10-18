"""Hiding Omarchy's own night light toggle while this plugin drives hyprsunset.

Omarchy's indicators widget ships a `NightLight` entry that switches between a
fixed 4000K and 6500K and knows nothing about a schedule. While this plugin owns
hyprsunset.conf that toggle is a footgun: one click silently overrides the
schedule until the next profile switch.

So enabling the plugin removes `NightLight` from the `items` list of every
indicators widget in ~/.config/omarchy/shell.json, and disabling puts the list
back. Only `bar.layout.*` entries whose id ends in `.indicators` are touched,
and only their `items` key: everything else in the file is preserved. The
previous value is remembered in the plugin's state so `disable` can restore it,
and a one-time copy of the file is kept as shell.json.pre-nightlight.
"""

import json
import shutil

from . import config

TOGGLE = "NightLight"

# What Omarchy's indicators widget shows when `items` is unset. Kept here so a
# widget that relies on the defaults still gets an explicit list without the
# toggle, rather than losing every other indicator.
DEFAULT_ITEMS = ["Dictation", "ScreenRecording", "Reminder", TOGGLE, "Dnd", "StayAwake"]


def _entries(shell):
    """(section, entry) for every indicators widget in the bar layout."""
    layout = (shell.get("bar") or {}).get("layout") or {}
    for section, items in layout.items():
        for entry in items or []:
            if isinstance(entry, dict) and str(entry.get("id", "")).endswith(".indicators"):
                yield section, entry


def _read():
    try:
        return json.loads(config.SHELL_CONFIG.read_text())
    except (OSError, ValueError):
        return None


def _write(shell):
    config.write_text(config.SHELL_CONFIG,
                      json.dumps(shell, indent=2, ensure_ascii=False) + "\n")


def _schema(data):
    """The state file: which widgets were changed and what they looked like."""
    config.check_version(data)
    widgets = data.get("widgets")
    config.check(isinstance(widgets, list), "widgets must be a list")
    for w in widgets:
        config.check(isinstance(w, dict), "widget entry must be an object")
        config.check(isinstance(w.get("section"), str), "section must be a string")
        config.check(isinstance(w.get("id"), str), "id must be a string")
        items = w.get("items")
        config.check(items is None or (isinstance(items, list)
                                       and all(isinstance(i, str) for i in items)),
                     "items must be a list of strings or null")
    return data


def hidden():
    """True while the built-in toggle is removed from the bar."""
    return config.INDICATORS_STATE.exists()


def hide():
    """Remove `NightLight` from every indicators widget.

    Returns how many widgets were changed: 0 when there is no shell.json, no
    indicators widget, or the toggle was already gone.
    """
    shell = _read()
    if not isinstance(shell, dict):
        return 0
    previous = []
    for section, entry in _entries(shell):
        if "items" in entry:
            items = entry["items"]
            if not isinstance(items, list) or TOGGLE not in items:
                continue
            previous.append({"section": section, "id": entry["id"], "items": list(items)})
            entry["items"] = [i for i in items if i != TOGGLE]
        else:
            previous.append({"section": section, "id": entry["id"], "items": None})
            entry["items"] = [i for i in DEFAULT_ITEMS if i != TOGGLE]
    if not previous:
        return 0
    backup = config.SHELL_CONFIG.with_name(config.SHELL_CONFIG.name + ".pre-nightlight")
    if not backup.exists():
        shutil.copy2(config.SHELL_CONFIG, backup)
    _write(shell)
    config.write_json(config.INDICATORS_STATE, config.versioned({"widgets": previous}))
    return len(previous)


def restore():
    """Put the `items` lists back the way `hide` found them.

    Returns how many widgets were restored; 0 when nothing was hidden.
    """
    state = config.read_json(config.INDICATORS_STATE, _schema)
    config.INDICATORS_STATE.unlink(missing_ok=True)
    if not state:
        return 0
    shell = _read()
    if not isinstance(shell, dict):
        return 0
    wanted = {(w["section"], w["id"]): w["items"] for w in state["widgets"]}
    restored = 0
    for section, entry in _entries(shell):
        key = (section, entry["id"])
        if key not in wanted:
            continue
        items = wanted[key]
        if items is None:
            entry.pop("items", None)
        else:
            entry["items"] = list(items)
        restored += 1
    if restored:
        _write(shell)
    return restored
