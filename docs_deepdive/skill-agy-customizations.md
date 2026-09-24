# Deep Dive: Antigravity Customization System (`agy-customizations`)

The Antigravity Customization System enables deep configuration of agent behavior, workflow orchestration, rule enforcement, and external tool integration across workspaces.

---

## 1. Customization Taxonomy

| Type | Configuration File/Folder | Scope | Primary Purpose |
|---|---|---|---|
| **Rules** | `GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md` | Contextual / Hierarchical | Enforces coding standards, security boundaries, and local workspace guidelines. |
| **Skills** | `skills/<name>/SKILL.md` | On-Demand (Progressive) | Multi-step procedures, runbooks, and specialized playbooks loaded only when needed. |
| **Plugins** | `plugins/<name>/plugin.json` | Bundle | Bundles related skills, rules, and MCP configurations into a portable unit. |
| **Hooks** | `hooks.json` | Lifecycle Event | Runs scripts at specific agent lifecycle trigger points (e.g. pre-tool execution). |
| **MCP Servers** | `mcp_config.json` | Tool Integration | Connects the agent to Model Context Protocol (MCP) servers and external services. |

---

## 2. Discovery Mechanisms & Locations

Antigravity automatically discovers customizations by traversing specific paths:

1. **Workspace Project Level (Highest Precedence):**
   * Path: `.agents/` (or `.agent/`, `_agents/`) at the repository root.
   * Walks up from current working directory to the Git root.
2. **Directory & Project Rules (Hierarchical):**
   * Paths: `GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md`.
   * Automatically loaded as the agent accesses files in that directory subtree.
3. **Global Machine-Local Level:**
   * Path: `~/.gemini/config/` (contains `skills/`, `skills.json`, `mcp_config.json`).
   * Applies across all projects and terminals on the host machine.
4. **Built-in Application Level:**
   * Bundled with the AGY installation (`/home/wsl/.gemini/antigravity-cli/builtin/skills/`).

---

## 3. Loading Priority & Precedence

When multiple definitions share the same identifier, higher-priority locations override lower ones:

$$\text{Workspace Project (.agents/)} \succ \text{Declared Configs (skills.json)} \succ \text{Global Discovery (~/.gemini/config/)} \succ \text{Built-in Skills} \succ \text{Global Declared}$$

---

## 4. Context Optimization Mechanisms

### A. Progressive Disclosure
To prevent overflowing the LLM context window with thousands of lines of documentation:
* **Skills:** Only metadata (name and brief description from the YAML frontmatter) is initially injected into the system prompt.
* **Full Loading:** The complete instructions and reference files of a skill are loaded into context **only** when explicitly invoked by the user (`/<skill_name>`) or when the agent selects it based on task relevance.

### B. Deduplication
Customizations (especially rules) are deduplicated by their resolved absolute canonical file paths. A rule is never injected into the context window more than once per turn, even if triggered by multiple matching conditions.

---

## 5. Skill Directory Layout

A standard Antigravity skill follows this internal layout:
```text
skills/<skill-name>/
├── SKILL.md            # REQUIRED: YAML frontmatter (name, description) + instructions
├── scripts/            # Helper automation scripts executable by the agent
├── references/         # In-depth technical documentation read on demand
└── assets/             # Templates, configuration files, or data schemas
```
