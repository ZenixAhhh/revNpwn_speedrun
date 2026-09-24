# Deep Dive: `ctf-toolkit` Skill

The `ctf-toolkit` skill is the primary operational playbook for autonomous and interactive CTF management in the Antigravity ecosystem. It translates terse human input into deterministic command executions, enforces workspace boundaries, and coordinates challenge infrastructure.

---

## 1. Core Architecture & Philosophy

The skill operates on three non-negotiable principles:
1. **Preserve Momentum:** When a user enters shorthand like `pwn5` or `next`, the agent must not ask clarifying questions or respond with filler conversation. It immediately executes the next verification or state transition.
2. **Deterministic Evidence Contract:** No challenge is ever marked solved based on heuristic assumption. Proof must exist as reproducible code in `solver/solve.py` or output in `script/analysis.md`.
3. **Mandatory Human Submission Rule:** The agent and any automated subagent are strictly forbidden from calling `ctf submit` or automated submission hooks. Candidate flags are hoarded locally using `ctf hoard` for human terminal review.

---

## 2. Prompt-as-Command Routing (PACR)

The skill uses an internal precedence evaluator located in [`scripts/route_prompt.py`](file:///home/wsl/tools/auto_download_ctf_challenge/skills/ctf-toolkit/scripts/route_prompt.py) matching [`assets/command-routes.yaml`](file:///home/wsl/tools/auto_download_ctf_challenge/skills/ctf-toolkit/assets/command-routes.yaml).

```text
Strict Precedence Order:
REJECT_CANDIDATE ──> STATUS ──> CONTINUE ──> SELECT ──> HYPOTHESIS ──> CONSTRAINT
```

### Route Table & Dispatch Actions

| Input Pattern | Routed Action | Concrete Dispatch Behavior |
|---|---|---|
| `pwn5`, `rev12`, `Lottery`, `crypto_3` | `SELECT` | Resolves challenge folder via `workspace_locator.py`. Reads `metadata.json`, `challenge/NOTE.md`, and files in `challenge/`. Begins triage immediately without conversational prompts. |
| `next`, `nexxt`, `continue`, `tiếp tục` | `CONTINUE` | Inspects `script/` state, determines the latest unfinished verification probe, and executes the next step. |
| `tiến độ`, `tieens ddooj`, `status` | `STATUS` | Emits a structured 4-bullet card: (1) Current Phase, (2) Verified Facts, (3) Next Planned Probe, (4) Active Blocker. |
| `decoy`, `cái này là flag decoy` | `REJECT_CANDIDATE` | Updates `script/analysis.md`, marks the candidate as `REJECTED`, records provenance, and pivots execution to the next branch. |
| `có thể đó là hint...` | `HYPOTHESIS` | Formalizes the hypothesis in `script/` and constructs a targeted probe to validate it. |
| `server chỉ connect qua lan`, `dùng mcp` | `CONSTRAINT` | Updates in-memory execution parameters (e.g. proxying or networking limits) without wiping existing discovery. |

---

## 3. Workspace Directory Contract

The skill enforces a clean, three-directory separation of concerns for every challenge:

```text
<workspace>/<category>/<challenge_name>/
├── challenge/          # READ-ONLY source files, binaries, attachments, and NOTE.md
├── script/             # SCRATCH environment: exploration probes, logs, analysis.md
└── solver/             # REPRODUCIBLE final solution: solve.py and test assertions
```

### Candidate Flag State Machine
Every potential flag discovered during analysis progresses through three explicit states in `script/analysis.md`:
* `CANDIDATE`: An unverified string matching the flag format pattern.
* `VERIFIED`: Re-executed deterministically against the local or remote target with proof.
* `REJECTED`: Discarded as a decoy or test string.

---

## 4. 3-Tier Safety Filter Recovery Protocol

When an LLM model encounters content policy blocks or refusal loops during CTF analysis, the skill defines a rigid 3-tier rescue protocol:

```mermaid
flowchart TD
    Block[Model Filter Triggered] --> T1[Tier 1: Directed Micro-Prompt]
    T1 -->|Refusal Persists| T2[Tier 2: Context Rollback & History Pruning]
    T2 -->|Refusal Persists| T3[Tier 3: Mathematical / Logic Isolation]
    T3 --> AskSkill[Invoke 'ctf-ask' with pure abstract math formulation]
```

1. **Tier 1 (Directed Micro-Prompt):** Dispatch a minimal, non-conversational directive like `/ctf-toolkit next: continue logic verification`.
2. **Tier 2 (Context Rollback):** Prune the poisoned conversation turn using `/rewind` or session restart so refusal momentum does not contaminate future reasoning.
3. **Tier 3 (Math/Logic Isolation):** Decouple the problem completely from cybersecurity terminology. Strip binary artifacts, IPs, and protocol labels into an abstract algebra or state-machine specification and hand off to the `ctf-ask` skill.

---

## 5. Canonical Command Reference

* `ctf auth --from-burp -u <URL>`: Syncs cookies and authorization tokens from local Burp Suite proxy.
* `ctf pull -u <URL> -o <DIR> --verify-downloads strict`: Pulls challenges and attachments with SHA-256 validation.
* `ctf instance start --id <ID> -w <WORKSPACE>`: Launches dynamic challenge containers.
* `ctf hoard <ID> "FLAG{...}"`: Persists a discovered flag to the local hoard without submitting.
* `ctf doctor --runtime`: Runs local environment dependency checks.
* `ctf config theme <THEME>`: Switches terminal styling (`cyberpunk`, `matrix`, `exodia`, `dracula`).
