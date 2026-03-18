# ==========================================
# Agent-CI-Lens: Universal Control Panel (v 5.21)
# Milestone 5: Deterministic Mandatory Rules
# Milestone 6: Token Telemetry & Data Lifecycle
# ==========================================
.PHONY: help boot validate index lint lint-fix test test-kernel test-all coverage pipeline mock status clean purge env-init spec --hard knowledge-add knowledge-import-csv knowledge-export knowledge-import knowledge-export-debug tokens-last tokens-today tokens-total tokens tokens-remove-legacy tokens-remove-history tokens-reset

# ==========================================
# ENV
# ==========================================
PYTHON       := uv run python
PYTEST       := uv run pytest
RUFF         := uv run ruff
MYPY         := uv run mypy

# Paths
CORE         := agent_core/
SRC          := src/
CTX          := agent_context/
TESTS_APP    := tests/
TESTS_AGENT  := agent_tests/
CACHE        := .claude/cache/
SKILLS       := .claude/skills/
SESSION_FILE := agent_context/SESSION.md
DB_FILE      := .claude/cache/memory.db

# Load environment variables
ifneq ("$(wildcard .env)","")
	include .env
	export $(shell sed 's/=.*//' .env)
endif

# Helper for resilient table formatting
FORMAT_TABLE := { which column >/dev/null && column -t -s '|' || cat; }

# Dummy target for hard purge argument
--hard:
	@:

# ==========================================
# HELP
# ==========================================
help:
	@echo "🤖 Agent-CI-Lens Commands:"
	@echo "  Core:"
	@echo "    make boot        - Full initialization"
	@echo "    make pipeline    - Start AI Orchestrator"
	@echo "    make mock        - Start AI Orchestrator (Simulation)"
	@echo "    make spec TASK=\"desc\" - Generate structured GOAL from idea"
	@echo "    make status      - Show HALT, Session and Memory Engine status with Token Telemetry"
	@echo "    make clean       - Reset session (Agent section only)"
	@echo "  Quality & Testing:"
	@echo "    make lint        - Check code style & types (src & tests)"
	@echo "    make lint-fix    - Auto-fix code style (src & tests)"
	@echo "    make test        - Run application tests"
	@echo "    make test-kernel - Run framework tests"
	@echo "    make validate    - Verify system integrity"
	@echo "  Knowledge Base (ACMI):"
	@echo "    make knowledge-add           - Add expert entry (req: CATEGORY, CONTENT) [opt: MANDATORY=true]"
	@echo "    make knowledge-import-csv    - Bulk ingest from CSV (req: FILE)"
	@echo "    make knowledge-import        - Import knowledge from JSON backup (req: FILE)"
	@echo "    make knowledge-export        - Export knowledge to JSON backup (req: FILE)"
	@echo "    make knowledge-export-debug  - Export full DB table for debugging (req: FILE)"
	@echo "  Maintenance:"
	@echo "    make index       - Update codebase map"
	@echo "    make purge       - Clear temporary caches (Runs DB VACUUM)"
	@echo "    make purge --hard- Completely delete the Knowledge Bank & Memory DB"
	@echo "  Telemetria (Token Usage):"
	@echo "    make tokens-last - Usage for the most recent GOAL"
	@echo "    make tokens-today- Usage in the last 24 hours"
	@echo "    make tokens-total- Cumulative project usage"
	@echo "    make tokens GOAL=001 - Filter by specific Goal ID"
	@echo "    make tokens-remove-legacy  - Remove records with missing provider"
	@echo "    make tokens-remove-history - Remove records older than 7 days"
	@echo "    make tokens-reset          - Clear ALL telemetry (Nukleárna možnosť)"

# ==========================================
# BOOT SEQUENCE
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

spec:
	@if [ -z '$(TASK)' ]; then \
		echo "❌ Error: TASK variable is required."; \
		echo "Usage: make spec TASK=\"Develop a persistent JSON logger\""; \
		exit 1; \
	fi
	@$(PYTHON) $(CORE)spec_gen.py --task '$(TASK)'

# ==========================================
# QUALITY & TESTS
# ==========================================
lint:
	@$(RUFF) check $(SRC) $(TESTS_APP)
	@$(RUFF) format --check $(SRC) $(TESTS_APP)
	@$(MYPY) $(SRC) $(TESTS_APP)

