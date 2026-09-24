# Deep Dive: `checksec` & Binary Hardening Mitigations

`checksec` ([`/home/wsl/.local/bin/checksec`](file:///home/wsl/.local/bin/checksec)) is a utility designed to inspect the security hardening mitigations compiled into Executable and Linkable Format (ELF) binaries.

Understanding these mitigations is essential for determining viable analysis paths and exploitation constraints.

---

## 1. Summary of Mitigations

| Mitigation | Primary Protection Goal | Implementation Mechanism | ELF Header / Section Marker |
|---|---|---|---|
| **RELRO** | Prevents Global Offset Table (GOT) overwrites | Re-orders sections and marks GOT read-only | `PT_GNU_RELRO` segment + `BIND_NOW` dynamic flag |
| **Stack Canary** | Detects stack buffer overflows before return | Inserts random guard value before saved `$rbp` | `__stack_chk_fail` symbol in `.dynsym` |
| **NX / DEP** | Prevents code execution on stack or heap | CPU NX bit marks writable pages non-executable | `PT_GNU_STACK` flags (`PF_R \| PF_W`, without `PF_X`) |
| **PIE** | Randomizes code segment base address (ASLR) | Compiles executable as position-independent shared object | ELF type `ET_DYN` (PIE) vs `ET_EXEC` (No PIE) |
| **FORTIFY** | Replaces unsafe string/memory calls with bounded variants | Inlines buffer size checks at compile-time | `*_chk` symbols (e.g. `__printf_chk`, `__memcpy_chk`) |

---

## 2. In-Depth Technical Breakdown

### A. RELRO (Relocation Read-Only)
ELF binaries use dynamic linking to resolve library function addresses (e.g. `libc` calls) lazily at runtime:
* **The Vulnerability:** In standard binaries, the Procedure Linkage Table (PLT) uses the Global Offset Table (`.got.plt`) to store resolved pointers. If `.got.plt` remains writable, an attacker can overwrite a function pointer (e.g. replacing `puts` with `win()`).
* **Partial RELRO:**
  * The dynamic loader re-orders internal ELF data sections (`.ctors`, `.dtors`, `.jcr`, `.dynamic`, `.got`) so they precede the program `.data` section.
  * Marks non-PLT GOT sections read-only after relocation.
  * **Weakness:** The PLT GOT (`.got.plt`) remains writable to allow lazy binding.
* **Full RELRO:**
  * Enforces **eager binding** at load time (`-Wl,-z,now` / `BIND_NOW`).
  * Resolves all external function pointers immediately when the program starts.
  * The loader marks the entire `.got` as **read-only** (`mprotect(..., PROT_READ)`).
  * **Result:** Arbitrary GOT overwrites are impossible.

---

### B. Stack Canaries (Stack Smashing Protection - SSP)
* **The Mechanism:** When compiling with `-fstack-protector`, the compiler injects a secret pseudo-random value onto the stack frame directly between local variables and the saved frame pointer (`$rbp`):
  ```text
  [ High Memory ]
    Saved Return Address (RIP)
    Saved Frame Pointer  (RBP)
    Stack Canary (fs:0x28)  <--- Corrupted by overflow
    Local Variables / Buffer
  [ Low Memory ]
  ```
* **Canary Initialization:** On x86_64 Linux, the canary is loaded from Thread Local Storage (TLS) at offset `fs:0x28`.
* **The Null Byte Terminator:** On 64-bit systems, the lowest byte of the canary is always `0x00` (e.g. `0x0061b3f94a28c100`). This ensures string functions like `strcpy`, `strcat`, or `printf("%s")` terminate immediately upon reaching the canary, preventing accidental leaks.
* **Verification:** Immediately before returning from a function, the compiler inserts a check:
  ```assembly
  mov  rax, QWORD PTR [rbp-0x8]
  xor  rax, QWORD PTR fs:0x28
  jne  __stack_chk_fail
  ```
  If corrupted, the process immediately aborts (`*** stack smashing detected ***`).

---

### C. NX / DEP (No-Execute / Data Execution Prevention)
* **The Mechanism:** Operates at the hardware Memory Management Unit (MMU) level using the CPU's **NX (No-Execute) bit** (bit 63 of page table entries).
* **Enforcement:** Enforces the principle of $W \oplus X$ (Write XOR Execute):
  * Code memory is Read + Execute (`r-x`).
  * Data memory (Stack, Heap, BSS) is Read + Write (`rw-`).
* **ELF Marker:** `checksec` reads the `PT_GNU_STACK` program header. If flags are `RW` (`0x6`), NX is enabled. If flags are `RWX` (`0x7`), the stack is executable, allowing direct shellcode execution.

---

### D. PIE (Position Independent Executable) & ASLR
* **Address Space Layout Randomization (ASLR):** A Linux kernel feature that randomizes the base memory addresses of the stack, heap, and loaded libraries (`libc.so`) on each program launch.
* **No PIE (`ET_EXEC`):** The main binary's code segment (`.text`, `.rodata`) is hardcoded to load at fixed virtual addresses (e.g. `0x400000` on x86_64). An attacker can reliably jump to fixed addresses or ROP gadgets without needing an address leak.
* **PIE Enabled (`ET_DYN`):** The binary is compiled as a shared library. The kernel randomizes the base address of the main executable on every run. To jump to any function in the binary, an analyst or exploit must first obtain a memory disclosure (leak) of a code pointer to calculate the randomized base address.

---

### E. FORTIFY_SOURCE
* **The Mechanism:** When compiling with `-D_FORTIFY_SOURCE=2`, GCC substitutes standard unsafe library calls with bounds-checked alternatives when buffer sizes are known at compile time:
  * `memcpy()` $\longrightarrow$ `__memcpy_chk(dest, src, n, dest_size)`
  * `sprintf()` $\longrightarrow$ `__sprintf_chk(...)`
* If `n > dest_size`, the process aborts immediately.
