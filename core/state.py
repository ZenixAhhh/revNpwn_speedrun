"""
State Management - Blackboard Pattern
Maintains structured metadata across triage, analysis, and reversing stages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class StateManager:
    """Manages reading, caching, and writing state.json for binary analysis."""

    def __init__(self, workspace_dir: Path | str):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.state_file = self.workspace_dir / "state.json"
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads state from file or initializes an empty state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = self._init_schema()
        else:
            self._data = self._init_schema()
        return self._data

    def _init_schema(self) -> Dict[str, Any]:
        return {
            "binary_path": "",
            "arch": "",
            "bitness": 0,
            "endian": "",
            "mitigations": {},
            "user_functions": [],
            "callgraph": {},
            "decompiled_cache": {},
            "notes": []
        }

    def save(self) -> None:
        """Persists current in-memory state to disk atomically."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        temp_file = self.state_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        temp_file.replace(self.state_file)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        self._data[key] = value
        if auto_save:
            self.save()

    def update_dict(self, key: str, new_entries: Dict[str, Any], auto_save: bool = True) -> None:
        current = self._data.setdefault(key, {})
        if isinstance(current, dict):
            current.update(new_entries)
            if auto_save:
                self.save()

    def to_json(self) -> str:
        return json.dumps(self._data, indent=2)
