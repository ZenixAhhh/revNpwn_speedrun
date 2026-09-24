#!/usr/bin/env python3
"""
bintriage - Unified Binary Triage, Disassembly, Crash Analysis & Exploit Scaffolding
Built for CTF reverse engineering and binary exploitation automation with Antigravity (agy).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

try:
    import pwn
    # Disable pwntools update checks
    pwn.context.log_level = 'error'
    PWNTOOLS_AVAILABLE = True
except ImportError:
    PWNTOOLS_AVAILABLE = False


BOILERPLATE_SYMBOLS = {
    '_init', '_fini', '_start', '__libc_csu_init', '__libc_csu_fini',
    'deregister_tm_clones', 'register_tm_clones', '__do_global_dtors_aux',
    'frame_dummy', '__x86.get_pc_thunk.bx', '__x86.get_pc_thunk.dx',
    '__libc_start_main', '__gmon_start__', '_ITM_deregisterTMCloneTable',
    '_ITM_registerTMCloneTable', '__cxa_finalize'
}

SUSPICIOUS_NAMES = [
    'win', 'flag', 'vuln', 'shell', 'backdoor', 'admin', 'secret',
    'auth', 'check', 'validate', 'login', 'hidden', 'system', 'exec'
]

RISKY_IMPORTS = {
    'system', 'execve', 'execvp', 'execl', 'popen', 'gets', 'read',
    'fgets', 'printf', 'fprintf', 'sprintf', 'snprintf', 'strcpy',
    'strcat', 'scanf', 'fscanf', 'sscanf', 'malloc', 'free', 'realloc',
    'mprotect', 'mmap', 'ptrace', 'alarm', 'signal', 'prctl', 'seccomp'
}


def print_msg(msg: str, style: str = ""):
    if RICH_AVAILABLE and console:
        console.print(msg, style=style)
    else:
        print(msg)


def print_error(msg: str):
    if RICH_AVAILABLE and console:
        console.print(f"[bold red][!] Error:[/bold red] {msg}")
    else:
        print(f"[!] Error: {msg}", file=sys.stderr)


def get_file_hashes(filepath: Path) -> dict:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            md5.update(chunk)
            sha256.update(chunk)
    return {
        "md5": md5.hexdigest(),
        "sha256": sha256.hexdigest(),
        "size": filepath.stat().st_size
    }


def analyze_elf(filepath: Path) -> dict:
    info = {
        "path": str(filepath.resolve()),
        "name": filepath.name,
        "is_elf": False,
        "hashes": get_file_hashes(filepath),
        "arch": "unknown",
        "bits": 0,
        "endian": "unknown",
        "stripped": True,
        "entry": 0,
        "interpreter": None,
        "checksec": {
            "relro": "Unknown",
            "canary": False,
            "nx": False,
            "pie": False,
            "fortify": False
        },
        "user_functions": [],
        "target_functions": [],
        "imports": [],
        "libraries": [],
        "seccomp_detected": False,
        "interesting_strings": []
    }

    if not PWNTOOLS_AVAILABLE:
        # Fallback to checksec / file
        cmd = subprocess.run(["file", str(filepath)], capture_output=True, text=True)
        info["raw_file"] = cmd.stdout.strip()
        info["is_elf"] = "ELF" in cmd.stdout
        return info

    try:
        elf = pwn.ELF(str(filepath), checksec=True)
        info["is_elf"] = True
        info["arch"] = elf.arch
        info["bits"] = elf.bits
        info["endian"] = elf.endian
        info["entry"] = hex(elf.entry)
        interp_sec = elf.get_section_by_name('.interp')
        info["interpreter"] = interp_sec.data().rstrip(b'\x00').decode(errors='ignore') if interp_sec else None

        # Checksec
        info["checksec"]["relro"] = elf.relro if elf.relro else "No"
        info["checksec"]["canary"] = bool(elf.canary)
        info["checksec"]["nx"] = bool(elf.nx)
        info["checksec"]["pie"] = bool(elf.pie)

        # Libraries
        info["libraries"] = list(elf.libs.keys()) if hasattr(elf, 'libs') else []

        # Symbols / Functions
        all_symbols = elf.symbols
        info["stripped"] = len(all_symbols) == 0

        user_funcs = []
        target_funcs = []

        for name, addr in all_symbols.items():
            if name in BOILERPLATE_SYMBOLS:
                continue
            if name.startswith('__') or name.startswith('.'):
                continue
            
            func_data = {"name": name, "address": hex(addr)}
            user_funcs.append(func_data)
            
            # Check for suspicious / high-value names
            lower_name = name.lower()
            if any(s in lower_name for s in SUSPICIOUS_NAMES):
                target_funcs.append(func_data)

        info["user_functions"] = sorted(user_funcs, key=lambda x: x["name"])
        info["target_functions"] = sorted(target_funcs, key=lambda x: x["name"])

        # Imports / GOT
        imports = []
        for name in elf.got.keys():
            is_risky = name in RISKY_IMPORTS
            imports.append({"name": name, "risky": is_risky})
            if name in ('prctl', 'seccomp'):
                info["seccomp_detected"] = True

        info["imports"] = sorted(imports, key=lambda x: (not x["risky"], x["name"]))

        # Interesting strings
        strings_cmd = subprocess.run(["strings", "-n", "4", str(filepath)], capture_output=True, text=True)
        if strings_cmd.returncode == 0:
            interesting = []
            flag_patterns = re.compile(r'(flag\{|ctf\{|admin|password|token|/bin/sh|/bin/bash|/bin/cat|%[0-9]*[spdxfn])', re.IGNORECASE)
            for line in strings_cmd.stdout.splitlines():
                line = line.strip()
                if flag_patterns.search(line) and len(line) <= 120:
                    if line not in interesting:
                        interesting.append(line)
                if 'seccomp' in line.lower() or 'bpf' in line.lower():
                    info["seccomp_detected"] = True
            info["interesting_strings"] = interesting[:30]

    except Exception as e:
        info["error"] = str(e)

    return info


def inspect_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    info = analyze_elf(filepath)

    if args.json:
        print(json.dumps(info, indent=2))
        return

    if not RICH_AVAILABLE:
        print(f"=== File: {info['name']} ===")
        print(f"Size: {info['hashes']['size']} bytes | SHA256: {info['hashes']['sha256']}")
        print(f"Arch: {info['arch']} ({info['bits']}-bit, {info['endian']}) | Entry: {info['entry']}")
        print(f"Mitigations: RELRO={info['checksec']['relro']}, Canary={info['checksec']['canary']}, NX={info['checksec']['nx']}, PIE={info['checksec']['pie']}")
        print(f"Stripped: {info['stripped']} | Seccomp: {info['seccomp_detected']}")
        if info["target_functions"]:
            print("Target/Interesting Functions:")
            for f in info["target_functions"]:
                print(f"  - {f['name']} ({f['address']})")
        if info["imports"]:
            print("Notable Imports:")
            for imp in [i for i in info["imports"] if i["risky"]]:
                print(f"  - {imp['name']}")
        if info["interesting_strings"]:
            print("Interesting Strings:")
            for s in info["interesting_strings"][:10]:
                print(f"  - {s}")
        return

    # Rich formatted output
    table_file = Table(title="📦 Binary Information", box=box.ROUNDED, expand=True)
    table_file.add_column("Property", style="cyan", width=18)
    table_file.add_column("Value", style="white")

    table_file.add_row("File Path", info["path"])
    table_file.add_row("Size", f"{info['hashes']['size']:,} bytes")
    table_file.add_row("SHA-256", info["hashes"]["sha256"])
    table_file.add_row("Arch & Bitness", f"{info['arch']} ({info['bits']}-bit, {info['endian']}-endian)")
    table_file.add_row("Entry Point", str(info["entry"]))
    table_file.add_row("Stripped", "[yellow]Yes[/yellow]" if info["stripped"] else "[green]No[/green]")
    if info["interpreter"]:
        table_file.add_row("Interpreter", info["interpreter"])

    console.print(table_file)

    # Mitigations Table
    table_sec = Table(title="🛡️ Security Mitigations (Checksec)", box=box.ROUNDED, expand=True)
    table_sec.add_column("RELRO", justify="center")
    table_sec.add_column("Stack Canary", justify="center")
    table_sec.add_column("NX / DEP", justify="center")
    table_sec.add_column("PIE", justify="center")
    table_sec.add_column("Seccomp", justify="center")

    relro_val = f"[green]{info['checksec']['relro']}[/green]" if info['checksec']['relro'] == "Full" else (
        f"[yellow]{info['checksec']['relro']}[/yellow]" if info['checksec']['relro'] == "Partial" else f"[red]{info['checksec']['relro']}[/red]"
    )
    canary_val = "[green]Enabled[/green]" if info['checksec']['canary'] else "[red]Disabled[/red]"
    nx_val = "[green]Enabled[/green]" if info['checksec']['nx'] else "[red]Disabled[/red]"
    pie_val = "[green]Enabled[/green]" if info['checksec']['pie'] else "[red]Disabled[/red]"
    seccomp_val = "[bold yellow]Detected[/bold yellow]" if info['seccomp_detected'] else "[dim]Not Detected[/dim]"

    table_sec.add_row(relro_val, canary_val, nx_val, pie_val, seccomp_val)
    console.print(table_sec)

    # Target Functions
    if info["target_functions"]:
        table_target = Table(title="🎯 High-Value / Target Functions", box=box.ROUNDED, expand=True)
        table_target.add_column("Function Name", style="bold yellow")
        table_target.add_column("Address", style="cyan")
        for f in info["target_functions"]:
            table_target.add_row(f["name"], f["address"])
        console.print(table_target)
    elif info["user_functions"]:
        table_funcs = Table(title=f"📋 User Functions ({len(info['user_functions'])})", box=box.ROUNDED, expand=True)
        table_funcs.add_column("Function Name", style="white")
        table_funcs.add_column("Address", style="cyan")
        for f in info["user_functions"][:15]:
            table_funcs.add_row(f["name"], f["address"])
        if len(info["user_functions"]) > 15:
            table_funcs.add_row(f"... and {len(info['user_functions']) - 15} more", "")
        console.print(table_funcs)

    # Notable Imports
    risky_imps = [i["name"] for i in info["imports"] if i["risky"]]
    if risky_imps:
        console.print(Panel(
            Text(", ".join(risky_imps), style="bold magenta"),
            title="⚠️ Notable / Sensitive Imported Functions",
            box=box.ROUNDED
        ))

    # Interesting Strings
    if info["interesting_strings"]:
        strings_table = Table(title="🔍 Interesting Strings Extracted", box=box.ROUNDED, expand=True)
        strings_table.add_column("String Match", style="green")
        for s in info["interesting_strings"][:12]:
            strings_table.add_row(s)
        console.print(strings_table)


def disasm_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    target_func = args.function or "main"

    # Try objdump first
    cmd = ["objdump", "-d", "-M", "intel", "--no-show-raw-insn", str(filepath)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = proc.stdout
        
        # Extract the function
        func_regex = re.compile(rf"(^[0-9a-fA-F]+\s+<[^>]*\b{re.escape(target_func)}\b[^>]*>:.*?)(?=\n\n|\Z)", re.DOTALL | re.MULTILINE)
        match = func_regex.search(output)
        if match:
            print_msg(f"=== Disassembly of {target_func} ===", "bold cyan")
            print(match.group(1))
            return
        else:
            # Fallback: check if target is an address
            if target_func.startswith("0x"):
                addr_hex = target_func[2:]
                addr_regex = re.compile(rf"(^[0-9a-fA-F]*{addr_hex}\s+<.*?:.*?)(?=\n\n|\Z)", re.DOTALL | re.MULTILINE)
                match = addr_regex.search(output)
                if match:
                    print(match.group(1))
                    return

            print_error(f"Function/symbol '{target_func}' not found in objdump output. Listing available symbols...")
            symbols_cmd = subprocess.run(["nm", "--defined-only", str(filepath)], capture_output=True, text=True)
            if symbols_cmd.returncode == 0:
                print(symbols_cmd.stdout[:500])
    except Exception as e:
        print_error(f"Failed to disassemble: {e}")


def decompile_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    target_func = args.function or "main"

    # Check for radare2
    r2_path = shutil.which("r2")
    if r2_path:
        print_msg(f"[*] Decompiling '{target_func}' via Radare2...", "cyan")
        # Try pdg (r2ghidra) or pdc (r2 pseudocode)
        cmd_ghidra = [r2_path, "-qc", f"aaa; pdg @ sym.{target_func} || pdg @ {target_func}", str(filepath)]
        proc = subprocess.run(cmd_ghidra, capture_output=True, text=True)
        if proc.returncode == 0 and len(proc.stdout.strip()) > 30 and "ERROR" not in proc.stdout:
            print(proc.stdout)
            return

        # Fallback to pdc
        cmd_pdc = [r2_path, "-qc", f"aaa; pdc @ sym.{target_func} || pdc @ {target_func}", str(filepath)]
        proc_pdc = subprocess.run(cmd_pdc, capture_output=True, text=True)
        if proc_pdc.returncode == 0 and len(proc_pdc.stdout.strip()) > 20:
            print(proc_pdc.stdout)
            return

    print_error("No native decompiler plugin (r2ghidra / pdg) found. Falling back to assembly disassembly.")
    disasm_command(args)


def crash_test_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    payload = b""
    is_cyclic = False
    cyclic_len = 0

    if args.cyclic:
        if not PWNTOOLS_AVAILABLE:
            print_error("Pwntools is required for --cyclic generation.")
            sys.exit(1)
        cyclic_len = args.cyclic
        payload = pwn.cyclic(cyclic_len)
        is_cyclic = True
        print_msg(f"[*] Generated {cyclic_len}-byte cyclic pattern", "cyan")
    elif args.payload:
        payload = args.payload.encode('latin1')
    elif args.file:
        with open(args.file, 'rb') as f:
            payload = f.read()
    else:
        print_error("Specify --cyclic <length>, --payload <string>, or --file <path> to test crash.")
        sys.exit(1)

    # Save payload to temp file
    payload_file = Path("/tmp/bintriage_payload.bin")
    payload_file.write_bytes(payload)

    # Construct GDB batch script
    gdb_script = Path("/tmp/bintriage_run.gdb")
    extra_args = args.args if args.args else ""
    gdb_script.write_text(f"""