lint-fix:
	@$(RUFF) check --fix $(SRC) $(TESTS_APP)
	@$(RUFF) format $(SRC) $(TESTS_APP)

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
# TOKEN TELEMETRY (ACMI)
# ==========================================
tokens-last:
	@if [ ! -f $(DB_FILE) ]; then echo "❌ DB not found"; exit 1; fi
	@echo "🧠 Token Usage - Last Goal Context:"
	@sqlite3 $(DB_FILE) " \
		SELECT stage, provider, COUNT(*) as calls, SUM(tokens_used) as tokens, \
		SUM(tokens_prompt) as prompt, SUM(tokens_completion) as compl, \
		ROUND(AVG(duration_ms)/1000.0, 1) as avg_s \
		FROM execution_logs \
		WHERE task_id = (SELECT task_id FROM execution_logs WHERE tokens_used > 0 ORDER BY timestamp DESC LIMIT 1) \
		GROUP BY stage, provider ORDER BY tokens DESC; \
	" | (echo "Stage|Provider|Calls|Tokens|Prompt|Compl|Avg(s)" && cat) | $(FORMAT_TABLE)

tokens-today:
	@if [ ! -f $(DB_FILE) ]; then echo "❌ DB not found"; exit 1; fi
	@echo "🧠 Token Usage - Last 24h:"
	@sqlite3 $(DB_FILE) " \
		SELECT stage, provider, COUNT(*) as calls, SUM(tokens_used) as tokens, \
		SUM(tokens_prompt) as prompt, SUM(tokens_completion) as compl \
		FROM execution_logs \
		WHERE timestamp > datetime('now', '-1 day') AND tokens_used > 0 \
		GROUP BY stage, provider ORDER BY tokens DESC; \
	" | (echo "Stage|Provider|Calls|Tokens|Prompt|Compl" && cat) | $(FORMAT_TABLE)

tokens-total:
	@if [ ! -f $(DB_FILE) ]; then echo "❌ DB not found"; exit 1; fi
	@echo "🧠 Token Usage - All Time Project Totals:"
	@sqlite3 $(DB_FILE) " \
		SELECT provider, SUM(tokens_used) as tokens, COUNT(*) as calls, \
		SUM(tokens_prompt) as prompt, SUM(tokens_completion) as compl \
		FROM execution_logs \
		WHERE tokens_used > 0 \
		GROUP BY provider ORDER BY tokens DESC; \
	" | (echo "Provider|Total_Tokens|Calls|Prompt|Compl" && cat) | $(FORMAT_TABLE)

tokens:
	@if [ -z "$(GOAL)" ]; then echo "❌ Usage: make tokens GOAL=001"; exit 1; fi
	@echo "🧠 Token Usage - Goal $(GOAL):"
	@sqlite3 $(DB_FILE) " \
		SELECT stage, provider, COUNT(*) as calls, SUM(tokens_used) as tokens, \
		SUM(tokens_prompt) as prompt, SUM(tokens_completion) as compl \
		FROM execution_logs \
		WHERE task_id LIKE '%$(GOAL)%' AND tokens_used > 0 \
		GROUP BY stage, provider ORDER BY tokens DESC; \
	" | (echo "Stage|Provider|Calls|Tokens|Prompt|Compl" && cat) | $(FORMAT_TABLE)

tokens-remove-legacy:
	@if [ ! -f $(DB_FILE) ]; then echo "❌ DB not found"; exit 1; fi
	@sqlite3 $(DB_FILE) "DELETE FROM execution_logs WHERE provider = '' OR provider IS NULL;"
	@echo "✅ Legacy token records (empty provider) removed."

tokens-remove-history:
	@if [ ! -f $(DB_FILE) ]; then echo "❌ DB not found"; exit 1; fi
	@sqlite3 $(DB_FILE) "DELETE FROM execution_logs WHERE timestamp < datetime('now', '-7 days');"
	@echo "✅ Telemetry history older than 7 days removed."

tokens-reset:
	@if [ ! -f $(DB_FILE) ]; then echo "❌ DB not found"; exit 1; fi
	@echo "⚠️  WARNING: This will clear ALL token telemetry data."
	@read -p "Are you sure you want to proceed? [y/N] " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		sqlite3 $(DB_FILE) "DELETE FROM execution_logs;"; \
		echo "✅ Telemetry wiped."; \
	else \
		echo "❌ Operation cancelled."; \
	fi

# ==========================================
# KNOWLEDGE BASE (ACMI)
# ==========================================
knowledge-add:
	@if [ -z "$(CATEGORY)" ] || [ -z "$(CONTENT)" ]; then \
		echo "❌ Error: CATEGORY and CONTENT variables are required."; \
		exit 1; \
	fi
	@echo "🧠 Adding Knowledge to DB..."
	@$(PYTHON) -m agent_core.memory_engine knowledge-add \
		--category "$(CATEGORY)" \
		--content "$(CONTENT)" \
		$(if $(SUBCATEGORY),--subcategory "$(SUBCATEGORY)") \
		$(if $(TYPE),--type "$(TYPE)") \
		$(if $(TAGS),--tags "$(TAGS)") \
		$(if $(filter true,$(MANDATORY)),--mandatory)

