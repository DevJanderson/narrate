"""Keep each coding agent's last reply so the hotkey can read it on demand.

A Stop hook in Claude Code or Codex runs `narrate --save-reply`, which stores
the reply under the agent's process id. The hotkey then reads the newest
reply from an agent running inside the focused window.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

AGENT_NAMES = {"claude", "codex"}


def _parent(pid: int) -> int | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        # The command name may contain spaces or parentheses; fields resume
        # after the last ")": state, then the parent pid.
        return int(stat.rsplit(")", 1)[1].split()[1])
    except (OSError, IndexError, ValueError):
        return None


def _name(pid: int) -> str | None:
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return None


def _ancestors(pid: int) -> Iterator[int]:
    """pid itself, then its parent, grandparent... up to (excluding) init."""
    current: int | None = pid
    while current and current > 1:
        yield current
        current = _parent(current)


def _agent_pid() -> int:
    """The Claude Code or Codex process that ran this hook."""
    for pid in _ancestors(os.getppid()):
        if _name(pid) in AGENT_NAMES:
            return pid
    return os.getppid()


def _prune(directory: Path) -> None:
    for reply in directory.glob("*.txt"):
        if not Path(f"/proc/{reply.stem}").exists():
            reply.unlink(missing_ok=True)


def save(hook_input: str, directory: Path) -> bool:
    """Store last_assistant_message from a Stop hook's JSON input."""
    try:
        data = json.loads(hook_input)
    except json.JSONDecodeError:
        return False
    message = data.get("last_assistant_message") if isinstance(data, dict) else None
    if not isinstance(message, str) or not message.strip():
        return False

    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    pid = _agent_pid()
    partial = directory / f".{pid}.tmp"
    partial.write_text(message)
    partial.replace(directory / f"{pid}.txt")
    _prune(directory)
    return True


def _focused_window_pid() -> int | None:
    """Process id of the focused window (Hyprland only for now)."""
    try:
        result = subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            check=False, capture_output=True, text=True, timeout=2,
        )
        return int(json.loads(result.stdout)["pid"])
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
        return None


def latest_in_focused_window(directory: Path) -> str | None:
    """The newest saved reply from an agent running inside the focused window."""
    window = _focused_window_pid()
    if not window or window <= 1 or not directory.is_dir():
        return None
    candidates = []
    for reply in directory.glob("*.txt"):
        try:
            pid = int(reply.stem)
        except ValueError:
            continue
        if window in _ancestors(pid):
            candidates.append(reply)
    if not candidates:
        return None
    newest = max(candidates, key=lambda reply: reply.stat().st_mtime)
    return newest.read_text()
