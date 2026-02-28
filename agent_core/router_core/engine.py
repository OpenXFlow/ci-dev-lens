#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""agent_core/router_core/engine.py - Main cyclical logic (Router) (v 1.3 Pydantic)."""

import re
import subprocess
import time
from typing import Any

from .llm import APIClient, PromptBuilder, TokenBudgetManager
from .managers import HaltManager, SessionManager, TasksManager
from .utils import (
    ROOT,
    UV_PATH,
    load_agents_registry,
    load_env,
    load_orchestrator_config,
    log,
)


class Router:
    """Core state machine and orchestration engine."""

    def __init__(self, mock: bool = False) -> None:
        self.env = load_env()
        self.orch_config = load_orchestrator_config()  # Previously load_agent_policy

        # Source of Truth: CLI arg OR .env variable
        self.mock = mock or self.env.MOCK

        # Load Agents Registry (formerly agents.json)
        self.agent_registry = load_agents_registry()

        self.session = SessionManager()
        self.tasks = TasksManager()
        self.halt = HaltManager()

        self.api = APIClient(self.env, self.mock, self.orch_config)
        self.builder = PromptBuilder()

    def _execute_skill(self, name: str, args: dict[str, str], tid: str | None = None) -> tuple[str, str]:
        log(f"Executing skill: {name} {args}", "INFO", tid=tid)
        s_map = {
            "testing-pro": ".claude/skills/testing-pro/scripts/verify.py",
            "quality-gate": ".claude/skills/quality-gate/scripts/check.sh",
            "security-guard": ".claude/skills/security-guard/scripts/scan.py",
            "context-compressor": ".claude/skills/context-compressor/scripts/summarize.py",
            "git-manager": ".claude/skills/git-manager/scripts",
        }

        rel_path = f"{s_map[name]}/{args.get('action', 'push')}.sh" if name == "git-manager" else s_map.get(name)
        if not rel_path or not (ROOT / rel_path).exists():
            return "RESULT:ERROR", "Skill not found"

        script_path = ROOT / rel_path
        env = {
            # Use Pydantic dump or explicit construction if needed,
            # but here subprocess needs strict strings.
            "MOCK": "true" if self.mock else "false",
            "PATH": str(ROOT) + ":" + "/usr/local/bin:/usr/bin:/bin",
            **{k: v for k, v in self.env.model_dump().items() if isinstance(v, str) and k != "credentials"},
        }

        cmd = (
            [UV_PATH, "run", "python", str(script_path)] if script_path.suffix == ".py" else ["bash", str(script_path)]
        )
        for k, v in args.items():
            if k != "action":
                cmd.extend([f"--{k}", v])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
        except Exception as e:
            return f"RESULT:ERROR:{e}", str(e)
        else:
            output = res.stdout + "\n" + res.stderr
            tag = "RESULT:COMPLETED"
            for line in reversed(output.splitlines()):
                if "RESULT:" in line:
                    tag = line.strip()
                    break
            return tag, output

    def run_agent(self, agent_name: str, task_desc: str, current_state: str, tid: str | None = None) -> dict[str, Any]:
        if self.halt.is_halted():
            return {"error": "HALTED"}

        # Pydantic Registry Lookup
        if agent_name not in self.agent_registry.profiles:
            # Fallback to developer if specific agent not found (safety)
            profile = self.agent_registry.profiles["developer"]
        else:
            profile = self.agent_registry.profiles[agent_name]

        session_data = self.session.read()
        prompt = self.builder.build(agent_name, profile, task_desc, session_data)

        # Token Budget using Pydantic Config
        budget = TokenBudgetManager(profile.max_tokens, self.orch_config)
        if budget.check(prompt) == "yellow":
            self._execute_skill("context-compressor", {}, tid=tid)

        log(f"Calling {agent_name} ({profile.model})", "INFO", tid=tid)

        try:
            response = self.api.call(agent_name, profile, prompt, tid=tid)
        except Exception as e:
            err_str = str(e)
            self.halt.halt(f"Critical API Failure - {err_str}", tid=tid)
            return {"error": "API_SYSTEM_ERROR"}

        writes_count = 0

        for m in re.finditer(r'<file_write path="([^"]+)">\n?(.*?)\n?</file_write>', response, re.DOTALL):
            path, content = m.group(1), m.group(2)

            content = content.strip()
            if content.startswith("```python"):
                content = content[9:].lstrip()
            elif content.startswith("```"):
                content = content[3:].lstrip()

            if content.endswith("```"):
                content = content[:-3].rstrip()

            if not content.endswith("\n"):
                content += "\n"

            if path == "agent_context/TASKS.md":
                existing_ids = self.tasks.get_all_task_ids()
                new_ids = set(re.findall(r"TASK-(\d+)", content))
                if existing_ids - new_ids:
                    return {"error": f"HISTORY_VIOLATION: Missing tasks {existing_ids - new_ids}"}

                if tid and str(tid) != "START" and not str(tid).startswith("GOAL-"):
                    clean_tid = str(tid).replace("TASK-", "").replace("GOAL-", "")
                    pattern = rf"- \[x\] (TASK-{clean_tid}\b)"
                    if re.search(pattern, content):
                        content = re.sub(pattern, r"- [ ] \1", content)
                        log(
                            f"Silent Auto-Correction: Task {clean_tid} reverted to [ ].",
                            "WARN",
                            tid,
                        )

            # CORE PROTECTION: Updated paths for Model 5.3
            if not any(
                path.startswith(p)
                for p in [
                    "agent_core/",
                    "agent_tests/",
                    ".claude/",
                    ".agents/",
                    "agent_context/SESSION.md",
                ]
            ):
                dest = ROOT / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                log(f"File written: {path}", "OK", tid=tid)
                writes_count += 1

        for m in re.finditer(r"<<<SKILL:([^|>]+)(?:\|([^>]*))?>>>", response):
            name, args_str = m.group(1), m.group(2) or ""
            args = {k.strip(): v.strip() for k, _, v in [a.partition(":") for a in args_str.split("|") if ":" in a]}
            if name == "git-manager" and "action" not in args:
                args["action"] = args_str

            tag, out = self._execute_skill(name, args, tid=tid)
            self.session.write_action_log(f"Skill {name} -> {tag}\nOutput: {out[:250]}...")

            if "RESULT:SECRET_FOUND" in tag:
                self.halt.halt(f"Secret detected by {agent_name}!", tid=tid)
                return {"error": "SECURITY_HALT"}
            if "RESULT:ERROR" in tag:
                return {"error": f"Skill {name} failed with system error: {tag}"}
            if any(fc in tag for fc in ["RUFF_FAIL", "MYPY_FAIL", "TEST_FAIL", "FAIL"]):
                return {"error": f"QUALITY_GATE_REJECT: {tag}", "log": out}

        for m in re.finditer(r"<<<SESSION:(\w+)\|([^>]*)>>>", response):
            cmd, val = m.group(1), m.group(2)
            if cmd == "update_context":
                self.session.write_action_log(f"AGENT_SUGGESTION: {val}")
            if cmd == "add_workspace":
                self.session.add_workspace(val)

        if agent_name == "queen" and current_state == "PLANNING" and writes_count == 0:
            return {"error": "POLICY_VIOLATION: Queen did not update TASKS.md"}

        if current_state == "EXECUTING" and writes_count == 0:
            if "```" in response:
                return {
                    "error": 'POLICY_VIOLATION: You used a markdown block instead of <file_write path="...">. Fix it.'
                }
            return {"error": "POLICY_VIOLATION: Developer did not submit code changes via <file_write> tags."}

        return {"status": "OK"}

    def _run_cloud_stage(self, task: dict[str, Any]) -> bool:
        tid = str(task.get("id", ""))
        log("☁️  Starting CLOUD STAGE (GHA v2)...", "PIPELINE", tid=tid)
        if self.run_agent("git-manager", str(task.get("description", "")), "CLOUD_PUSH", tid=tid).get("error"):
            return False
        log("⏳ Waiting for GitHub Actions...", "INFO", tid=tid)
        tag, _ = self._execute_skill("git-manager", {"action": "gha_status"}, tid=tid)
        if "RESULT:GHA_PASS" in tag:
            log("🚀 GHA cloud stage passed!", "OK", tid=tid)
            return True
        log("❌ GHA failed.", "ERROR", tid=tid)
        return False

    def run_pipeline(self) -> None:
        log("Starting pipeline...", "PIPELINE")
        iterations = 0
        # Pydantic Access for Workflow Settings
        wf_global = self.orch_config.workflow_global
        wf_local = self.orch_config.workflow_local

        max_iter = wf_global.max_continuous_tasks.value

        while iterations < max_iter:
            tasks = self.tasks.get_active_tasks()
            if not tasks:
                break

            task = tasks[0]
            tid = str(task["id"])
            log(f"Processing {tid}", "PIPELINE", tid=tid)

            if task.get("is_synthetic"):
                ctx = self.session.read().get("CONTEXT", "")

                if f"PLANNED:{tid}" in ctx:
                    content = self.tasks.path.read_text(encoding="utf-8")
                    agent_part = content.split("## [AGENT_PROGRESS]")[-1]

                    total_tasks = agent_part.count("- [")
                    completed_tasks = agent_part.count("- [x]")

                    if total_tasks > 0 and total_tasks == completed_tasks:
                        gid = tid.replace("GOAL-", "")
                        self.tasks.mark_goal_completed(gid)
                        log(
                            f"Auto-closed {tid} (All planned sub-tasks finished).",
                            "OK",
                            tid=tid,
                        )
                        self.session.write_state("IDLE", tid=tid)
                        continue

            action_log = self.session.read().get("ACTION_LOG", "")

            stages = [
                ("ANALYSE", "queen"),
                ("PLANNING", "queen"),
                ("EXECUTING", "developer"),
                ("LINTING", "pedant"),
                ("TESTING", "developer"),
                ("VERIFYING", "auditor"),
            ]
            task_success = True

            for state, agent in stages:
                # Pydantic Access for Local Stage Settings
                conf = wf_local.get(state)
                if not conf or not conf.active.value:
                    continue

                if f"STAGE_SUCCESS:{state}:{tid}" in action_log and not task.get("is_synthetic"):
                    continue

                if task.get("is_synthetic") and state not in ["ANALYSE", "PLANNING"]:
                    continue

                self.session.write_state(state, tid=tid)
                res = self.run_agent(agent, str(task.get("description", "")), state, tid=tid)

                if "error" in res:
                    if res["error"] in ["API_SYSTEM_ERROR", "SECURITY_HALT", "HALTED"]:
                        log(
                            f"Pipeline stopped completely due to critical error: {res['error']}",
                            "ERROR",
                            tid=tid,
                        )
                        self.session.write_state("BLOCKED", tid=tid)
                        return

                    max_stage_retries = conf.max_retries.value
                    current_stage_attempts = action_log.count(f"STAGE_FAIL:{state}:{tid}") + 1

                    log(
                        f"Stage {state} failed (Attempt {current_stage_attempts}/{max_stage_retries}).",
                        "WARN",
                        tid=tid,
                    )
                    self.session.write_action_log(f"STAGE_FAIL:{state}:{tid}")

                    if current_stage_attempts < max_stage_retries:
                        self.session.write_context(
                            f"LAST_ERROR in {state} for {tid}: {res.get('log', 'Unknown error')}"
                        )

                        if state in ["LINTING", "TESTING", "VERIFYING"]:
                            log(
                                "Routing back to EXECUTING to fix code issues.",
                                "WARN",
                                tid=tid,
                            )
                            s = self.session.read()
                            s["ACTION_LOG"] = s.get("ACTION_LOG", "").replace(
                                f"STAGE_SUCCESS:EXECUTING:{tid}",
                                f"REVERTED:EXECUTING:{tid}",
                            )
                            self.session._write_all(s)

                        task_success = False
                        break
                    log(
                        f"Stage {state} retries exhausted. Global attempt incremented.",
                        "ERROR",
                        tid=tid,
                    )
                    self.tasks.increment_attempts(tid, str(res["error"]))
                    self.session.write_state("BLOCKED", tid=tid)
                    return

                self.session.write_action_log(f"STAGE_SUCCESS:{state}:{tid}")
                if state == "ANALYSE" and conf.pause_after and conf.pause_after.value:
                    log("Analysis completed. Pausing.", "OK", tid=tid)
                    return

                if state == "PLANNING" and task.get("is_synthetic"):
                    log(
                        "Plan created. Deferring execution to sub-tasks.",
                        "INFO",
                        tid=tid,
                    )

                    ctx = self.session.read().get("CONTEXT", "")
                    if f"PLANNED:{tid}" not in ctx:
                        self.session.write_context(ctx.strip() + f"\nPLANNED:{tid}")

                    task_success = False
                    break

            if not task_success:
                iterations += 1
                continue

            if not task.get("is_synthetic"):
                self.tasks.mark_completed(tid)

            if self.env.CI_MODE == "github" and not self._run_cloud_stage(task):
                self.session.write_state("BLOCKED", tid=tid)
                break

            self.session.write_state("IDLE", tid=tid)
            log("Task successfully completed.", "OK", tid=tid)

            if not wf_global.loop_mode.value:
                break

            # Rate Limit Protection
            delay = wf_global.loop_delay_seconds.value
            if delay > 0 and self.tasks.get_active_tasks():
                log(f"Rate limit protection: waiting {delay}s before next task...", "INFO")
                time.sleep(delay)

            iterations += 1

        if iterations >= max_iter:
            log(f"Safety limit reached ({max_iter} iterations).", "WARN")
