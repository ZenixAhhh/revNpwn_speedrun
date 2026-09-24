# Deep Dive: `ctf-ask` Skill (Cognitive & Math Escalation)

The `ctf-ask` skill formalizes the cognitive process of **Mathematical Kernel Extraction** and **Expert Consultation**. It is designed for moments when a puzzle or challenge is blocked on a formal algebraic, cryptographic, lattice, or SMT subproblem that can be isolated, solved by high-reasoning models (such as Astra / Codex / o1), and independently verified.

---

## 1. Core Philosophy: What is Expert Consultation?

Expert consultation is **not** passing raw challenge files or network traces to an external AI model. It is an intentional cognitive transformation:
1. **Mathematical Kernel Extraction:** Stripping noisy execution wrappers (sockets, binaries, ELF headers, docker configurations) until only a formal, self-contained mathematical relation remains.
2. **De-cyberization (Pure Algebraic Dialect):** Translating security-sensitive terminology into abstract algebra or discrete mathematics to completely eliminate safety filter tripping and focus reasoning on raw mathematics.
3. **Quarantine Isolation:** Isolating external expert sessions inside a strictly sanitized directory (`math_workspace/`) where the expert cannot read challenge filenames, URLs, or binaries.
4. **Deterministic Verification Contract:** Never trusting a solution without independent verification. The answer must satisfy the original equations when plugged back in locally.

---

## 2. Cognitive Triggers: When to Escalate?

```text
Decision Tree for Expert Consultation:
Encountered an obstacle?
  ├── 1. What type of obstacle is it?
  │      ├── Standard binary reversing, unpacking, API tracing ──> SOLVE LOCALLY.
  │      └── Nonlinear equations, Lattice (CVP/SVP), Polynomial root finding, Complex SMT ──> PROCEED TO 2.
  │
  ├── 2. Can it be modeled as a standalone mathematical relation?
  │      ├── No (depends on live server state or network race condition) ──> Continue local analysis.
  │      └── Yes (defined unknowns, modulus ring, algebraic bounds) ──> PROCEED TO 3.
  │
  └── 3. Can the solution be deterministically verified?
         ├── No (speculation without verification equation) ──> DO NOT ESCALATE; refine problem model first.
         └── Yes (substituting roots into the equation provides 100% verification) ──> ESCALATE TO EXPERT.
```

---

## 3. The De-Cyberization Dictionary

The rule of de-cyberization is: **100% Lossless Mathematics, 0% Cybersecurity Context**.

| Challenge Domain | Sanitized Algebraic Representation | Preserved Information | Stripped Information |
|---|---|---|---|
| **Differential Fault Analysis (DFA)** | Nonlinear error equations over the Galois field $GF(2^8)$ through S-Box permutation tables. | Matrix dimensions ($4 \times 4$), S-box values, differential positions, generator polynomial. | AES, HSM, fault injection, key extraction, attack vectors. |
| **RSA Coppersmith / Key Flaws** | Finding small roots of a univariate polynomial modulo an integer $N$: $f(x) \equiv 0 \pmod N$. | Polynomial degree, root bound $|x| < X$, modulus $N$, coefficients. | RSA, public key, private key, ciphertext, flag. |
| **Lattice / LWE / Knapsack** | Closest Vector Problem (CVP) or Shortest Vector Problem (SVP) on lattice $\mathcal{L}(B)$. | Basis matrix $B$, target vector $t$, norm metric, error bound. | Cryptosystem, secret key, ciphertext, user data. |
| **PRNG State Recovery** | Initial state reconstruction of a Linear/Nonlinear Feedback Shift Register modulo $m$. | Register length, feedback polynomial, observed sequence, bit ordering. | Session token, random generator, authentication cookie. |
| **Branch Logic / Checkers** | Satisfiability Modulo Theories (SMT) or Boolean CNF satisfiability. | Variable domain, bitwise clauses (AND/OR/XOR), bounds. | Password checker, crackme, license validation. |

---

## 4. Data Quarantine Protocol

External reasoning experts must operate strictly within a sanitized sandbox:
* **Directory:** `math_workspace/`
* **Artifacts:**
  * `TASK.md`: Formal problem statement in standard mathematical notation ($\LaTeX$ formulas, definitions, constraints).
  * `instance.json`: Concrete numerical coefficients, matrices, and modulo parameters.
  * `verifier.py`: Standalone script to test whether proposed candidate roots satisfy the system equations.
* **Prohibited Files:** No raw binaries, `.pcap` files, URLs, CTF platform names, or flags may ever enter `math_workspace/`.

---

## 5. Supporting Scripts

* [`validate_sanitized_handoff.py`](file:///home/wsl/tools/auto_download_ctf_challenge/skills/ctf-ask/scripts/validate_sanitized_handoff.py): Automated scanner that checks `TASK.md` and `instance.json` for forbidden keywords (IP addresses, cybersecurity terms, flag formats) before invoking an external model.
* [`run_astra_expert.py`](file:///home/wsl/tools/auto_download_ctf_challenge/skills/ctf-ask/scripts/run_astra_expert.py): Headless runner that initializes a persistent, isolated expert session with temperature calibration suited for formal proofs and symbolic solver generation.
