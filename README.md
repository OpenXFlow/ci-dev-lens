# 🚀 CI-DEV-Lens: Autonomous AI-Powered CI/CD Orchestrator for Python

![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Ruff](https://img.shields.io/badge/Ruff-passing-brightgreen)

<p align="center">
  <a href="https://github.com/OpenXFlow/ci-dev-lens">
    <img src="docs/assets/Agent-CI-Lens2.png" alt="CI-DEV-Lens Banner" width="900">
  </a>
</p>

<p align="center">
  <strong>You write a one-line goal. The swarm writes the code, tests it, lints it, and opens a PR. You just review.</strong>
  <br><br>
  <em>Precision Vision. Autonomous Execution. Zero-Tolerance Quality.</em>
</p>

CI-DEV-Lens (Model 6.1) is not just another AI chat — it is a **Managed State Machine**. By employing a Hypervisor Pattern and Docker-based isolation, it coordinates specialized AI personas that physically interact with a sandboxed filesystem.

---

## 🔄 How It Works

```
You write a GOAL  →  Queen plans  →  Developer codes  →  Pedant lints  →  Auditor reviews  →  PR opened
```

1. **Queen** analyzes your codebase and decomposes the GOAL into atomic tasks
2. **Developer** implements code and writes tests (TDD)
3. **Pedant** enforces Ruff + Mypy quality gates with auto-fix
4. **Auditor** performs final security and quality review
5. **Git Manager** creates a feature branch and opens a PR *(optional, CI_MODE=github)*

If any stage fails, the system **automatically self-corrects** — routing raw error logs back to the responsible agent.

---

## ✨ Key Capabilities

- 🧠 **Sequential Multi-Stage Pipeline:** Strictly ordered relay race: `STRATEGY → EXECUTING → LINTING → TESTING → VERIFYING → VCS_DELIVERY`
- 🔄 **Autonomous Feedback Loops:** Quality gate failures are automatically routed back for self-correction
- 🧠 **ACMI Learning Memory:** RAG-powered Knowledge Bank that gets smarter with every task
- ☁️ **Cloud-Native Integration (GHA v2):** Automated PR creation and GitHub Actions status polling
- 🛡️ **Bimetric Isolation:** `[USER_SECTION]` and `[AGENT_SECTION]` are physically separated — the AI never overwrites your instructions
- ⚡ **API Resilience:** Native key rotation and automatic provider failover (Groq → Mistral)
- 📉 **Smart Context Compression:** Token-efficient log pruning without losing critical project memory
- 📦 **Hermetic Sandbox:** Zero impact on your host system

---

## 🧠 ACMI: The Learning Memory Engine

Unlike static AI tools, CI-DEV-Lens **gets smarter over time**.

| Feature | Description |
|---------|-------------|
| **Knowledge Bank** | 100+ expert rules injected into agent prompts via SQLite FTS5 RAG |
| **Reflections** | Post-mortem analysis automatically stored after each completed goal |
| **Mandatory Rules** | Critical engineering laws always injected — regardless of task context |
| **Portable Wisdom** | Export your `memory.db` and bring your expertise to a new project |

```bash
# Add your own expert rules
make knowledge-add CATEGORY="implementation" CONTENT="Always use pathlib over os.path"

# Export knowledge to a new project
make knowledge-export FILE="my_expertise.json"
```
---

## 🛠️ Tech Stack

**Core Engine:**
- **Python 3.12** — Modern type safety and performance
- **UV Manager** — Deterministic, lightning-fast dependency management
- **Pydantic V2** — Strict configuration and agent registry validation
- **SQLite + FTS5** — Zero-dependency RAG memory engine

**Quality Gates:**
- **Ruff (Tier 1)** — Rust-powered mechanical linting and formatting
- **Mypy (Tier 2)** — Strict logical type integrity enforcement
- **Pytest** — Unified testing for both the Kernel and the Application

**Intelligence Providers** *(any OpenAI-compatible API)*:
- **Groq API** — Fast Llama 3.3 for implementation (free tier)
- **Mistral API** — Mistral Large for architecture and auditing (free tier)
- **Ollama** — Local LLM support for full privacy and no rate limits

---

## 🚀 Quick Start

**1. Clone the Repository:**
```bash
git clone https://github.com/OpenXFlow/ci-dev-lens.git
cd ci-dev-lens
```

**2. Wake the Swarm:**
```bash
make boot
```

**3. Configure your API keys:**
```env
# .env
GROQ_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
```

**4. Generate a structured GOAL:**
```bash
make spec TASK='Implement a temperature converter with Celsius, Fahrenheit and Kelvin support'
```
Paste the output into `agent_context/TASKS.md`

**5. Engage the Flow:**
```bash
make pipeline
```

---

## 💡 Real-World Example

Paste this into `agent_context/TASKS.md` to see the swarm in action:

```markdown
## [USER_QUEUE]
- [ ] GOAL-001: Temperature Converter
  |-- INTENT: Implement a TemperatureConverter class that converts
      between Celsius, Fahrenheit and Kelvin with input validation
  |-- CONSTRAINTS: No external libs. Files: src/converter.py,
      tests/test_converter.py. Google-style docstrings. Type hints.
  |-- METRIC: coverage>=95 complexity<=5 mypy=strict noqa=0
```

Then run `make pipeline` and watch the swarm work.

---

## 📚 Documentation

| Resource | Description |
|:---------|:------------|
| [⚙️ Architecture](docs/ci_architecture/flow_diagrams_operations_map.md) | Visual architectural map |
| [🕹️ Terminal Interface](docs/TERMINAL_CMD.md) | Full guide to `make` commands |
| [⚙️ Configuration](docs/CONFIGURATION.md) | Tuning `agent_orchestrator.json` |
| [🖥️ User Interface](docs/USER_INTERFACE.md) | Bimetric Markdown communication |
| [🤖 Agent Personas](docs/AGENT_PERSONAS.md) | Queen, Developer, Pedant, Auditor |
| [🏗️ Development Guide](docs/DEVELOPMENT_GUIDE.md) | Adding Skills and extending the Kernel |
| [🏛️ Framework Architecture](docs/ARCHITECTURE.md) | State Machine and Hypervisor deep dive |

---

## 📊 How CI-DEV-Lens Compares (Current State & Roadmap)

> CI-DEV-Lens is an actively developed open-source project.
> Some features marked ⏳ are on our roadmap.

### Open Source

| Feature | CI-DEV-Lens | Aider | Continue.dev | OpenHands | SWE-Agent |
|---------|:-----------:|:-----:|:------------:|:---------:|:---------:|
| Persistent memory | ✅ SQLite RAG | ✅ Repo Map | ✅ Vector DB | ✅ Long-term | ❌ |
| Learns from mistakes | ✅ Reflections | ✅ Lint/Test | ⚠️ Custom | ✅ Agentic | ❌ |
| Custom rules | ✅ Knowledge Bank | ✅ Conventions | ✅ Config | ✅ Rules | ❌ |
| Multi-agent pipeline | ✅ 4 agents | ❌ | ❌ | ✅ | ✅ |
| Built-in CI/CD | ✅ GHA native | ✅ Git-driven | ⚠️ Limited | ✅ Agentic | ❌ |
| Two-tier quality gates | ✅ Ruff+Mypy | ❌ | ❌ | ❌ | ❌ |
| Vector search | ⏳ Roadmap M8 | ❌ | ✅ | ⚠️ | ❌ |
| MCP integration | ⏳ Roadmap M7 | ❌ | ✅ | ⚠️ | ❌ |
| Local LLM | ✅ Ollama | ✅ | ✅ | ✅ | ✅ |
| Free tier | ✅ Groq+Mistral | ✅ DIY | ✅ DIY | ⚠️ Heavy | ✅ |
| Open source | ✅ MIT | ✅ Apache 2.0 | ✅ Apache 2.0 | ✅ MIT | ✅ MIT |
| Price/month | **$0** | **$0** | **$0** | **$0** | **$0** |

### Commercial

| Feature | CI-DEV-Lens | Devin 2.0 | Claude Code | Claude Cowork | Cursor | GH Copilot |
|---------|:-----------:|:---------:|:-----------:|:-------------:|:------:|:----------:|
| Persistent memory | ✅ SQLite RAG | ✅ Wiki+Search | ✅ Auto Memory | ✅ Knowledge | ⚠️ Indexing | ❌ |
| Learns from mistakes | ✅ Reflections | ✅ Feedback | ✅ Auto Memory | ⚠️ Planned | ❌ | ❌ |
| Custom rules | ✅ Knowledge Bank | ⚠️ Playbooks | ✅ CLAUDE.md | ⚠️ Planned | ✅ .cursorrules | ❌ |
| Multi-agent pipeline | ✅ 4 agents | ✅ Parallel | ✅ Subagents | ✅ Tasks | ❌ | ❌ |
| Built-in CI/CD | ✅ GHA native | ✅ Sandbox | ⚠️ Headless | ❌ | ❌ | ⚠️ Actions |
| Two-tier quality gates | ✅ Ruff+Mypy | ❌ | ❌ | ❌ | ❌ | ❌ |
| Vector search | ⏳ Roadmap M8 | ✅ | ⚠️ | ⚠️ | ✅ | ❌ |
| MCP integration | ⏳ Roadmap M7 | ❌ | ✅ | ✅ | ❌ | ❌ |
| Local LLM | ✅ Ollama | ❌ Cloud only | ❌ | ❌ | ❌ | ❌ |
| Free tier | ✅ | ❌ | ❌ | ❌ | ✅ Limited | ✅ Limited |
| Open source | ✅ MIT | ❌ | ❌ | ❌ | ❌ | ❌ |
| Price/month | **$0** | $20–500 | $5–150* | $20+ | $0–60 | $10–25 |

> ✅ Full support &nbsp; ⚠️ Partial &nbsp; ❌ Not supported &nbsp; ⏳ On roadmap
>
> *Claude Code — consumption-based pricing, varies by usage

---

## Contributing

Contributions to the Core Hypervisor and Agent Skill-set are welcome. See the [Development Guide](docs/DEVELOPMENT_GUIDE.md).

## License

MIT License — see [LICENSE.md](LICENSE.md)

<p align="center">
  <a href="https://github.com/OpenXFlow/ci-dev-lens">
    <img src="docs/assets/Agent-CI-Lens.png" alt="CI-DEV-Lens Banner" width="900">
  </a>
</p>
