# Deep Dive: `binary-analyst` Skill

The `binary-analyst` skill coordinates automated binary inspection, disassembly, headless decompilation, dynamic crash/offset discovery, and exploit scaffolding. It integrates with `bintriage` to enable headless binary analysis directly within the CLI without GUI interaction.

---

## 1. Skill Purpose & Architecture

In standard CTF workflows, binary triage is slowed by interactive tools: launching Ghidra, waiting for background analysis, navigating symbol trees, and manually setting breakpoints in GDB to calculate buffer offsets.

The `binary-analyst` skill automates these mechanical steps:
* Connects the agent directly to system utilities (`readelf`, `file`, `strings`, `pwntools`, `ROPgadget`, `radare2`).
* Executes GDB in non-interactive batch mode (`gdb -nx --batch`) to extract register dumps and memory states during test runs.
* Automatically generates ready-to-run `pwntools` exploit templates (`solve.py`) customized to the binary's architecture and mitigations.

---

## 2. Command Mappings & Workflow Stages

```text
Target Binary (ELF)
   │
   ├── 1. Triage: bintriage inspect <binary> ──> Mitigations, Targets, Imports, Strings
   │
   ├── 2. Inspection:
   │      ├── Disassemble: bintriage disasm <binary> <func>
   │      └── Decompile:   bintriage decompile <binary> <func>
   │
   ├── 3. Dynamic Crash & Offset Discovery:
   │      └── bintriage crash-test <binary> --cyclic <N> ──> Recovers exact RIP offset
   │
   └── 4. Scaffolding:
          └── bintriage scaffold <binary> -o solve.py ──> Generates pwntools boilerplate
```

---

## 3. Supported Operations

| Subcommand | Underlying Tool | Functionality |
|---|---|---|
| `inspect <binary>` | `pwn.ELF` & `pyelftools` | Evaluates RELRO, Canary, NX, PIE; filters out CRT boilerplate symbols; extracts high-value targets (`win`, `vuln`) and sensitive imports (`system`, `read`). |
| `disasm <binary> [func]` | `objdump -M intel` | Extracts isolated assembly blocks for a specified function (default: `main`) with regex boundary detection. |
| `decompile <binary> [func]` | `radare2` (`pdg` / `pdc`) | Produces headless C pseudocode without opening a graphical decompiler interface. |
| `crash-test <binary> --cyclic <N>` | `gdb -nx --batch` | Injects a De Bruijn cyclic pattern, detects faults (`SIGSEGV`, `SIGBUS`), inspects registers, and calculates return address offsets via `cyclic_find`. |
| `seccomp <binary>` | `seccomp-tools` / imports | Identifies BPF filter rules or system call restrictions. |
| `rop <binary> --grep "<query>"` | `ROPgadget` / `ropper` | Searches for specific instruction sequences (e.g. `pop rdi; ret`). |
| `scaffold <binary>` | Template engine | Emits a structured `solve.py` script containing local process, GDB attach harnesses, and remote network handlers. |

---

## 4. Machine-Readable Agent Integration

For autonomous agent operations, the skill supports the `--json` flag on `inspect`:
```bash
bintriage inspect ./chall --json
```
This returns a structured JSON object containing:
* File metadata: size, SHA-256 hash, entry point, interpreter path, architecture, bitness, endianness.
* Security flags: RELRO state, Canary presence, NX state, PIE state.
* Target functions: Symbol names and hexadecimal addresses of non-boilerplate functions.
* Sensitive imports: System calls and risky standard library references.
* Filtered strings: Flag formats, system paths, and format string candidates.
