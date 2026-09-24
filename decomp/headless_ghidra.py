"""
Ghidra Headless Decompiler Wrapper
Automates running Ghidra's analyzeHeadless with ExportDecompiledC to extract full C source non-interactively.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class GhidraHeadlessDecompiler:
    """Invokes Ghidra analyzeHeadless to decompile binaries without opening the GUI."""

    def __init__(
        self,
        ghidra_home: Optional[Path | str] = None,
        java_home: Optional[Path | str] = None
    ):
        self.ghidra_home = Path(ghidra_home or "/home/wsl/tools/ghidra_12.1.3_PUBLIC").resolve()
        self.java_home = Path(java_home or "/home/wsl/tools/jdk-21.0.12+8").resolve()
        self.analyze_headless = self.ghidra_home / "support" / "analyzeHeadless"
        self.scripts_dir = Path(__file__).parent / "ghidra_scripts"

    def is_available(self) -> bool:
        """Verifies that Ghidra and the Java runtime exist."""
        return self.analyze_headless.exists() and (self.java_home / "bin" / "java").exists()

    def decompile(self, binary_path: Path | str, output_file: Optional[Path | str] = None) -> Path:
        """
        Decompiles the specified binary to a C file using Ghidra in headless mode.
        """
        binary = Path(binary_path).resolve()
        if not binary.exists():
            raise FileNotFoundError(f"Binary not found: {binary}")

        out_path = Path(output_file).resolve() if output_file else binary.parent / f"{binary.name}.decompiled.c"

        if not self.is_available():
            raise RuntimeError(f"Ghidra or JDK not found at {self.ghidra_home} / {self.java_home}")

        env = os.environ.copy()
        env["JAVA_HOME"] = str(self.java_home)
        env["PATH"] = f"{self.java_home}/bin:{env.get('PATH', '')}"

        with tempfile.TemporaryDirectory(prefix="ghidra_proj_") as temp_dir:
            cmd = [
                str(self.analyze_headless),
                temp_dir,
                "TempProject",
                "-import", str(binary),
                "-scriptPath", str(self.scripts_dir),
                "-postScript", "ExportDecompiledC.java", str(out_path),
                "-deleteProject",
                "-noanalysis"  # fast run or allow default analysis
            ]
            # Replace -noanalysis with standard analysis so decompiler gets proper types
            cmd.remove("-noanalysis")

            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if not out_path.exists() or out_path.stat().st_size == 0:
                error_msg = proc.stderr or proc.stdout
                raise RuntimeError(f"Ghidra headless decompilation failed: {error_msg[-400:]}")

        return out_path
