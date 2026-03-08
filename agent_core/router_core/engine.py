#!/usr/bin/env python3
# The MIT License (MIT)
# Copyright (c) 2026 Jozef Darida (LinkedIn/Xing)
# For full license text, see the LICENSE file in the project root.

"""
agent_core/router_core/engine.py
Hybrid Orchestration Engine (v 1.25 VCS Master Kill-Switch).
"""

import re
import subprocess
import time
from typing import Any, ClassVar

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
from .utils import (
    ROOT,
    load_agents_registry,
    load_env,
    load_orchestrator_config,
    log,
)


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

    def _apply_file_writes(self, writes: list[FileWrite], tid: str | None = None) -> int:
        """Physically commits file changes to disk with security checks."""
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
                existing_ids = self.tasks.get_all_task_ids()
                new_ids = set(re.findall(r"TASK-(\d+)", content))
                if existing_ids - new_ids:
                    log(f"History Violation: Queen tried to delete tasks {existing_ids - new_ids}", "ERROR", tid)
                    continue

                # ARCHITECT SHIELD: Prevent premature completion
                if tid and not str(tid).startswith("GOAL-"):
                    pattern = re.compile(rf"-\s*\[\s*x\s*\]\s*TASK-{tid}\b", re.IGNORECASE)
                    if pattern.search(content):
                        content = pattern.sub(f"-[ ] TASK-{tid}", content)
                        w.content = content
                        log(
                            f"Sanitized TASKS.md: Prevented agent from prematurely marking TASK-{tid} as [x]",
                            "WARN",
                            tid,
                        )

            dest = ROOT / w.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            log(f"File written: {w.path}", "OK", tid)
            count += 1
        return count

    def _apply_skill_calls(self, calls: list[SkillCall], tid: str | None = None) -> list[str]:
        """Executes a batch of skills and returns their status tags."""
        results = []
        for c in calls:
            tag, out = self._run_skill_process(c.name, c.arguments, tid)
            self.session.write_action_log(f"Skill {c.name} -> {tag}\nOutput: {out[:250]}...")
            results.append(tag)

            if "RESULT:SECRET_FOUND" in tag:
                self.halt.halt(f"Secret detected during skill {c.name}!", tid)
        return results

    def _run_skill_process(self, name: str, args: dict[str, str], tid: str | None = None) -> tuple[str, str]:
        """Low-level skill execution via subprocess."""
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

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
        except Exception as e:
            return f"RESULT:ERROR:{e}", str(e)
        else:
            output = res.stdout + "\n" + res.stderr
            tag = next(
                (line.strip() for line in reversed(output.splitlines()) if "RESULT:" in line), "RESULT:COMPLETED"
            )
            return tag, output

    def run_agent(self, agent_name: str, task_desc: str, current_state: str, tid: str | None = None) -> dict[str, Any]:
        """Invokes an agent using either Structured (Instructor) or Legacy mode."""
        if self.halt.is_halted():
            return {"error": "HALTED"}

        default_profile = self.agent_registry.profiles["developer"]
        profile = self.agent_registry.profiles.get(agent_name, default_profile)

        session_data = self.session.read()
        prompt = self.builder.build(agent_name, profile, task_desc, session_data)

        response_model = self.RESPONSE_MODELS.get(agent_name)
        log(f"Calling {agent_name} (Mode: {'Structured' if response_model else 'Legacy XML'})", "INFO", tid)

        try:
            ai_resp = self.api.call(agent_name, profile, prompt, tid, response_model=response_model)
        except Exception as e:
            self.halt.halt(f"Critical API Failure - {e}", tid=tid)
            return {"error": "API_SYSTEM_ERROR"}
        else:
            writes: list[FileWrite] = []
            skills: list[SkillCall] = []

            if response_model and not isinstance(ai_resp, str):
                match ai_resp:
                    case QueenResponse(updated_tasks=tasks):
                        original_content = self.tasks.path.read_text(encoding="utf-8")
                        user_match = re.search(r"(?s)^(.*?)\n---\n", original_content)
                        if not user_match:
                            user_match = re.search(r"(?s)^(.*?)## \[AGENT_PROGRESS\]", original_content)

                        user_section = user_match.group(1).strip() if user_match else original_content.strip()

                        md_lines = [user_section, "", "---", "", "## [AGENT_PROGRESS]"]
                        for t in tasks:
                            icon = "[x]" if t.status == "completed" else "[ ]"
                            md_lines.append(f"- {icon} TASK-{t.id}: {t.description.strip()} [attempts: {t.attempts}]")

                        writes.append(FileWrite(path="agent_context/TASKS.md", content="\n".join(md_lines) + "\n"))

                        if tid and tid.startswith("GOAL-"):
                            fb = self.session.read().get("FEEDBACK", "")
                            if f"PLANNED:{tid}" not in fb:
                                self.session.write_feedback(f"{fb}\nPLANNED:{tid}".strip())

                    case DeveloperResponse(files=f, skills=s):
                        writes.extend(f)
                        skills.extend(s)

                    case AuditorResponse(is_verified=ok, feedback_for_dev=fb):
                        if not ok:
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

            writes_count = self._apply_file_writes(writes, tid)
            skill_results = self._apply_skill_calls(skills, tid)

            if self.halt.is_halted():
                return {"error": "SECURITY_HALT"}

            if current_state == "PLANNING" and writes_count == 0:
                return {"error": "POLICY_VIOLATION: No task updates proposed."}

            combined_skills = "".join(skill_results)
            if any(f in combined_skills for f in ["FAIL", "ERROR"]):
                return {"error": "QUALITY_GATE_REJECT", "log": combined_skills}

            return {"status": "OK"}

    def _run_vcs_delivery(self, tid: str) -> bool:
        """Pythonic implementation of the delivery stage (Local/GitHub)."""
        cfg = self.orch_config.vcs_control
        log(f"📦 VCS Delivery (Mode: {cfg.mode.value})", "PIPELINE", tid)

        # Branch is aligned strictly with the Active GOAL
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
                            # PR name uses the active goal for consistency
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
        # ARCHITECT FIX: Master Kill-Switch check for State-Sync
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

    def run_pipeline(self) -> None:
        """Main autonomous loop with refined semantic state management."""
        log("Pipeline Started", "PIPELINE")
        wf = self.orch_config.workflow_global
        local_wf = self.orch_config.workflow_local

        for _ in range(wf.max_continuous_tasks.value):
            active_tasks = self.tasks.get_active_tasks()
            if not active_tasks:
                break

            task = active_tasks[0]
            tid = str(task["id"])
            log(f"Processing {tid}", "PIPELINE", tid)

            # =================================================================
            # ARCHITECT UPDATE: Eager Branching with Master Kill-Switch Check
            # =================================================================
            vcs_stage_cfg = local_wf.get("VCS_DELIVERY")
            is_vcs_enabled = vcs_stage_cfg and vcs_stage_cfg.active.value

            if is_vcs_enabled:
                vcs_cfg = self.orch_config.vcs_control
                if vcs_cfg.mode.value in {"local_git", "github"} and vcs_cfg.local_git_settings.branch_per_goal.value:
                    active_goal = self.tasks.get_current_goal_id()
                    if active_goal:
                        self.git.ensure_branch(f"feat/{active_goal}")
            # =================================================================

            if task.get("is_synthetic"):
                fb = self.session.read().get("FEEDBACK", "")
                if f"PLANNED:{tid}" in fb and self.tasks.are_all_tasks_completed():
                    gid = tid.replace("GOAL-", "")
                    self.tasks.mark_goal_completed(gid)
                    log(f"Auto-closed {tid}", "OK", tid)
                    self.session.write_state("IDLE", tid)
                    self._sync_vcs_state(tid)
                    continue

            stages = [
                ("ANALYSE", "queen"),
                ("PLANNING", "queen"),
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

                if is_synth and state not in {"ANALYSE", "PLANNING"}:
                    continue

                self.session.write_state(state, tid)

                match state:
                    case "VCS_DELIVERY":
                        success = self._run_vcs_delivery(tid)
                        res = {"status": "OK"} if success else {"error": "VCS_FAIL"}
                    case _:
                        res = self.run_agent(agent, task["description"], state, tid)
                        success = "error" not in res

                if not success:
                    if res.get("error") in {"API_SYSTEM_ERROR", "SECURITY_HALT", "HALTED"}:
                        self.session.write_state("BLOCKED", tid)
                        self._sync_vcs_state(tid)
                        return

                    current_attempts = action_log.count(f"STAGE_FAIL:{state}:{tid}") + 1
                    max_retries = conf.max_retries.value
                    log(f"Stage {state} failed ({current_attempts}/{max_retries})", "WARN", tid)
                    self.session.write_action_log(f"STAGE_FAIL:{state}:{tid}")

                    if current_attempts < max_retries:
                        err_msg = res.get("error")
                        self.session.write_feedback(f"LAST_ERROR in {state} for {tid}: {err_msg}")

                        if state in {"LINTING", "TESTING", "VERIFYING", "VCS_DELIVERY"}:
                            s = self.session.read()
                            action_log_curr = s.get("ACTION_LOG", "")
                            old_tag = f"STAGE_SUCCESS:EXECUTING:{tid}"
                            new_tag = f"REVERTED:EXECUTING:{tid}"
                            s["ACTION_LOG"] = action_log_curr.replace(old_tag, new_tag)
                            self.session._write_all(s)

                        task_success = False
                        break

                    self.tasks.increment_attempts(tid, str(res.get("error", "Max retries")))
                    self.session.write_state("BLOCKED", tid)
                    self._sync_vcs_state(tid)
                    return

                self.session.write_action_log(f"STAGE_SUCCESS:{state}:{tid}")

            if task_success:
                if not task.get("is_synthetic"):
                    self.tasks.mark_completed(tid)
                self.session.write_state("IDLE", tid)
                log(f"Task {tid} Finished", "OK", tid)

            self._sync_vcs_state(tid)

            if task_success:
                if not wf.loop_mode.value:
                    break
                time.sleep(wf.loop_delay_seconds.value)
            else:
                time.sleep(wf.loop_delay_seconds.value)
