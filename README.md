# JARVIS — Advanced Personal AI Computer Assistant

> **Laptop-First • Local-First • Privacy-First • Security-First • Windows Edition**

JARVIS is a production-quality personal AI assistant built specifically for Windows laptops. It is engineered with strict safety guarantees: the AI model **never** directly executes arbitrary operating system commands or shell scripts. Instead, all operations must pass through a central, deterministic Security Manager, Tool Registry, and Permission Gate with single/double confirmation workflows.

---

## 1. Core Architectural Principles

* **Laptop-First & Local-First**: Runs directly on your Windows machine. Local AI (e.g. Ollama/Qwen), local SQLite database (WAL mode), local voice processing, and local file storage are always prioritized.
* **Privacy-First (Zero Trust)**: All permissions (`microphone`, `internet`, `files`, `screen`, `pc_control`, `automation`, `cloud_ai`, `web_access`) are **BLOCKED by default**. No capability can run without explicit user authorization.
* **Security-First Pipeline**:
  ```text
  User Command / AI Request
            │
            ▼
     Tool Registry (Approved Tools Only)
            │
            ▼
     Input Schema Validation (Strict Pydantic)
            │
            ▼
     Permission Check (Permission Manager)
            │
            ▼
     Policy Engine Check (Safe Mode, Offline Constraints, Emergency Stop)
            │
            ▼
     Risk Assessment & Confirmation (Single / Double Confirmation)
            │
            ▼
     Controlled Tool Execution
            │
            ▼
     Structured Audit Logging (JSON-lines + SQLite)
            │
            ▼
     Result Reported to User / AI Response
  ```
* **No Arbitrary Shell Execution**: Tools are pre-compiled Python modules with validated parameter schemas. The AI cannot synthesize and run ad-hoc command strings.
* **Deterministic Risk Levels**:
  * `LOW`: Read-only, safe diagnostics (auto-allowed if permission granted).
  * `MEDIUM`: Non-destructive state alterations.
  * `HIGH`: Disruptive actions (requires explicit single confirmation).
  * `CRITICAL`: Destructive actions (requires **double confirmation**).

---

## 2. Directory Structure

```text
jarvis/
├── main.py                     # Safe interactive CLI entrypoint & health status banner
├── config.py                   # Type-safe settings, Enums, and environment loader
├── requirements.txt            # Pinned dependencies
├── .env.example                # Example configuration schema
├── .env                        # Local configuration (never committed)
├── .gitignore                  # Git exclusions for secrets, venv, and databases
├── README.md                   # Complete system documentation
│
├── core/
│   ├── __init__.py
│   ├── assistant.py            # Central assistant orchestrator
│   └── command_router.py       # Deterministic command router & safe CLI parser
│
├── security/
│   ├── __init__.py
│   ├── permission_manager.py   # Zero-trust privacy manager (all blocked by default)
│   ├── confirmation_manager.py # Single & double confirmation coordinator
│   ├── policy_engine.py        # Deterministic security rules (Safe Mode, Emergency Stop, Offline)
│   ├── security_manager.py     # Central security gateway & execution pipeline
│   └── audit_logger.py         # Segregated logging & secret-sanitizing audit recorder
│
├── memory/
│   ├── __init__.py
│   └── database.py             # SQLite WAL-mode persistence (permissions, audit, memories)
│
├── tools/
│   ├── __init__.py
│   ├── base_tool.py            # Abstract BaseTool, ToolResult, and schema exporter
│   ├── registry.py             # Central approved Tool Registry
│   └── system_control.py       # Safe read-only system diagnostic tools (Phase 1)
│
├── ai/                         # Stubs ready for Phase 4 (Local + OpenRouter providers)
├── voice/                      # Stubs ready for Phase 3 (Wake word "Jzt Jarvis", STT, TTS)
├── automation/                 # Stubs ready for Phase 8 (Scheduler & workflows)
├── vision/                     # Stubs ready for Phase 9 (Screen analysis - opt-in only)
│
├── tests/
│   ├── __init__.py
│   ├── test_permissions.py     # Tests for zero-trust defaults, grants, and revocations
│   ├── test_security.py        # Tests for policy engine, risk confirmations, and safe mode
│   ├── test_tools.py           # Tests for registry, schema export, and tool executions
│   ├── test_memory.py          # Tests for database tables, memories CRUD, and audit persistence
│   └── test_router.py          # Tests for CLI command router and emergency stop
│
└── data/                       # Local runtime data (ignored in Git)
    ├── jarvis.db               # SQLite database
    └── logs/
        ├── app.log             # Application events
        ├── error.log           # Exceptions and warnings
        ├── security.log        # Security events & permission denials
        └── audit.log           # Immutable JSON-lines audit trail
```

---

## 3. Installation & Quick Start

### 1. Requirements
* Windows 10/11
* Python 3.10+ (tested on Python 3.13)

### 2. Environment Setup
Create a virtual environment and install the required dependencies:
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` (already done by default):
```powershell
cp .env.example .env
```
Key settings in `.env`:
* `JARVIS_MODE=offline` (Options: `offline`, `hybrid`, `online`)
* `SAFE_MODE=true` (Prohibits HIGH/CRITICAL actions)
* `AI_PROVIDER=local`
* `LOCAL_MODEL_ENDPOINT=http://127.0.0.1:11434`
* `LOCAL_MODEL_NAME=qwen2.5:7b`

### 4. Run JARVIS Health Status Check
To view the full diagnostic report without entering the interactive CLI:
```powershell
python main.py --status
```

### 5. Launch the Safe Interactive CLI
```powershell
python main.py
```

---

