# Deep Dive: `cyclic` & De Bruijn Pattern Offset Discovery

`cyclic` ([`/home/wsl/.local/bin/cyclic`](file:///home/wsl/.local/bin/cyclic), provided by `pwntools`) is a non-repeating pattern generator and offset recovery utility. It automates the discovery of exact stack offsets, register overwrites, and memory corruptions without manual calculation.

---

## 1. Mathematical Foundation: De Bruijn Sequences

A naive buffer overflow payload consists of repetitive bytes (e.g. `400 * 'A'`). While this demonstrates a crash, the faulting register displays `0x41414141`, giving no indication of *which* specific byte in the 400-byte sequence overwrote the instruction pointer.

`cyclic` solves this using **De Bruijn Sequences**:
* A De Bruijn sequence $B(k, n)$ over an alphabet of size $k$ is a cyclic sequence where every possible subsequence of length $n$ appears **exactly once** as a contiguous substring.
* In `pwntools`, the default alphabet uses lowercase English characters ($k = 26$) with subsequence window size $n = 4$:
  $$\text{Alphabet: } \Sigma = \{a, b, c, \dots, z\}, \quad k = 26, \quad n = 4$$
* **Maximum Non-Repeating Length:**
  $$\text{Length} = k^n = 26^4 = 456,976 \text{ bytes}$$
* Any 4-byte slice taken from this pattern is mathematically unique within the first 456,976 bytes.

```text
Sequence Layout:
Index:   0    4    8    12   16   20   24   28
Bytes:   aaaa baaa caaa daaa eaaa faaa gaaa haaa ...
```

---

## 2. Endianness & Register Representation

When a 4-byte string is placed on the stack and read into an integer register on little-endian x86/x64 systems, the byte order is reversed:

| Substring in Memory | Memory Byte Values | Register Value (Little-Endian) |
|---|---|---|
| `"aaaa"` | `0x61, 0x61, 0x61, 0x61` | `0x61616161` |
| `"baaa"` | `0x62, 0x61, 0x61, 0x61` | `0x61616162` |
| `"saaa"` | `0x73, 0x61, 0x61, 0x61` | `0x61616173` |

`cyclic_find()` accepts either:
* The integer hex value directly from the register: `cyclic_find(0x61616173)` $\to$ `72`
* The raw ASCII string: `cyclic_find(b"saaa")` $\to$ `72`

---

## 3. The 64-Bit Non-Canonical Addressing Nuance

In 32-bit systems, the CPU attempts to pop any 32-bit value into `$eip`. If the pattern overwrote the stack, `$eip` cleanly displays `0x61616162`, and the crash signal identifies the exact offset.

In 64-bit systems (x86_64), virtual addresses are limited to 48 bits (bits 48 to 63 must be identical to bit 47—known as **canonical form**).
* An 8-byte ASCII pattern like `"saataaaa"` corresponds to `0x6161617461616173`.
* Because bits 48–63 are not sign-extended, this address is **non-canonical**.
* When the CPU executes `ret`, the MMU raises a General Protection Fault (`SIGSEGV`) **on the `ret` instruction itself**, before the non-canonical address can be loaded into `$rip`.
* **The Solution:** In 64-bit binaries, when `$rip` remains at the function's final `ret` instruction, inspect the value at the top of the stack (`$rsp`). That top value is the exact sequence that was about to be popped into `$rip`:
  ```bash
  # Inside GDB:
  x/gx $rsp
  # Returns: 0x6161617461616173
  # Calculate offset:
  cyclic -l 0x6161617461616173
  ```

---

## 4. CLI & Python Reference

```bash
# Generate 150-byte pattern to stdout
cyclic 150

# Output pattern to a file
cyclic 200 > payload.bin

# Find offset of faulting register
cyclic -l 0x61616172
# Output: 64

# 64-bit window generation (n=8)
cyclic -n 8 200
```

### Python API:
```python
from pwn import *

# Generate pattern
pattern = cyclic(128)

# Find offset from integer or bytes
offset_rbp = cyclic_find(0x6161617261616171 & 0xffffffff) # 64
offset_rip = cyclic_find(0x6161617461616173 & 0xffffffff) # 72
```
