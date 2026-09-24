"""
Symbol Table Parser & Boilerplate Pruner
Extracts and categorizes symbols from ELF binaries, isolating user code from runtime thunks.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Set

BOILERPLATE_SYMBOLS: Set[str] = {
    "_init",
    "_fini",
    "_start",
    "__libc_csu_init",
    "__libc_csu_fini",
    "deregister_tm_clones",
    "register_tm_clones",
    "__do_global_dtors_aux",
    "frame_dummy",
    "__x86.get_pc_thunk.bx",
    "__x86.get_pc_thunk.dx",
    "__libc_start_main",
    "__gmon_start__",
    "_ITM_deregisterTMCloneTable",
    "_ITM_registerTMCloneTable",
    "__cxa_finalize",
    "_dl_relocate_static_pie"
}


class SymbolExtractor:
    """Extracts, filters, and classifies symbols from binaries."""

    def __init__(self, binary_path: Path | str):
        self.binary_path = Path(binary_path).resolve()
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")

    def extract_symbols(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Parses symbol tables using nm and objdump.
        Returns categorized lists of symbols: user_functions, imports, and boilerplate.
        """
        user_funcs = []
        imports = []
        boilerplate = []

        # Run nm to get defined and undefined symbols
        cmd = ["nm", "-C", "--defined-only", str(self.binary_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 3:
                    addr, sym_type, name = parts[0], parts[1], parts[2]
                    # Filter for text/function symbols (T, t)
                    if sym_type.lower() == "t":
                        entry = {"name": name, "address": f"0x{addr.lstrip('0') or '0'}"}
                        if name in BOILERPLATE_SYMBOLS or name.startswith("__") or name.startswith("."):
                            boilerplate.append(entry)
                        else:
                            user_funcs.append(entry)

        # Run nm for undefined / imported symbols
        cmd_dyn = ["nm", "-D", "-u", str(self.binary_path)]
        res_dyn = subprocess.run(cmd_dyn, capture_output=True, text=True)
        if res_dyn.returncode == 0:
            for line in res_dyn.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    name = parts[-1]
                    imports.append({"name": name, "type": "dynamic_import"})

        return {
            "user_functions": sorted(user_funcs, key=lambda x: x["name"]),
            "imports": sorted(imports, key=lambda x: x["name"]),
            "boilerplate": sorted(boilerplate, key=lambda x: x["name"])
        }
