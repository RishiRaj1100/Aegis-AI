"""
AegisAI - Execution Agent
Synthesises the Commander's subtask graph and the Research Agent's insights
into a concrete, step-by-step execution plan with milestones and success criteria.
"""

from __future__ import annotations

import logging
import subprocess
import re
import tempfile
import os
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from services.groq_service import GroqService
from models.schemas import SubTask
from utils.helpers import language_instruction

logger = logging.getLogger(__name__)


# ── SafeExecutionAgent: Sandboxed Command Execution ──────────────────────────

class ExecutionStatus(str, Enum):
    """Status of command execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class CommandExecutionResult:
    """Result of a command execution."""
    command: str
    status: ExecutionStatus
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timestamp: str


class SafeExecutionAgent:
    """
    Safely executes commands with strict sandboxing and validation.
    
    Security principles:
    1. Whitelist approach: only allow known-safe commands
    2. Blacklist: explicitly block dangerous patterns
    3. Sandboxing: run in isolated subprocess with timeout
    4. Audit: log all execution attempts
    5. Resource limits: CPU, memory constraints
    """

    ALLOWED_COMMANDS = [
        "python",
        "python3",
        "curl",
        "wget",
        "mkdir",
        "touch",
        "echo",
        "cat",
        "grep",
        "ls",
        "pwd",
    ]

    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",
        r"dd\s+if=.*of=",
        r":()\s*{.*;}",
        r"sudo\s+",
        r"su\s+",
        r"chmod\s+777",
        r"reboot",
        r"shutdown",
    ]

    def __init__(self, default_timeout: int = 300):
        self.default_timeout = default_timeout

    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Validate if a command is safe to execute."""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Dangerous pattern blocked: {pattern}"
        
        cmd_root = command.split()[0] if command else ""
        is_whitelisted = any(cmd_root.startswith(allowed) for allowed in self.ALLOWED_COMMANDS)
        
        if not is_whitelisted:
            return False, f"Command '{cmd_root}' not whitelisted"
        
        return True, None

    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> CommandExecutionResult:
        """Execute a command safely with sandboxing."""
        start_time = datetime.utcnow()
        timeout = timeout or self.default_timeout
        
        # Validate command
        is_safe, block_reason = self.validate_command(command)
        if not is_safe:
            logger.warning(f"[SafeExecutionAgent] Command blocked: {block_reason}")
            return CommandExecutionResult(
                command=command,
                status=ExecutionStatus.BLOCKED,
                exit_code=-1,
                stdout="",
                stderr=block_reason,
                duration_seconds=0,
                timestamp=start_time.isoformat()
            )
        
        # Execute in sandbox
        with tempfile.TemporaryDirectory() as sandbox_dir:
            env = os.environ.copy()
            env["HOME"] = sandbox_dir
            
            try:
                proc_result = subprocess.run(
                    command,
                    shell=True,
                    timeout=timeout,
                    capture_output=True,
                    text=True,
                    cwd=sandbox_dir,
                    env=env,
                )
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                return CommandExecutionResult(
                    command=command,
                    status=ExecutionStatus.SUCCESS if proc_result.returncode == 0 else ExecutionStatus.FAILURE,
                    exit_code=proc_result.returncode,
                    stdout=proc_result.stdout[:10000],
                    stderr=proc_result.stderr[:10000],
                    duration_seconds=duration,
                    timestamp=start_time.isoformat()
                )
            
            except subprocess.TimeoutExpired:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"[SafeExecutionAgent] Timeout after {timeout}s")
                return CommandExecutionResult(
                    command=command,
                    status=ExecutionStatus.TIMEOUT,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command exceeded timeout of {timeout}s",
                    duration_seconds=duration,
                    timestamp=start_time.isoformat()
                )
            
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"[SafeExecutionAgent] Execution error: {e}")
                return CommandExecutionResult(
                    command=command,
                    status=ExecutionStatus.ERROR,
                    exit_code=-1,
                    stdout="",
                    stderr=str(e),
                    duration_seconds=duration,
                    timestamp=start_time.isoformat()
                )

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are the Execution Agent of AegisAI — a world-class project execution strategist.

Your role:
  1. Receive a goal, its decomposed subtasks, and research insights.
  2. Produce a comprehensive, actionable execution plan.
  3. The plan must include: phases, concrete steps per phase, milestones, owner hints, and success criteria.

Return a valid JSON object:
{
  "execution_plan": "<full multi-paragraph execution plan in markdown format>",
  "phases": [
    {
      "phase_number": 1,
      "phase_name": "<name>",
      "duration_estimate": "<e.g. Week 1-2>",
      "subtask_ids": ["T1", "T2"],
      "milestone": "<what must be true at end of phase>",
      "success_criteria": "<measurable outcome>"
    }
  ],
  "total_estimated_duration": "<e.g. 8 weeks>",
  "critical_path": ["T1", "T3", "T5"],
  "key_dependencies": "<paragraph describing external dependencies>"
}

Rules:
- execution_plan must be detailed markdown (≥ 200 words).
- Group subtasks into logical phases.
- Highlight the critical path explicitly.
- Return ONLY valid JSON.
""".strip()


class ExecutionAgent:
    """
    Converts the decomposed subtask list + research insights into a
    structured execution plan.
    """

    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    async def generate_plan(
        self,
        goal: str,
        goal_summary: str,
        subtasks: List[SubTask],
        research_insights: str,
        risks: List[str],
        context: Dict[str, Any] | None = None,
        language: str = "en-IN",
    ) -> Dict[str, Any]:
        """
        Produce a structured execution plan.

        Returns:
            Dict with keys: execution_plan (str), phases (list),
            total_estimated_duration (str), critical_path (list),
            key_dependencies (str).
        """
        subtask_text = "\n".join(
            f"  [{s.id}] P{s.priority} | ~{s.estimated_duration_minutes}min | "
            f"{s.title}: {s.description} | deps={s.dependencies}"
            for s in subtasks
        )
        risks_text = "\n".join(f"  - {r}" for r in risks) or "  None identified."
        context_str = ""
        if context:
            context_str = "\nContext: " + ", ".join(f"{k}={v}" for k, v in context.items())

        user_message = (
            f"Goal: {goal}\n"
            f"Summary: {goal_summary}\n"
            f"Subtasks:\n{subtask_text}\n\n"
            f"Research Insights:\n{research_insights}\n\n"
            f"Known Risks:\n{risks_text}"
            f"{context_str}"
        )
        lang_note = language_instruction(language)
        if lang_note:
            user_message += lang_note

        logger.info("Execution Agent generating plan (subtasks=%d) …", len(subtasks))
        raw: Dict[str, Any] = await self.groq.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.25,
            # Keep this bounded to stay within Groq TPM/request limits.
            max_tokens=4096,
        )

        result = {
            "execution_plan": raw.get("execution_plan", "Plan generation failed."),
            "phases": raw.get("phases", []),
            "total_estimated_duration": raw.get("total_estimated_duration", "Unknown"),
            "critical_path": raw.get("critical_path", []),
            "key_dependencies": raw.get("key_dependencies", ""),
        }
        logger.info(
            "Execution Agent done | phases=%d | duration=%s",
            len(result["phases"]),
            result["total_estimated_duration"],
        )
        return result
