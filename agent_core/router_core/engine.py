#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/engine.py
Hybrid Orchestration Engine (v 2.0.2).
Milestone 4: Added Post-Mortem REFLECTION state for ACMI Blueprint v3.2.
Updated with Agent execution logging for Objective Auditor (Milestone 3).
Surgical Patch: Bimetric Shield (Immutable User Section Merge).
Surgical Patch: Smart Task Merge for Pydantic QueenResponse.
Milestone 5 (v1.49.0): Central Dispatcher `_execute_stage` & TESTING Read-Only Lock.
Surgical Patch 1.49.1: State Leakage Fix (Targeted FEEDBACK cleanup).
Milestone 6 (v2.0.0): Token Telemetry integration & Dispatcher-driven architecture.
Surgical Patch 2.0.1: Enhanced Pipeline Logging (Include Goal/Task description).
Surgical Patch 2.0.2: Smart LINTING Feedback Accumulator (Ping-Pong Prevention).
"""

import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from .agent_actions import (
    AuditorResponse,
    DeveloperResponse,
    FileWrite,
    QueenResponse,
    SkillCall,
)
from .git_local import GitLocalManager
from .github_client import GitHubAPIClient
from .llm import APIClient, PromptBuilder
from .managers import HaltManager, SessionManager, TasksManager
from .models import ExecutionLogEntry, StageConfig
from .utils import (
    ROOT,
    load_agents_registry,
    load_env,
    load_orchestrator_config,
    log,
)

# Safe fallback import for standalone execution
try:
    from agent_core.memory_engine import MemoryEngine
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))
    from agent_core.memory_engine import MemoryEngine


# ==========================================
# REFLECTION SCHEMAS (Pydantic)
# ==========================================
class ReflectionItem(BaseModel):
    """Structured lesson learned from execution failures."""

    error_pattern: str = Field(description="Summary of the error pattern, mistake, or bug.")
    solution: str = Field(description="The correct approach, solution, or best practice.")
    tags: str = Field(description="Semicolon separated tags, e.g., 'python;pytest;syntax'")


class ReflectionResponse(BaseModel):
    """Response model for the Queen Post-Mortem analysis."""

    thought: str = Field(description="Post-mortem analysis thought process.")
    reflections: list[ReflectionItem] = Field(description="Extracted lessons learned.")


class Router:
    """Hybrid State Machine supporting both Structured and Legacy AI interactions."""

    RESPONSE_MODELS: ClassVar[dict[str, type[Any]]] = {
        "queen": QueenResponse,
        "auditor": AuditorResponse,
    }

    def __init__(self, mock: bool = False) -> None:
        self.env = load_env()
        self.orch_config = load_orchestrator_config()
        self.mock = mock or self.env.MOCK

        self.agent_registry = load_agents_registry()
        self.session = SessionManager()
        self.tasks = TasksManager()
        self.halt = HaltManager()

        self.api = APIClient(self.env, self.mock, self.orch_config)
        self.builder = PromptBuilder()
        self.git = GitLocalManager()

    def _apply_file_writes(self, writes: list[FileWrite], tid: str | None = None, state: str = "UNKNOWN") -> int:
        """Physically commits file changes to disk with security checks."""
        # SAFETY LOCK: Prevent writing code during TESTING stage
        if state == "TESTING":
            log("Write blocked: TESTING stage is strictly Read-Only for Developer.", "ERROR", tid)
            return 0

        count = 0
        protected = [
            "agent_core/",
            "agent_tests/",
            ".claude/",
            ".agents/",
            "agent_context/SESSION.md",
        ]

        for w in writes:
            if any(w.path.startswith(p) for p in protected):
                log(f"Blocked write attempt to protected path: {w.path}", "WARN", tid)
                continue

            content = w.content
            if w.path == "agent_context/TASKS.md":
                # BIMETRIC SHIELD: Always reconstruct file using User Section from disk
                if self.tasks.path.exists():
                    disk_content = self.tasks.path.read_text(encoding="utf-8")
                    user_match = re.search(r"(?s)^(.*?)(?:\n---\n|\n## \[AGENT_PROGRESS\])", disk_content)
                    disk_user_section = user_match.group(1).strip() if user_match else disk_content.strip()

                    ai_agent_match = re.search(r"(?s)## \[AGENT_PROGRESS\](.*)", content)
                    if ai_agent_match:
                        ai_agent_section = ai_agent_match.group(1).strip()
                    else:
                        ai_agent_section = content.split("---")[-1].strip()

                    content = f"{disk_user_section}\n\n---\n\n## [AGENT_PROGRESS]\n{ai_agent_section}\n"
                    w.content = content

                existing_ids = self.tasks.get_all_task_ids()
                new_ids = set(re.findall(r"(?:TASK|GOAL)-([\w\-]+)", content))
                if existing_ids - new_ids:
                    log(f"History Violation: Queen tried to delete tasks/goals {existing_ids - new_ids}", "ERROR", tid)
                    continue

                if tid and not str(tid).startswith("GOAL-"):
                    pattern = re.compile(rf"-\s*\[\s*x\s*\]\s*TASK-{tid}\b", re.IGNORECASE)
                    if pattern.search(content):
                        content = pattern.sub(f"- [ ] TASK-{tid}", content)
                        w.content = content
                        log(f"Sanitized TASKS.md: Prevented premature task closure for TASK-{tid}", "WARN", tid)

            dest = ROOT / w.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            log(f"File written: {w.path}", "OK", tid)
            count += 1
        return count

    def _apply_skill_calls(
        self, calls: list[SkillCall], tid: str | None = None, stage: str = "UNKNOWN", attempt: int = 1
    ) -> list[str]:
        """Executes a batch of skills and returns their status tags."""
        results = []
        for c in calls:
            tag, out = self._run_skill_process(c.name, c.arguments, tid, stage, attempt)
            self.session.write_action_log(f"Skill {c.name} -> {tag}\nOutput: {out[:250]}...")
            results.append(tag)

            if "RESULT:SECRET_FOUND" in tag:
                self.halt.halt(f"Secret detected during skill {c.name}!", tid)
        return results

    def _run_skill_process(
        self, name: str, args: dict[str, str], tid: str | None = None, stage: str = "UNKNOWN", attempt: int = 1
    ) -> tuple[str, str]:
        """Low-level skill execution via subprocess with High-Fidelity execution logging."""
        s_map = {
            "testing-pro": ".claude/skills/testing-pro/scripts/verify.py",
            "quality-gate": ".claude/skills/quality-gate/scripts/check.sh",
            "security-guard": ".claude/skills/security-guard/scripts/scan.py",
            "context-compressor": ".claude/skills/context-compressor/scripts/summarize.py",
        }
        rel_path = s_map.get(name)
        if not rel_path:
            return "RESULT:ERROR", f"Skill {name} unknown"

        cmd = (
            ["uv", "run", "python", str(ROOT / rel_path)]
            if rel_path.endswith(".py")
            else ["bash", str(ROOT / rel_path)]
        )
        for k, v in args.items():
            if k != "action":
                cmd.extend([f"--{k}", v])

        log(f"Spawning subprocess for skill: {name}", "INFO", tid)

        start_time = time.perf_counter()
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
        except Exception as e:
            tag = f"RESULT:ERROR:{e}"
            output = str(e)
        else:
            output = f"{res.stdout}\n{res.stderr}"
            tag = next(
                (line.strip() for line in reversed(output.splitlines()) if "RESULT:" in line), "RESULT:COMPLETED"
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Secure DB write using Pydantic Validation (ACMI)
        if self.orch_config.memory_engine.enabled.value:
            try:
                log_entry = ExecutionLogEntry(
                    task_id=tid or "UNKNOWN",
                    stage=stage,
                    tool=name,
                    result=tag.replace("RESULT:", ""),
                    output=output,
                    duration_ms=duration_ms,
                    attempt=attempt,
                    provider="local_skill",
                )
                with MemoryEngine() as engine, engine.get_connection() as conn, conn:
                    conn.execute(
                        """
                        INSERT INTO execution_logs
                        (task_id, stage, tool, result, output, duration_ms, attempt, provider)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            log_entry.task_id,
                            log_entry.stage,
                            log_entry.tool,
                            log_entry.result,
                            log_entry.output,
                            log_entry.duration_ms,
                            log_entry.attempt,
                            log_entry.provider,
                        ),
                    )
            except Exception as db_e:
                log(f"Failed to record execution log to DB: {db_e}", "WARN", tid)

        return tag, output

    def _record_agent_execution(
        self,
        tid: str | None,
        stage: str,
        agent: str,
        result: str,
        output: str,
        dur_ms: int,
        attempt: int,
        provider: str = "",
        usage: dict[str, int] | None = None,
    ) -> None:
        """Helper to record agent execution and token usage into the memory engine."""
        if not self.orch_config.memory_engine.enabled.value:
            return
        try:
            u = usage or {"prompt": 0, "completion": 0, "total": 0}
            le = ExecutionLogEntry(
                task_id=tid or "UNKNOWN",
                stage=stage,
                tool=agent,
                result=result,
                output=output,
                duration_ms=dur_ms,
                attempt=attempt,
                provider=provider,
                tokens_prompt=u["prompt"],
                tokens_completion=u["completion"],
                tokens_used=u["total"],
            )
            with MemoryEngine() as engine, engine.get_connection() as conn, conn:
                conn.execute(
                    """
                    INSERT INTO execution_logs
                    (task_id, stage, tool, result, output, duration_ms, attempt,
                     provider, tokens_prompt, tokens_completion, tokens_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        le.task_id,
                        le.stage,
                        le.tool,
                        le.result,
                        le.output,
                        le.duration_ms,
                        le.attempt,
                        le.provider,
                        le.tokens_prompt,
                        le.tokens_completion,
                        le.tokens_used,
                    ),
                )
        except Exception as db_e:
            log(f"Failed to record execution log to DB: {db_e}", "WARN", tid)

    def run_agent(
        self, agent_name: str, task_desc: str, current_state: str, tid: str | None = None, attempt: int = 1
    ) -> dict[str, Any]:
        """Invokes an agent using either Structured (Instructor) or Legacy mode."""
        if self.halt.is_halted():
            return {"error": "HALTED"}

        default_profile = self.agent_registry.profiles["developer"]
        profile = self.agent_registry.profiles.get(agent_name, default_profile)

        session_data = self.session.read()
        prompt = self.builder.build(agent_name, profile, task_desc, session_data, current_state, tid)

        response_model = self.RESPONSE_MODELS.get(agent_name)
        log(f"Calling {agent_name} (Mode: {'Structured' if response_model else 'Legacy XML'})", "INFO", tid)

        start_time = time.perf_counter()
        try:
            ai_resp, usage = self.api.call(agent_name, profile, prompt, tid, response_model=response_model)
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self._record_agent_execution(
                tid, current_state, agent_name, "API_ERROR", str(e), duration_ms, attempt, provider=profile.provider
            )
            self.halt.halt(f"Critical API Failure - {e}", tid=tid)
            return {"error": "API_SYSTEM_ERROR"}
        else:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            writes: list[FileWrite] = []
            skills: list[SkillCall] = []

            if response_model and not isinstance(ai_resp, str):
                match ai_resp:
                    case QueenResponse() as q_resp:
                        # SMART TASK MERGE: Extract existing tasks from disk, overlay AI updates
                        orig_content = self.tasks.path.read_text(encoding="utf-8") if self.tasks.path.exists() else ""
                        _, agent_part = self.tasks._split_sections(orig_content)

                        existing_tasks = {}
                        import re as regex

                        task_pattern = regex.compile(
                            r"^\s*-\s*\[\s*([^\]]*)\s*\]\s*(GOAL|TASK)-([\w\-]+):\s*(.+)$", regex.IGNORECASE
                        )
                        for line in agent_part.splitlines():
                            if match := task_pattern.match(line):
                                t_id = match.group(3)
                                existing_tasks[t_id] = line

                        for t in q_resp.updated_tasks:
                            icon = "[x]" if t.status == "completed" else "[ ]"
                            # Cleaner, less verbose task description formatting
                            combined_desc = f"{t.description.strip()} (File: `{t.source_file}`, Test: `{t.test_file}`)"
                            new_line = f"- {icon} TASK-{t.id}: {combined_desc}[attempts: {t.attempts}]"
                            existing_tasks[t.id] = new_line

                        sorted_task_lines = [existing_tasks[k] for k in sorted(existing_tasks.keys())]
                        md_lines = ["## [AGENT_PROGRESS]", *sorted_task_lines]

                        writes.append(FileWrite(path="agent_context/TASKS.md", content="\n".join(md_lines) + "\n"))

                        if hasattr(q_resp, "thought") and q_resp.thought:
                            self.session.write_action_log(f"[STRATEGY thought]\n{q_resp.thought}")

                        if tid and tid.startswith("GOAL-"):
                            fb = self.session.read().get("FEEDBACK", "")
                            if f"PLANNED:{tid}" not in fb:
                                self.session.write_feedback(f"{fb}\nPLANNED:{tid}".strip())

                    case DeveloperResponse(files=f, skills=s):
                        writes.extend(f)
                        skills.extend(s)

                    case AuditorResponse(is_verified=ok, feedback_for_dev=fb):
                        if not ok:
                            self._record_agent_execution(
                                tid,
                                current_state,
                                agent_name,
                                "FAIL_AUDIT",
                                str(ai_resp),
                                duration_ms,
                                attempt,
                                provider=profile.provider,
                                usage=usage,
                            )
                            return {"error": f"VERIFICATION_FAILED: {fb}"}

            else:
                pattern = r'<file_write path="([^"]+)">\n?(.*?)\n?</file_write>'
                for m in re.finditer(pattern, str(ai_resp), re.DOTALL):
                    content = m.group(2).strip()
                    if content.startswith("```"):
                        content = re.sub(r"^```[a-z]*\n|```$", "", content, flags=re.MULTILINE)
                    writes.append(FileWrite(path=m.group(1), content=content + "\n"))

                for m in re.finditer(r"<<<SKILL:([^|>]+)(?:\|([^>]*))?>>>", str(ai_resp)):
                    raw_args = (m.group(2) or "").split("|")
                    args = {k.strip(): v.strip() for a in raw_args if ":" in a for k, _, v in [a.partition(":")]}
                    skills.append(SkillCall(name=m.group(1), arguments=args))

                if agent_name == "queen" and tid and tid.startswith("GOAL-"):
                    fb = self.session.read().get("FEEDBACK", "")
                    if f"PLANNED:{tid}" not in fb:
                        self.session.write_feedback(f"{fb}\nPLANNED:{tid}".strip())

            # SURGICAL PATCH: Safety Lock enabled by propagating state to _apply_file_writes
            writes_count = self._apply_file_writes(writes, tid, state=current_state)
            skill_results = self._apply_skill_calls(skills, tid, stage=current_state, attempt=attempt)

            if self.halt.is_halted():
                self._record_agent_execution(
                    tid,
                    current_state,
                    agent_name,
                    "SECURITY_HALT",
                    str(ai_resp),
                    duration_ms,
                    attempt,
                    provider=profile.provider,
                    usage=usage,
                )
                return {"error": "SECURITY_HALT"}

            if current_state == "STRATEGY" and writes_count == 0:
                self._record_agent_execution(
                    tid,
                    current_state,
                    agent_name,
                    "POLICY_VIOLATION",
                    str(ai_resp),
                    duration_ms,
                    attempt,
                    provider=profile.provider,
                    usage=usage,
                )
                return {"error": "POLICY_VIOLATION: No task updates proposed."}

            combined_skills = "".join(skill_results)
            if any(f in combined_skills for f in ["FAIL", "ERROR"]):
                self._record_agent_execution(
                    tid,
                    current_state,
                    agent_name,
                    "FAIL_LINT",
                    str(ai_resp),
                    duration_ms,
                    attempt,
                    provider=profile.provider,
                    usage=usage,
                )
                return {"error": "QUALITY_GATE_REJECT", "log": combined_skills}

            self._record_agent_execution(
                tid,
                current_state,
                agent_name,
                "OK",
                str(ai_resp),
                duration_ms,
                attempt,
                provider=profile.provider,
                usage=usage,
            )
            return {"status": "OK"}

    def _execute_stage(
        self, state: str, agent: str, tid: str, conf: StageConfig, task_desc: str, attempt: int
    ) -> dict[str, Any]:
        """Central dispatcher for robust stage execution logic (Subprocess or LLM)."""
        if not conf.requires_llm.value:
            skill_map = {"LINTING": "quality-gate", "TESTING": "testing-pro"}
            skill = skill_map.get(state)
            if skill:
                if state == "LINTING":
                    log("Executing Dumb Pedant (Local Autofix & Linter)...", "INFO", tid)

                tag, out = self._run_skill_process(skill, {}, tid, stage=state, attempt=attempt)

                if "RESULT:PASS" in tag:
                    if state == "LINTING":
                        log("Dumb Pedant passed perfectly. Skipping AI Pedant.", "OK", tid)
                    return {"status": "OK"}
                if state == "LINTING":
                    log("Dumb Pedant found complex errors. Escalating to AI...", "WARN", tid)
                    self.session.write_action_log(f"Dumb Pedant Error:\n{out[:250]}...")
                    return self.run_agent(agent, task_desc, state, tid, attempt=attempt)

                return {"error": f"SKILL_FAILED: {tag}"}

        if state == "VERIFYING":
            log("Compressing context before Verifying (Pre-flight)...", "INFO", tid)
            self._run_skill_process("context-compressor", {}, tid, stage=state, attempt=attempt)

        return self.run_agent(agent, task_desc, state, tid, attempt=attempt)

    def _run_vcs_delivery(self, tid: str) -> bool:
        """Pythonic implementation of the delivery stage (Local/GitHub)."""
        cfg = self.orch_config.vcs_control
        log(f"📦 VCS Delivery (Mode: {cfg.mode.value})", "PIPELINE", tid)

        is_branch_per_goal = cfg.local_git_settings.branch_per_goal.value
        active_goal = self.tasks.get_current_goal_id()
        branch = f"feat/{active_goal}" if is_branch_per_goal and active_goal else "main"

        self.git.ensure_branch(branch)

        if cfg.local_git_settings.auto_commit.value:
            self.git.commit_all(f"feat({tid}): automated delivery")

        match cfg.mode.value:
            case "local_git":
                return True
            case "github":
                try:
                    gh = GitHubAPIClient(self.env, self.orch_config)
                    if cfg.github_settings.auto_push.value:
                        self.git.push()

                    if cfg.github_settings.auto_pr.value:
                        try:
                            pr_name = active_goal if active_goal else tid
                            pr = gh.create_pull_request(branch, f"PROPOSAL: GOAL-{pr_name}", "Automated PR.")
                            log(f"PR Created: {pr.html_url}", "OK", tid)
                        except Exception as pr_err:
                            if "422" in str(pr_err):
                                log("PR already exists, continuing to polling...", "INFO", tid)
                            else:
                                raise

                    delivery_success = True
                    if cfg.github_settings.watch_gha.value:
                        run = gh.poll_workflow_status(branch)
                        delivery_success = run.conclusion == "success"
                except Exception as e:
                    log(f"GitHub Error: {e}", "ERROR", tid)
                    return False
                else:
                    return delivery_success
            case _:
                log(f"Unknown VCS mode: {cfg.mode.value}", "ERROR", tid)
                return False

    def _sync_vcs_state(self, tid: str) -> None:
        """Helper to sync orchestration meta-state (TASKS.md, SESSION.md) to Git."""
        vcs_stage_cfg = self.orch_config.workflow_local.get("VCS_DELIVERY")
        if not vcs_stage_cfg or not vcs_stage_cfg.active.value:
            return

        vcs_cfg = self.orch_config.vcs_control
        if vcs_cfg.mode.value in {"local_git", "github"} and self.git.is_dirty():
            self.git.commit_all(f"chore(state): sync meta-state for {tid}")

            is_gh = vcs_cfg.mode.value == "github"
            auto_push = vcs_cfg.github_settings.auto_push.value

            if is_gh and auto_push:
                try:
                    log("Pushing meta-state to remote...", "INFO", tid)
                    self.git.push()
                    log("Meta-state synced successfully.", "OK", tid)
                except Exception as e:
                    log(f"Failed to push meta-state: {e}", "WARN", tid)

    def _run_reflection(self, goal_id: str) -> None:
        """Post-Mortem analyzer: extracts lessons learned from recent execution failures."""
        if not self.orch_config.memory_engine.enabled.value:
            return

        try:
            with MemoryEngine() as engine, engine.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT task_id, stage, tool, result, output
                    FROM execution_logs
                    WHERE result != 'PASS'
                      AND result NOT LIKE 'COMPRESS_%'
                      AND result NOT LIKE 'MCP_%'
                    ORDER BY timestamp DESC
                    LIMIT 20
                    """
                )
                rows = cursor.fetchall()

            if not rows:
                log("No execution errors found for reflection.", "INFO", goal_id)
                return

            log("Running Post-Mortem Reflection...", "STATE", goal_id)
            self.session.write_state("REFLECTION", goal_id)

            error_summaries = [
                f"Task: {r['task_id']} | Stage: {r['stage']} | Tool: {r['tool']} | Result: {r['result']}\n"
                f"Output:\n{str(r['output'])[:600]}{'...' if len(str(r['output'])) > 600 else ''}"
                for r in rows
            ]
            errors_text = "\n\n".join(error_summaries)

            prompt = (
                "You are the Lead Architect analyzing execution logs from the recently completed goal.\n"
                "Review the following errors that occurred during development.\n"
                "Extract structured lessons learned (anti-patterns, fixes, best practices) to prevent "
                "these mistakes in the future.\n\n"
                f"RECENT EXECUTION ERRORS:\n{errors_text}"
            )

            profile = self.agent_registry.profiles.get("queen", self.agent_registry.profiles["developer"])
            log("Calling Queen for Post-Mortem Analysis...", "INFO", goal_id)

            resp, _ = self.api.call(
                agent="queen",
                profile=profile,
                prompt=prompt,
                tid=goal_id,
                response_model=ReflectionResponse,
            )

            if isinstance(resp, ReflectionResponse) and resp.reflections:
                with MemoryEngine() as engine, engine.get_connection() as conn, conn:
                    for ref in resp.reflections:
                        conn.execute(
                            """
                            INSERT INTO system_reflections (goal_id, error_pattern, solution, tags)
                            VALUES (?, ?, ?, ?)
                            """,
                            (goal_id, ref.error_pattern, ref.solution, ref.tags),
                        )

                    max_refs = self.orch_config.memory_engine.max_reflections.value
                    conn.execute(
                        """
                        DELETE FROM system_reflections
                        WHERE id NOT IN (
                            SELECT id FROM system_reflections
                            ORDER BY created_at DESC
                            LIMIT ?
                        )
                        """,
                        (max_refs,),
                    )
                log(f"Saved {len(resp.reflections)} reflections to Memory Engine.", "OK", goal_id)
            else:
                log("No actionable reflections extracted.", "INFO", goal_id)

        except Exception as e:
            log(f"Reflection process failed: {e}", "WARN", goal_id)

    def run_pipeline(self) -> None:
        """Main autonomous loop with adaptive delays and strictly routed stages."""
        log("Pipeline Started", "PIPELINE")
        wf = self.orch_config.workflow_global
        local_wf = self.orch_config.workflow_local

        for _ in range(wf.max_continuous_tasks.value):
            active_tasks = self.tasks.get_active_tasks()
            if not active_tasks:
                break

            task = active_tasks[0]
            tid = str(task["id"])

            # PRE-FLIGHT GOAL VALIDATOR (Contract-Driven Constraints)
            if task.get("is_synthetic"):
                desc = task.get("description", "")
                missing = [req for req in ["INTENT:", "CONSTRAINTS:", "METRIC:"] if req not in desc]
                if missing:
                    err_msg = f"CRITICAL: Invalid GOAL format. Missing sections: {', '.join(missing)}."
                    log(err_msg, "ERROR", tid)
                    self.session.write_state("BLOCKED", tid)
                    self.session.write_feedback(err_msg)

                    gid = tid.replace("GOAL-", "")
                    self.tasks._update_status("GOAL", gid, "BLOCKED")
                    self._sync_vcs_state(tid)
                    break

            desc_preview = task.get("description", "").splitlines()[0].strip()
            log(f"Processing {tid} : {desc_preview}", "PIPELINE", tid)

            vcs_stage_cfg = local_wf.get("VCS_DELIVERY")
            is_vcs_enabled = vcs_stage_cfg and vcs_stage_cfg.active.value

            if is_vcs_enabled:
                vcs_cfg = self.orch_config.vcs_control
                if vcs_cfg.mode.value in {"local_git", "github"} and vcs_cfg.local_git_settings.branch_per_goal.value:
                    active_goal = self.tasks.get_current_goal_id()
                    if active_goal:
                        self.git.ensure_branch(f"feat/{active_goal}")

            if task.get("is_synthetic"):
                fb = self.session.read().get("FEEDBACK", "")
                if f"PLANNED:{tid}" in fb and self.tasks.are_all_tasks_completed():
                    gid = tid.replace("GOAL-", "")
                    self.tasks.mark_goal_completed(gid)
                    log(f"Auto-closed {tid}", "OK", tid)

                    self._run_reflection(gid)

                    self.session.write_state("IDLE", tid)
                    self._sync_vcs_state(tid)
                    continue

            stages = [
                ("STRATEGY", "queen"),
                ("EXECUTING", "developer"),
                ("LINTING", "pedant"),
                ("TESTING", "developer"),
                ("VERIFYING", "auditor"),
                ("VCS_DELIVERY", "auditor"),
            ]

            action_log = self.session.read().get("ACTION_LOG", "")
            task_success = True

            for state, agent in stages:
                conf = local_wf.get(state)
                if not conf or not conf.active.value:
                    continue

                success_marker = f"STAGE_SUCCESS:{state}:{tid}"
                is_synth = task.get("is_synthetic")

                if success_marker in action_log and not is_synth:
                    continue

                if is_synth and state != "STRATEGY":
                    continue

                self.session.write_state(state, tid)
                delay_after_stage = wf.loop_delay_seconds.value if conf.requires_llm.value else 0.1

                current_attempts = action_log.count(f"STAGE_FAIL:{state}:{tid}") + 1

                if state == "VCS_DELIVERY":
                    success_val = self._run_vcs_delivery(tid)
                    res = {"status": "OK"} if success_val else {"error": "VCS_FAIL"}
                else:
                    res = self._execute_stage(state, agent, tid, conf, task.get("description", ""), current_attempts)

                success = "error" not in res

                if not success:
                    if res.get("error") in {"API_SYSTEM_ERROR", "SECURITY_HALT", "HALTED"}:
                        self.session.write_state("BLOCKED", tid)
                        self._sync_vcs_state(tid)
                        return

                    max_retries = conf.max_retries.value
                    log(f"Stage {state} failed ({current_attempts}/{max_retries})", "WARN", tid)
                    self.session.write_action_log(f"STAGE_FAIL:{state}:{tid}")

                    if current_attempts < max_retries:
                        err_msg = res.get("error")

                        # SURGICAL PATCH 2.0.2: Targeted FEEDBACK cleanup & Smart LINTING history
                        current_fb = self.session.read().get("FEEDBACK", "")
                        fb_lines = current_fb.splitlines()
                        planned_lines = [l for l in fb_lines if l.startswith("PLANNED:")]

                        if state == "LINTING":
                            # Keep last 2 errors to make room for the new one (total 3)
                            error_lines = [l for l in fb_lines if "LAST_ERROR" in l]
                            recent_errors = error_lines[-2:]
                            new_err = f"LAST_ERROR in {state} for {tid} (Attempt {current_attempts}): {err_msg}"
                            self.session.write_feedback("\n".join([*planned_lines, *recent_errors, new_err]).strip())
                        else:
                            # Standard replacement for non-linting stages
                            new_err = f"LAST_ERROR in {state} for {tid}: {err_msg}"
                            self.session.write_feedback("\n".join([*planned_lines, new_err]).strip())

                        if state in ["LINTING", "TESTING", "VERIFYING", "VCS_DELIVERY"]:
                            s = self.session.read()
                            action_log_curr = s.get("ACTION_LOG", "")

                            stages_to_revert = ["EXECUTING", "LINTING", "TESTING", "VERIFYING"]
                            for s_rev in stages_to_revert:
                                old_tag = f"STAGE_SUCCESS:{s_rev}:{tid}"
                                new_tag = f"REVERTED:{s_rev}:{tid}"
                                action_log_curr = action_log_curr.replace(old_tag, new_tag)

                            action_log_curr += "\n\n--- NEW ATTEMPT (PREVIOUS FAILURE DETECTED) ---\n"

                            s["ACTION_LOG"] = action_log_curr
                            self.session._write_all(s)

                        task_success = False
                        time.sleep(delay_after_stage)
                        break

                    self.tasks.increment_attempts(tid, str(res.get("error", "Max retries")))
                    self.session.write_state("BLOCKED", tid)
                    self._sync_vcs_state(tid)
                    return

                self.session.write_action_log(f"STAGE_SUCCESS:{state}:{tid}")
                time.sleep(delay_after_stage)

            if task_success:
                if not task.get("is_synthetic"):
                    self.tasks.mark_completed(tid)

                # Final cleanup of errors upon task success
                current_fb = self.session.read().get("FEEDBACK", "")
                cleaned_fb = "\n".join(
                    line for line in current_fb.splitlines() if not line.startswith("LAST_ERROR")
                ).strip()
                self.session.write_feedback(cleaned_fb)

                self.session.write_state("IDLE", tid)
                status_msg = "Planned" if task.get("is_synthetic") else "Finished"
                log(f"Task {tid} {status_msg}", "OK", tid)

            self._sync_vcs_state(tid)

            if not task_success and not wf.loop_mode.value:
                break