## 4. Safe Interactive CLI Commands

Inside the JARVIS CLI, you can control the assistant using deterministic administrative commands:

| Command | Description |
| :--- | :--- |
| `status` | Displays the comprehensive diagnostic status table of all subsystems |
| `permissions` | Lists all 8 permissions and their current state (`ALLOWED` or `BLOCKED`) |
| `allow <permission>` | Grants an explicit permission (e.g. `allow pc_control`, `allow files`, `allow microphone`) |
| `block <permission>` | Revokes an explicit permission (e.g. `block microphone`) |
| `block all` | Instantly revokes and locks **all** permissions |
| `open <app\|folder>` | Safely launches approved app (`open Chrome`, `open Notepad`) or folder (`open Downloads`) |
| `find <pattern>` | Safely searches user folders (`find Python files`, `find *.pdf`) |
| `voice status` | Shows voice state machine, listening loop status, wake phrase, and audio providers |
| `start listening` | Engages the background voice listener loop (requires microphone permission) |
| `stop listening` | Disengages voice listener loop, returning JARVIS to SLEEPING state |
| `voice simulate <speech>` | Simulates voice turn with wake phrase (e.g. `voice simulate Jzt Jarvis open Downloads`) |
| `voice say <text>` | Speaks text through local Windows SAPI5 offline TTS engine |
| `wake phrase <phrase>` | Configures a custom wake phrase dynamically |
| `mode <offline\|hybrid\|online>` | Switches operating mode (offline strictly blocks all network tools) |
| `safe mode <on\|off>` | Toggles Safe Mode (`on` blocks HIGH & CRITICAL tools) |
| `emergency stop` | Instantly engages Emergency Stop, locking all tool execution |
| `reset emergency stop` | Disengages Emergency Stop after verified recovery |
| `tools` | Lists all 11 approved tools with their risk level and required permissions |
| `run <tool> [json_args]` | Safely dispatches a registered tool through the security pipeline |
| `audit [limit]` | Displays recent immutable audit records from the audit trail |
| `help` | Shows the command reference |
| `exit` / `quit` | Cleanly shuts down the assistant and releases resources |

---

## 5. Automated Test Suite

A complete test suite covers all security policies, permission handling, database integrity, schema validation, tool routing, and voice interaction:

```powershell
.venv\Scripts\pytest.exe -v
```

**Test Coverage Highlights (44 Automated Tests):**
* **Permission Tests**: Zero-trust default blocked state, explicit grants, explicit revocations, `block_all` lockdown, rejection of invalid permission names.
* **Security & Policy Tests**: Rejection of unauthorized/unregistered tools, schema validation failure handling, Safe Mode blocking HIGH/CRITICAL tools, Emergency Stop lifecycle, offline network enforcement, single confirmation for HIGH risk, double confirmation for CRITICAL risk.
* **Phase 2 Safe PC Tools Tests**: Application launcher allowlist enforcement, unknown application rejection, folder launcher (Desktop, Documents, Downloads), system location protections (`C:\Windows`, `C:\Program Files`), safe non-destructive file operations (create folder, create text file, rename file, copy file, move file), file search within user roots.
* **Phase 3 Voice Interaction Tests**: Wake phrase detection and phonetic variants ("Jzt Jarvis", "Just Jarvis", "Hey Jarvis"), dynamic wake phrase update, microphone permission denial/approval, voice state transitions (`SLEEPING` -> `LISTENING` -> `PROCESSING` -> `SPEAKING` -> `SLEEPING`), voice tool execution of Phase 2 tools, listening timeout handling, unapproved app rejection via voice, TTS failure recovery, CLI voice commands (`voice status`, `start listening`, `stop listening`, `voice simulate`).
* **Memory & Database Tests**: Schema initialization, WAL mode, user preferences, memory CRUD (filtering by approved/category), audit log persistence.
* **Router Tests**: Interactive command routing, argument parsing, error trapping, shortcut commands (`open`, `find`).

---

## 6. Development Roadmap

* [x] **Phase 1 — Foundation**: Modular structure, Settings, SQLite WAL database, Zero-trust Privacy Manager, Security Manager, Policy Engine, Confirmation Manager, Tool Registry, Base Tool, Audit Logging, Safe CLI, Automated Tests.
* [x] **Phase 2 — Safe PC Tools**: Allowlist-based Windows application launcher, standard folder launcher (Desktop/Downloads/Documents), safe file searching, non-destructive file operations (create folder, create text file, rename, copy, move), hardware diagnostics (CPU, RAM, disk, battery).
* [x] **Phase 3 — Voice**: Wake word engine ("Jzt Jarvis"), local offline STT, local Windows SAPI5 TTS, voice state machine (`SLEEPING`, `LISTENING`, `PROCESSING`, `SPEAKING`, `ERROR`), listening/sleep states, command timeouts, noise handling, zero cloud audio streaming.
* [ ] **Phase 4 — AI Brain**: AI provider abstraction (Local Ollama / OpenRouter), structured function calling via Tool Registry, intent parsing.
* [ ] **Phase 5 — Memory**: Long-term memory store, conversation history, user preferences.
* [ ] **Phase 6 — Advanced PC Control**: Lock PC, restart/shutdown with double confirmation.
* [ ] **Phase 7 — Web + Hybrid AI**: Optional internet capabilities, web search, online information retrieval.
* [ ] **Phase 8 — Automation**: Scheduled tasks, reminders, multi-step workflows.
* [ ] **Phase 9 — Vision**: Opt-in screen capture and understanding.
* [ ] **Phase 10 — Advanced JARVIS**: Advanced planning, tool chaining, desktop UI.
