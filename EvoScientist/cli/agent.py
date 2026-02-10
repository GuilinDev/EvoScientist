"""Agent loading and workspace helpers."""

import os
from datetime import datetime
from pathlib import Path

from ..paths import new_run_dir, RUNS_DIR


def _shorten_path(path: str) -> str:
    """Shorten absolute path to relative path from current directory."""
    if not path:
        return path
    try:
        cwd = os.getcwd()
        if path.startswith(cwd):
            rel = path[len(cwd):].lstrip(os.sep)
            return os.path.join(os.path.basename(cwd), rel) if rel else os.path.basename(cwd)
        return path
    except Exception:
        return path


def _deduplicate_run_name(name: str, runs_dir: Path = RUNS_DIR) -> str:
    """Return *name* if available, otherwise *name_1*, *name_2*, etc."""
    if not (runs_dir / name).exists():
        return name
    i = 1
    while (runs_dir / f"{name}_{i}").exists():
        i += 1
    return f"{name}_{i}"


def _create_session_workspace(name: str | None = None) -> str:
    """Create a per-session workspace directory and return its path.

    Args:
        name: Optional human-friendly run name.  Duplicates are resolved
              by appending ``_1``, ``_2``, etc.  Falls back to a timestamp
              if *name* is None.
    """
    if name:
        session_id = _deduplicate_run_name(name)
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_dir = str(new_run_dir(session_id))
    os.makedirs(workspace_dir, exist_ok=True)
    return workspace_dir


def _load_agent(workspace_dir: str | None = None):
    """Load the CLI agent (with InMemorySaver checkpointer for multi-turn).

    Args:
        workspace_dir: Optional per-session workspace directory.
    """
    from ..EvoScientist import create_cli_agent
    return create_cli_agent(workspace_dir=workspace_dir)
