# revNpwn_speedrun

High-efficiency binary inspection, symbol pruning, and headless decompilation toolkit designed for rapid triage in competitive CTF reverse engineering.

---

## Architecture Overview

```text
revNpwn_speedrun/
├── core/
│   ├── state.py              # Blackboard pattern state manager (state.json)
│   └── symbols.py            # Symbol table extractor and CRT boilerplate pruner
├── analysis/
│   └── callgraph.py          # Static call-graph extractor & compact ASCII tree visualizer
├── decomp/
│   ├── headless_ghidra.py    # Non-interactive Ghidra analyzeHeadless export runner
│   └── ghidra_scripts/
│       └── ExportDecompiledC.java # Ghidra headless script exporting full C source
└── cli.py                    # Main CLI entrypoint
```

---

## Features

### 1. Compact Call-Graph Generation (`callgraph`)
Generates caller-to-callee hierarchy trees starting from a root function to map program flow without loading raw assembly into the context window:
```bash
./cli.py callgraph ./chall --root main --depth 4
```
**Example output:**
```text
=== Call Graph for chall (Root: main) ===
main
└── authenticate
    ├── read_input
    └── verify_hash
        └── crypto_box
```

### 2. Boilerplate & Symbol Pruning (`symbols`)
Filters out compiler runtime initialization thunks (`_start`, `__libc_csu_init`, `frame_dummy`, etc.) to surface user-defined functions immediately:
```bash
./cli.py symbols ./chall --user-only
```

### 3. Headless Ghidra Decompiler Export (`decompile`)
Invokes Ghidra's `analyzeHeadless` in the background with OpenJDK 21, decompiles all functions into C pseudocode, and outputs to disk without launching the graphical user interface:
```bash
./cli.py decompile ./chall -o ./chall.decompiled.c
```

### 4. Shared State Manager (`state`)
Inspects or initializes a persistent `state.json` file to pass findings between inspection scripts:
```bash
./cli.py state [dir]
```
