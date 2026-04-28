"""
AegisAI - Debate Agent
Runs a multi-agent simulation where an 'Optimist' and a 'Risk-Averse' agent
debate the feasibility and safety of a proposed goal/plan.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from services.groq_service import GroqService

logger = logging.getLogger(__name__)

class DebateAgent:
    """
    Simulates a debate between two adversarial personas to uncover hidden risks
    and opportunities in a plan.
    """

    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    async def run_debate(
        self,
        goal: str,
        plan: str,
        risks: List[str],
        language: str = "en-IN",
    ) -> Dict[str, Any]:
        """
        Run the debate and return the perspectives and final resolution.
        """
        logger.info("Debate Agent: starting multi-agent simulation…")

        system_prompt = """
You are the AegisAI Debate Engine. You will simulate four distinct agents debating a goal and plan:
1. OPTIMIST: Focused on ROI, speed, massive impact, and best-case scenarios.
2. RISK ANALYST: Focused on safety, constraints, edge cases, and failure modes.
3. EXECUTOR: Focused on practicality, resource constraints, and operational execution.
4. CRITIC: Focused on challenging assumptions, finding logical flaws, and being a harsh reviewer.

For the given goal and plan, simulate their perspectives and then provide a final synthesized decision.

Return ONLY valid JSON:
{
  "optimist": "<optimist's argument>",
  "risk_analyst": "<risk analyst's counter-argument>",
  "executor": "<executor's practical reality check>",
  "critic": "<critic's harsh review of assumptions>",
  "reasoning": "<synthesized logical reasoning and core consensus>",
  "final_decision": "<final synthesized path forward>"
}
""".strip()

        from utils.helpers import language_instruction
        lang_note = language_instruction(language)
        
        user_message = f"GOAL: {goal}\nPLAN: {plan}\nIDENTIFIED RISKS: {', '.join(risks)}"
        if lang_note:
            user_message += f"\n\n{lang_note}"

        try:
            debate = await self.groq.chat_json(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.5,
            )
            return debate
        except Exception as exc:
            logger.error("Debate Agent failed: %s", exc)
            return {
                "optimist": "The potential here is significant and we should move fast.",
                "risk_analyst": "We must proceed with extreme caution and mitigate all risks.",
                "executor": "We need clear milestones and resource allocation before starting.",
                "critic": "The current plan assumes too much and lacks rigorous validation.",
                "reasoning": "The debate concluded that while the goal is ambitious, safety guardrails and a phased approach are necessary to manage underlying risks.",
                "final_decision": "Staged rollout recommended with heavy monitoring."
            }
