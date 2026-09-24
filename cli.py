#!/usr/bin/env python3
"""
revNpwn_speedrun CLI
Streamlined tools for binary inspection, callgraph visualization, and headless decompilation.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from core.state import StateManager
from core.symbols import SymbolExtractor
from analysis.callgraph import CallGraphExtractor
from decomp.headless_ghidra import GhidraHeadlessDecompiler


def cmd_callgraph(args):
    extractor = CallGraphExtractor(args.binary)
    tree_text = extractor.render_tree(root=args.root, max_depth=args.depth)
    print(f"=== Call Graph for {Path(args.binary).name} (Root: {args.root}) ===")
    print(tree_text)


def cmd_symbols(args):
    extractor = SymbolExtractor(args.binary)
    res = extractor.extract_symbols()

    print(f"=== User Functions ({len(res['user_functions'])}) ===")
    for f in res["user_functions"]:
        print(f"  {f['address']:<18} {f['name']}")

    if not args.user_only:
        print(f"\n=== Imported Library Symbols ({len(res['imports'])}) ===")
        for imp in res["imports"][:20]:
            print(f"  {imp['name']}")
        if len(res["imports"]) > 20:
            print(f"  ... and {len(res['imports']) - 20} more")

        print(f"\n=== Filtered Boilerplate Functions ({len(res['boilerplate'])}) ===")
        for b in res["boilerplate"][:10]:
            print(f"  {b['name']}")


def cmd_decompile(args):
    decompiler = GhidraHeadlessDecompiler()
    if not decompiler.is_available():
        print("[!] Ghidra or JDK not found. Please verify setup.")
        sys.exit(1)

    print(f"[*] Running Ghidra analyzeHeadless on {Path(args.binary).name}...")
    try:
        out_path = decompiler.decompile(args.binary, output_file=args.output)
        print(f"[+] Decompiled C exported to: {out_path}")
        print(f"[+] File size: {out_path.stat().st_size:,} bytes")
    except Exception as e:
        print(f"[!] Decompilation failed: {e}")
        sys.exit(1)


def cmd_state(args):
    sm = StateManager(args.dir)
    print(f"=== State in {sm.workspace_dir} ===")
    print(sm.to_json())


def main():
    parser = argparse.ArgumentParser(
        description="revNpwn_speedrun - High-efficiency binary inspection and analysis toolkit"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # callgraph
    p_cg = subparsers.add_parser("callgraph", help="Generate compact ASCII call tree")
    p_cg.add_argument("binary", help="Target binary path")
    p_cg.add_argument("--root", default="main", help="Root function name (default: main)")
    p_cg.add_argument("--depth", type=int, default=4, help="Maximum recursion depth (default: 4)")
    p_cg.set_defaults(func=cmd_callgraph)

    # symbols
    p_sym = subparsers.add_parser("symbols", help="List user and imported symbols")
    p_sym.add_argument("binary", help="Target binary path")
    p_sym.add_argument("--user-only", action="store_true", help="Display only user-defined functions")
    p_sym.set_defaults(func=cmd_symbols)

    # decompile
    p_dec = subparsers.add_parser("decompile", help="Run headless Ghidra decompilation")
    p_dec.add_argument("binary", help="Target binary path")
    p_dec.add_argument("-o", "--output", help="Output C file path")
    p_dec.set_defaults(func=cmd_decompile)

    # state
    p_state = subparsers.add_parser("state", help="Inspect or initialize state.json")
    p_state.add_argument("dir", nargs="?", default=".", help="Workspace directory (default: current)")
    p_state.set_defaults(func=cmd_state)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
