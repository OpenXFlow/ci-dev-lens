# ==========================================
# Agent-CI-Lens: Universal Control Panel (v 5.2)
# ==========================================
.PHONY: help boot validate index lint lint-fix test test-kernel test-all coverage pipeline mock status clean purge env-init

# ==========================================
# PREMENNÉ (Updated for agent_* structure)
# ==========================================
PYTHON       := uv run python
PYTEST       := uv run pytest
RUFF         := uv run ruff
MYPY         := uv run mypy

# Nové cesty
CORE         := agent_core/
SRC          := src/
CTX          := agent_context/
TESTS_APP    := tests/
TESTS_AGENT  := agent_tests/
CACHE        := .claude/cache/
SKILLS       := .claude/skills/
SESSION_FILE := agent_context/SESSION.md

# Načítanie .env
ifneq ("$(wildcard .env)","")
	include .env
	export $(shell sed 's/=.*//' .env)
endif

# ==========================================
# HELP
# ==========================================
help:
	@echo "🤖 Agent-CI-Lens (v5.2) Commands:"
	@echo "  Core:"
	@echo "    make boot        - Full initialization"
	@echo "    make pipeline    - Start AI Orchestrator"
	@echo "    make mock        - Start AI Orchestrator (Simulation)"
	@echo "    make status      - Show HALT and Session status"
	@echo "    make clean       - Reset session (Agent section only)"
	@echo "  Quality & Testing:"
	@echo "    make lint        - Check code style & types"
	@echo "    make lint-fix    - Auto-fix code style"
	@echo "    make test        - Run application tests"
	@echo "    make test-kernel - Run framework tests"
	@echo "    make validate    - Verify system integrity"
	@echo "  Maintenance:"
	@echo "    make index       - Update codebase map"
	@echo "    make purge       - Clear all caches"
# ==========================================
# BOOT SEQUENCE (Volané z devcontainer.json)
# ==========================================
boot: env-init
	@echo "🚀 Booting Agent-CI-Lens..."
	uv sync --all-groups
	@$(MAKE) validate
	@$(MAKE) index
	@echo "✅ Boot complete."

env-init:
	@if [ ! -f .env ]; then cp .env.example .env; fi

# ==========================================
# CORE TASKS
# ==========================================
validate:
	@echo "🛡️  Validating Integrity..."
	@$(PYTHON) $(CORE)validator.py

index:
	@echo "📚 Indexing Codebase..."
	@$(PYTHON) $(CORE)indexer.py

# ==========================================
# QUALITY & TESTS
# ==========================================
lint:
	@$(RUFF) check $(SRC)
	@$(RUFF) format --check $(SRC)
	@$(MYPY) $(SRC)

lint-fix:
	@$(RUFF) check --fix $(SRC)
	@$(RUFF) format $(SRC)

test:
	@echo "🧪 App Tests..."
	@$(PYTEST) $(TESTS_APP)

test-kernel:
	@echo "🛠️  Agent Core Tests..."
	@$(PYTEST) $(TESTS_AGENT)

test-all: test-kernel test

# ==========================================
# PIPELINE
# ==========================================
pipeline:
	@echo "🚀 Running Pipeline..."
	@$(PYTHON) $(CORE)router.py --pipeline

mock:
	@echo "🧪 Running Mock Pipeline..."
	@$(PYTHON) $(CORE)router.py --pipeline --mock

# ==========================================
# STATUS & MAINTENANCE
# ==========================================
status:
	@echo "📊 Status Report:"
	@if [ -f $(CACHE)HALT.flag ]; then echo "🚨 SYSTEM HALTED"; cat $(CACHE)HALT.flag; fi
	@echo "State in $(SESSION_FILE):"
	@grep -A1 "### \[STATE\]" $(SESSION_FILE) | tail -1 || echo "Unknown"

clean:
	@echo "🧹 Cleaning Session..."
	rm -f $(CACHE)HALT.flag
	@if [ -f $(SESSION_FILE) ]; then \
		sed -n '1,/## \[AGENT_SECTION\]/p' $(SESSION_FILE) > $(SESSION_FILE).tmp; \
		echo "### [STATE]" >> $(SESSION_FILE).tmp; \
		echo "IDLE" >> $(SESSION_FILE).tmp; \
		echo "" >> $(SESSION_FILE).tmp; \
		echo "### [ACTION_LOG]" >> $(SESSION_FILE).tmp; \
		mv $(SESSION_FILE).tmp $(SESSION_FILE); \
	else \
		echo "Creating new session file..."; \
		printf "# Agent-CI-Lens SESSION\n\n## [USER_SECTION]\n### [CONTEXT]\n\n### [WORKSPACE]\n\n---\n\n## [AGENT_SECTION]\n### [STATE]\nIDLE\n\n### [ACTION_LOG]\n" > $(SESSION_FILE); \
	fi
	@$(MAKE) purge

purge:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true