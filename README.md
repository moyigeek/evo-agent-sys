# Evo Agent System

A Recursive Self-Improvement (RSI) agent system.

**Core principle: "Clone → Test → Swap → Restart"**

The Evo Agent cannot directly overwrite its own source code while running. Every self-modification must follow a strict evolution protocol enforced by a parent watchdog process (Base-OS).

## Architecture

```
evo-agent-sys/
├── base_os/                       # Immutable watchdog layer
│   └── os_kernel.py               # Exit code supervisor + upgrade/rollback logic
├── build_kernel.sh                # PyInstaller script → compiles Base-OS to binary
├── kernel                         # Compiled Base-OS binary (built once, never modified)
├── evo_agent_active/              # Mutable agent codebase (can be rewritten by LLM)
│   ├── main.py                    # Entry point + evolution protocol + ReAct loop
│   ├── memory.py                  # State persistence (JSON)
│   ├── reasoning.py               # ReAct reasoning framework
│   ├── system_prompt.py           # Architectural guardrails injected as system prompt
│   ├── llm.py                     # LLM client (zero external dependencies)
│   └── skills/
│       └── __init__.py            # Tool registry with built-in skills
├── .env                           # LLM credentials (user-editable)
├── staging_area/                  # Draft area for new code (generated at runtime)
├── history_versions/              # Version snapshots for rollback (generated at runtime)
├── .evo_state.json                # Persisted agent state
├── .evo_recovery_message.json     # Rollback recovery message (written by Base-OS)
├── Dockerfile
└── .dockerignore
```

### Dual-Layer Design

| Layer | Path | Mutable? | Role |
|-------|------|----------|------|
| **Base-OS** | `base_os/os_kernel.py` → compiled to `kernel` binary | No | Spawns agent as subprocess, monitors exit codes, handles upgrades and crash recovery |
| **Evo Agent** | `evo_agent_active/` | Yes | The self-modifying agent itself — code that can be rewritten by the LLM |

**Immutable Kernel Binary:** Compile Base-OS once with `bash build_kernel.sh` to produce a standalone `./kernel` binary. The binary cannot be read or modified by text editors or the LLM, ensuring the watchdog layer remains tamper-proof.

## Evolution Protocol

Every self-modification follows this 8-step protocol:

```
Evo Agent                    Base-OS                  Filesystem
  │                             │                         │
  │ 1. Clone code to staging   │                         │  staging_area/
  │ 2. Syntax check (py_compile)│                         │
  │ 3. Isolation process test  │                         │
  │ 4. Save state              │                         │  .evo_state.json
  │                             │                         │
  │── exit(42) ────────────────→│                         │
  │                             │ 5. Backup current code  │  history_versions/v{version}/
  │                             │ 6. Deploy staged code   │  evo_agent_active/
  │                             │ 7. Restart agent        │
  │←────────────────────────────│                         │
  │ 8. load_state()             │                         │
```

### Exit Codes

| Exit Code | Meaning | Base-OS Action |
|-----------|---------|----------------|
| 0 | Normal shutdown | Break the supervision loop |
| 42 | Upgrade request | Backup → swap staged code → restart |
| Any other non-zero | Crash | Record timestamp; rollback if ≥3 crashes in 10 min |

## Quick Start

### 1. Configure LLM

Create `.env` at project root (or export environment variables):

```bash
# .env
EVO_LLM_API_BASE=https://api.deepseek.com
EVO_LLM_API_KEY=sk-your-api-key
EVO_LLM_MODEL=deepseek-chat
```

Without a key the agent runs in **echo mode** (echoes input back) — useful for testing lifecycle.

### 2. Compile Base-OS Kernel (recommended)

Compile the watchdog layer into an immutable binary:

```bash
bash build_kernel.sh     # requires pyinstaller (pip install pyinstaller)
./kernel                 # start the system
```

The `kernel` binary is now a black box — no text editor or LLM can modify it.

### 3. Run the System

```bash
# Recommended: compiled binary
./kernel

# Alternative: Python source (for development)
python base_os/os_kernel.py

# Direct agent only (bypasses Base-OS watchdog)
python evo_agent_active/main.py
```

### Docker

```bash
docker build -t evo-agent .
docker run -it \
    -e EVO_LLM_API_KEY=sk-your-key \
    -e EVO_LLM_API_BASE=https://api.deepseek.com \
    -e EVO_LLM_MODEL=deepseek-chat \
    evo-agent
```

## LLM Configuration

Three configuration methods, in order of priority: **CLI arguments > environment variables > defaults**.

| CLI Argument | Environment Variable | Default | Description |
|-------------|---------------------|---------|-------------|
| `--llm-url` | `EVO_LLM_API_BASE` | `https://api.openai.com` | API base URL (OpenAI-compatible) |
| `--llm-key` | `EVO_LLM_API_KEY` | `""` | API key. When unset, agent runs in **echo mode** |
| `--llm-model` | `EVO_LLM_MODEL` | `gpt-4o` | Model name |