set pagination off
set confirm off
set debuginfod enabled off
r {extra_args} < {payload_file}
echo \\n=== CRASH DIAGNOSTIC ===\\n
info program
echo \\n=== REGISTERS ===\\n
info registers
echo \\n=== STACK DUMP ===\\n
x/16gx $rsp
echo \\n=== DISASSEMBLY AT FAULT ===\\n
x/5i $rip
quit
""")

    print_msg(f"[*] Running {filepath.name} under GDB batch mode...", "cyan")
    cmd = ["gdb", "-nx", "--batch", "-x", str(gdb_script), str(filepath)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = proc.stdout + proc.stderr

        # Check for crash signals
        crashed = False
        signal_name = "None"
        for sig in ["SIGSEGV", "SIGBUS", "SIGILL", "SIGFPE", "SIGABRT"]:
            if sig in output:
                crashed = True
                signal_name = sig
                break

        if not crashed:
            print_msg(f"[+] Program exited without fatal signal (no crash detected).", "green")
            if "exited normally" in output:
                print_msg("[+] Process exited normally.", "green")
            else:
                lines = [l for l in output.splitlines() if "exited with code" in l]
                if lines:
                    print(lines[0])
            return

        print_msg(f"[bold red][!] CRASH DETECTED: {signal_name}[/bold red]")

        # Extract registers
        regs = {}
        for reg in ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp', 'rip', 'eip']:
            m = re.search(rf"\b{reg}\s+(0x[0-9a-fA-F]+|\d+)", output)
            if m:
                regs[reg] = m.group(1)

        # Extract stack top values
        stack_vals = []
        stack_matches = re.findall(r"0x[0-9a-fA-F]+:\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)", output)
        for row in stack_matches:
            stack_vals.extend(row)

        # Print summary table
        if RICH_AVAILABLE:
            t = Table(title="💥 Crash State", box=box.ROUNDED)
            t.add_column("Register", style="cyan")
            t.add_column("Value", style="bold yellow")
            t.add_column("Cyclic Match", style="bold red")

            for reg, val in regs.items():
                match_str = ""
                if is_cyclic and PWNTOOLS_AVAILABLE:
                    try:
                        int_val = int(val, 16) if val.startswith("0x") else int(val)
                        offset = pwn.cyclic_find(int_val & 0xffffffff)
                        if offset != -1:
                            match_str = f"Offset: {offset} bytes"
                    except Exception:
                        pass
                t.add_row(reg.upper(), val, match_str)
            console.print(t)
        else:
            print("Registers:")
            for reg, val in regs.items():
                print(f"  {reg.upper()}: {val}")

        # Check cyclic match for rip/eip or stack top
        if is_cyclic and PWNTOOLS_AVAILABLE:
            found_rip = False
            for ip_reg in ['rip', 'eip']:
                if ip_reg in regs:
                    try:
                        ip_val = int(regs[ip_reg], 16)
                        offset = pwn.cyclic_find(ip_val & 0xffffffff)
                        if offset != -1:
                            print_msg(f"\n[bold green]🎯 BINGO! {ip_reg.upper()} overwritten at cyclic offset: {offset} bytes[/bold green]")
                            found_rip = True
                    except Exception:
                        pass

            # If rip wasn't directly overwritten (e.g. crashed on ret popping non-canonical address), check stack top
            if not found_rip and stack_vals:
                for s_val in stack_vals[:4]:
                    try:
                        s_int = int(s_val, 16)
                        offset = pwn.cyclic_find(s_int & 0xffffffff)
                        if offset != -1:
                            print_msg(f"\n[bold green]🎯 BINGO! Saved RET address at stack top matches cyclic offset: {offset} bytes[/bold green]")
                            break
                    except Exception:
                        pass

    except subprocess.TimeoutExpired:
        print_error("Execution timed out after 10s. The binary may be waiting for more input or blocked.")
    finally:
        payload_file.unlink(missing_ok=True)
        gdb_script.unlink(missing_ok=True)


def seccomp_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    seccomp_tool = shutil.which("seccomp-tools")
    if seccomp_tool:
        print_msg(f"[*] Dumping seccomp BPF filter via seccomp-tools...", "cyan")
        subprocess.run([seccomp_tool, "dump", str(filepath)])
    else:
        print_msg("[!] seccomp-tools not found. Checking binary imports/strings for seccomp signatures...", "yellow")
        info = analyze_elf(filepath)
        if info["seccomp_detected"]:
            print_msg("[+] Binary contains references to seccomp/prctl/BPF.", "green")
        else:
            print_msg("[-] No seccomp signatures found.", "dim")


def rop_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    rop_tool = shutil.which("ROPgadget") or shutil.which("ropper")
    if not rop_tool:
        print_error("Neither ROPgadget nor ropper is installed in PATH.")
        sys.exit(1)

    cmd = [rop_tool, "--binary", str(filepath)]
    if args.grep:
        if "ROPgadget" in rop_tool:
            cmd.extend(["--only", args.grep])
        else:
            cmd.extend(["--search", args.grep])

    print_msg(f"[*] Searching gadgets using {Path(rop_tool).name}...", "cyan")
    subprocess.run(cmd)


def scaffold_command(args):
    filepath = Path(args.binary)
    if not filepath.exists():
        print_error(f"File not found: {filepath}")
        sys.exit(1)

    info = analyze_elf(filepath)
    out_file = Path(args.output or "solve.py")

    template = f'''#!/usr/bin/env python3
# Solver template generated by bintriage for {info['name']}
from pwn import *

# === Binary Configuration ===
exe = "{info['path']}"
elf = context.binary = ELF(exe, checksec=False)
context.terminal = ["tmux", "splitw", "-h"]
context.log_level = "info"

# Remote target (format: host:port)
HOST, PORT = "{args.remote.split(':')[0] if args.remote else '127.0.0.1'}", {args.remote.split(':')[1] if args.remote and ':' in args.remote else '1337'}

def start(argv=[], *a, **kw):
    if args.REMOTE:
        return remote(HOST, PORT, *a, **kw)
    elif args.GDB:
        gdbscript = """
        init-pwndbg
        # break *main
        continue
        """
        return gdb.debug([exe] + argv, gdbscript=gdbscript, *a, **kw)
    else:
        return process([exe] + argv, *a, **kw)

io = start()

# === Exploit Logic ===
# Target Functions:
'''
    for f in info['target_functions']:
        template += f'#   {f["name"]}: {f["address"]}\n'

    template += '''
# io.sendline(b"payload")
io.interactive()
'''

    out_file.write_text(template)
    out_file.chmod(0o755)
    print_msg(f"[+] Exploit scaffold written to [bold green]{out_file}[/bold green]", "green")


def main():
    parser = argparse.ArgumentParser(
        description="bintriage - Unified Binary Triage & Dynamic Crash Analysis for CTF",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Deep static inspection and mitigation check")
    p_inspect.add_argument("binary", help="Target binary path")
    p_inspect.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_inspect.set_defaults(func=inspect_command)

    # disasm
    p_disasm = subparsers.add_parser("disasm", help="Disassemble function or address")
    p_disasm.add_argument("binary", help="Target binary path")
    p_disasm.add_argument("function", nargs="?", default="main", help="Function name or address (default: main)")
    p_disasm.set_defaults(func=disasm_command)

    # decompile
    p_decomp = subparsers.add_parser("decompile", help="Decompile function via r2/ghidra")
    p_decomp.add_argument("binary", help="Target binary path")
    p_decomp.add_argument("function", nargs="?", default="main", help="Function name (default: main)")
    p_decomp.set_defaults(func=decompile_command)

    # crash-test
    p_crash = subparsers.add_parser("crash-test", help="Test payload against binary under GDB non-interactively")
    p_crash.add_argument("binary", help="Target binary path")
    p_crash.add_argument("--cyclic", type=int, help="Generate and send cyclic pattern of length N")
    p_crash.add_argument("--payload", help="Raw string payload")
    p_crash.add_argument("--file", help="File containing binary payload")
    p_crash.add_argument("--args", help="Command-line arguments to pass to the binary")
    p_crash.set_defaults(func=crash_test_command)

    # seccomp
    p_seccomp = subparsers.add_parser("seccomp", help="Inspect seccomp BPF filter rules")
    p_seccomp.add_argument("binary", help="Target binary path")
    p_seccomp.set_defaults(func=seccomp_command)

    # rop
    p_rop = subparsers.add_parser("rop", help="Find ROP gadgets")
    p_rop.add_argument("binary", help="Target binary path")
    p_rop.add_argument("--grep", help="Filter pattern for gadgets (e.g. 'pop rdi')")
    p_rop.set_defaults(func=rop_command)

    # scaffold
    p_scaffold = subparsers.add_parser("scaffold", help="Generate solve.py exploit template")
    p_scaffold.add_argument("binary", help="Target binary path")
    p_scaffold.add_argument("-o", "--output", help="Output file path (default: solve.py)")
    p_scaffold.add_argument("--remote", help="Remote host:port string")
    p_scaffold.set_defaults(func=scaffold_command)

    # If first arg is a file and not a subcommand, default to inspect
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-") and sys.argv[1] not in subparsers.choices:
        if os.path.exists(sys.argv[1]):
            sys.argv.insert(1, "inspect")

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