knowledge-import-csv:
	@if [ -z "$(FILE)" ]; then echo "❌ Error: FILE variable is required."; exit 1; fi
	@$(PYTHON) -m agent_core.memory_engine knowledge-import-csv --file "$(FILE)"

knowledge-import:
	@if [ -z "$(FILE)" ]; then echo "❌ Error: FILE variable is required."; exit 1; fi
	@$(PYTHON) -m agent_core.memory_engine knowledge-import --input "$(FILE)"

knowledge-export:
	@if [ -z "$(FILE)" ]; then echo "❌ Error: FILE variable is required."; exit 1; fi
	@$(PYTHON) -m agent_core.memory_engine knowledge-export --output "$(FILE)"

knowledge-export-debug:
	@if [ -z "$(FILE)" ]; then echo "❌ Error: FILE variable is required."; exit 1; fi
	@$(PYTHON) -m agent_core.memory_engine knowledge-export-debug --output "$(FILE)"

# ==========================================
# STATUS & MAINTENANCE
# ==========================================
status:
	@echo "📊 Status Report:"
	@if [ -f $(CACHE)HALT.flag ]; then echo "🚨 SYSTEM HALTED"; cat $(CACHE)HALT.flag; fi
	@echo "State in $(SESSION_FILE):"
	@grep -A1 "### \[STATE\]" $(SESSION_FILE) | tail -1 || echo "Unknown"
	@if [ -f $(CORE)memory_engine.py ]; then \
		echo ""; \
		echo "🧠 Memory Engine Status:"; \
		$(PYTHON) -m agent_core.memory_engine health || true; \
	fi
	@if [ -f $(DB_FILE) ]; then \
		echo ""; \
		echo "🧠 Token Telemetry (Current Summary):"; \
		sqlite3 $(DB_FILE) " \
			SELECT \
				stage, \
				provider, \
				COUNT(*) as calls, \
				SUM(tokens_used) as total_tokens, \
				ROUND(AVG(duration_ms)/1000.0, 1) as avg_seconds \
			FROM execution_logs \
			WHERE tokens_used > 0 \
			GROUP BY stage, provider \
			ORDER BY total_tokens DESC; \
		" | (echo "Stage|Provider|Calls|Tokens|Avg(s)" && cat) | $(FORMAT_TABLE); \
	fi

clean:
	@echo "🧹 Cleaning Session..."
	rm -f $(CACHE)HALT.flag $(CACHE)AGENTS.md $(CACHE)agents-index.json
	@if [ -f $(SESSION_FILE) ]; then \
		sed -n '1,/## \[AGENT_SECTION\]/p' $(SESSION_FILE) > $(SESSION_FILE).tmp; \
		echo "### [STATE]" >> $(SESSION_FILE).tmp; \
		echo "IDLE" >> $(SESSION_FILE).tmp; \
		echo "" >> $(SESSION_FILE).tmp; \
		echo "### [FEEDBACK]" >> $(SESSION_FILE).tmp; \
		echo "" >> $(SESSION_FILE).tmp; \
		echo "### [ACTION_LOG]" >> $(SESSION_FILE).tmp; \
		mv $(SESSION_FILE).tmp $(SESSION_FILE); \
	else \
		echo "Creating new session file..."; \
		printf "# Agent-CI-Lens SESSION\n\n## [USER_SECTION]\n### [CONTEXT]\n\n### [WORKSPACE]\n\n---\n\n##[AGENT_SECTION]\n### [STATE]\nIDLE\n\n### [FEEDBACK]\n\n###[ACTION_LOG]\n" > $(SESSION_FILE); \
	fi
	@$(MAKE) purge WIPE=--wipe-ast

purge:
ifeq ($(filter --hard,$(MAKECMDGOALS)),--hard)
	@echo "💥 HARD PURGE: Deleting Knowledge Bank and Memory DB..."
	@rm -f $(CACHE)memory.db $(CACHE)memory.db-wal $(CACHE)memory.db-shm
else
	@echo "🧹 Standard Purge: Keeping Knowledge Bank, running maintenance..."
	@if [ -f $(CORE)memory_engine.py ]; then \
		$(PYTHON) -m agent_core.memory_engine maintenance $(WIPE) || true; \
	fi
endif
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true