**`.env` autoloading:** Both `os_kernel.py` and `main.py` automatically load `PROJECT_ROOT/.env` on startup using `os.environ.setdefault` (existing env vars take precedence). No external library required.

The LLM client (`llm.py`) uses only `urllib` from the Python standard library — no third-party SDKs required. Compatible with any OpenAI-format API (OpenAI, DeepSeek, vLLM, Ollama, etc.).

## Core Mechanisms

### State Persistence

Before `sys.exit(42)`, the agent serializes its entire state to `.evo_state.json`:

- **Conversation history** (user/assistant/system turns with timestamps)
- **Long-term facts** (deduplicated knowledge store)
- **Current task** (active long-running task)
- **Extra metadata** (upgrade target file, etc.)

On startup, `EvoAgent.__init__()` calls `load_state()` to restore all context. The user experiences no interruption across restarts.

| File | Purpose |
|------|---------|
| `.evo_state.json` | Agent state (written by agent) |
| `.evo_recovery_message.json` | Crash recovery context (written by Base-OS) |

### Death Spiral Protection

Base-OS maintains a timestamped crash log. If the agent crashes **≥3 times within 10 minutes**:

1. Base-OS identifies the latest backup in `history_versions/`
2. **Overwrites** `evo_agent_active/` with the backed-up code
3. Injects a recovery message into `.evo_recovery_message.json`:
   > *"Your last code caused a fatal crash (exit code X). The system has been rolled back from version Y. Analyze and fix the issue before attempting another upgrade."*
4. On next startup, `EvoAgent.__init__()` detects the recovery message, injects it into conversation history, and deletes the file

**Configurable thresholds** in `os_kernel.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `CRASH_WINDOW_SECONDS` | `600` | Observation window (10 minutes) |
| `MAX_CRASHES` | `3` | Crashes threshold within the window |

### Self-Testing

Before any upgrade is applied, two-stage testing runs in isolation:

**Stage 1 — Syntax Check:**
All `.py` files in the staging area are validated with `python -m py_compile`. Any syntax error rejects the upgrade.

**Stage 2 — Isolation Process Test:**
The staging `main.py` is launched as a subprocess. A test prompt (`{"action":"ping"}`) is sent to stdin. The test validates:
- Process exits within 10 seconds (catches infinite loops)
- Process returns exit code 0 or 42
- stdout contains the expected marker `[Evo Agent]`

Only when both stages pass does the agent proceed to `sys.exit(42)`.

### ReAct Reasoning Loop

`reasoning.py` implements the ReAct (Reason + Act) pattern:

1. Append user input to conversation history
2. Send full history to LLM
3. Parse response for `Thought:` and `Action:` tags
4. Execute the tool via `SkillRegistry` and collect observation
5. Append observation to history, repeat (max 10 iterations)
6. Return final answer when no `Action:` tag is present

The `evaluate_and_rewrite_core` tool is pre-registered, allowing the LLM to trigger self-modification through the ReAct loop.

### Mandatory Interfaces

When the LLM rewrites core code, these interfaces **must be preserved**. Deleting any of them prevents the system from booting. This constraint is declared in the system prompt (`system_prompt.py`).

| Interface | File | Requirement |
|-----------|------|-------------|
| `EvoAgent.__init__()` | main.py | Must call `load_state()` |
| `EvoAgent.run()` | main.py | Main loop entry point |
| `EvoAgent.evaluate_and_rewrite_core()` | main.py | Evolution protocol entry point |
| `save_state()` | memory.py | State serialization |
| `load_state()` | memory.py | State deserialization |
| `load_recovery_message()` | memory.py | Check for rollback recovery message |

## Built-in Skills

| Skill | Signature | Description |
|-------|-----------|-------------|
| `read_file` | `read_file(path: str) -> str` | Read file contents |
| `write_file` | `write_file({"path": ..., "content": ...}) -> str` | Write content to file (auto-creates parent dirs) |
| `run_command` | `run_command(cmd: str) -> str` | Execute shell command with 30s timeout |

Register additional skills via `SkillRegistry.register()`.

## Running Tests

```bash
python test_e2e.py
```

Covers: state persistence, recovery message handling, syntax checks (pass/fail), isolation process test, crash counter, and staging area integrity.

## Safety Warnings

- This agent can **rewrite its own source code** — analogous to rebuilding an engine mid-flight
- The system prompt declares architectural constraints and mandatory interfaces, but LLMs are not guaranteed to comply
- The death spiral rollback mechanism provides a last-resort safety net, but it is not foolproof
- Run in a sandbox or container in any environment where side effects matter
- **Compile Base-OS to binary** (`bash build_kernel.sh`) to prevent the LLM from tampering with the watchdog layer
- The `kernel` binary is write-protected by design: even if the agent goes rogue, the supervisor cannot be modified
