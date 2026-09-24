"""
Static Call-Graph Extractor & Tree Visualizer
Builds caller-to-callee relationships from disassembly and renders token-efficient ASCII call trees.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set


class CallGraphExtractor:
    """Extracts function call references from disassembly and generates reachable call trees."""

    def __init__(self, binary_path: Path | str):
        self.binary_path = Path(binary_path).resolve()
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")
        self.graph: Dict[str, List[str]] = {}
        self.func_addresses: Dict[str, str] = {}

    def build_graph(self) -> Dict[str, List[str]]:
        """
        Parses disassembly to map all function call sites.
        Returns adjacency list: { 'caller_func': ['callee_1', 'callee_2', ...] }
        """
        cmd = ["objdump", "-d", "-M", "intel", "--no-show-raw-insn", str(self.binary_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return {}

        current_func: Optional[str] = None
        call_regex = re.compile(r"\bcall\s+([0-9a-fA-F]+)\s+<([^>]+)>")
        func_header_regex = re.compile(r"^[0-9a-fA-F]+\s+<([^>]+)>:")

        self.graph = {}
        for line in proc.stdout.splitlines():
            line = line.strip()

            # Check for function entry header
            header_match = func_header_regex.match(line)
            if header_match:
                raw_name = header_match.group(1)
                # Clean up symbol names (e.g. sym.main, main@plt)
                current_func = raw_name.split("@")[0]
                if current_func not in self.graph:
                    self.graph[current_func] = []
                continue

            # Check for call instruction inside current function
            if current_func:
                call_match = call_regex.search(line)
                if call_match:
                    callee_name = call_match.group(2).split("@")[0]
                    if callee_name not in self.graph[current_func]:
                        self.graph[current_func].append(callee_name)

        return self.graph

    def render_tree(self, root: str = "main", max_depth: int = 4) -> str:
        """
        Renders a compact, hierarchical ASCII tree starting from the specified root function.
        Prevents infinite recursion on recursive function calls.
        """
        if not self.graph:
            self.build_graph()

        # Find matching root key (in case of prefixes or mangled names)
        matched_root = None
        for k in self.graph.keys():
            if k == root or k.endswith(f"::{root}"):
                matched_root = k
                break

        if not matched_root:
            available = [k for k in self.graph.keys() if not k.startswith("_")]
            return f"Root function '{root}' not found. Available functions: {', '.join(available[:15])}"

        lines = [f"{matched_root}"]
        visited: Set[str] = set()

        def _traverse(node: str, prefix: str, depth: int):
            if depth >= max_depth:
                lines.append(f"{prefix}└── ... (max depth reached)")
                return

            callees = self.graph.get(node, [])
            total = len(callees)
            for i, child in enumerate(callees):
                is_last = (i == total - 1)
                branch = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                # Filter out pure CRT/loader functions if deeply nested
                if child.startswith("__") and depth > 1:
                    continue

                if child in visited:
                    lines.append(f"{prefix}{branch}{child} (recursive/visited)")
                else:
                    visited.add(child)
                    lines.append(f"{prefix}{branch}{child}")
                    _traverse(child, next_prefix, depth + 1)

        visited.add(matched_root)
        _traverse(matched_root, "", 1)
        return "\n".join(lines)
