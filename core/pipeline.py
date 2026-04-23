"""
AegisAI - Core Pipeline Orchestrator
Coordinates all six agents in the correct sequence for a single goal submission.

Pipeline:
    1. CommanderAgent  → decompose goal into subtasks
    2. ResearchAgent   → gather insights, feasibility & data-completeness scores
    3. ExecutionAgent  → generate actionable execution plan
    4. TrustAgent      → calculate confidence score & risk level
    5. MemoryAgent     → persist task document + cache confidence
    6. ReflectionAgent → (async, non-blocking) reflect on recent history
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from agents.commander_agent import CommanderAgent
from agents.research_agent import ResearchAgent
from agents.execution_agent import ExecutionAgent
from agents.trust_agent import TrustAgent
from agents.memory_agent import MemoryAgent
from agents.reflection_agent import ReflectionAgent

from services.groq_service import GroqService
from services.sarvam_service import SarvamService
from services.mongodb_service import MongoDBService
from services.redis_service import RedisService
from services.intelligence_service import IntelligenceService

from models.schemas import (
    GoalRequest,
    GoalResponse,
    PlanResponse,
    SubTaskResponse,
    TaskDocument,
    TaskStatus,
)
from utils.helpers import sanitise_goal, utcnow

logger = logging.getLogger(__name__)


async def get_database():
    """FastAPI dependency: return the shared MongoDB database instance."""
    from services.mongodb_service import get_mongodb_service

    return get_mongodb_service().db


class AegisAIPipeline:
    """
    Top-level orchestrator that wires together all AegisAI agents.
    Instantiated once at application startup and injected into FastAPI routes.
    """

    def __init__(
        self,
        groq: GroqService,
        sarvam: SarvamService,
        mongo: MongoDBService,
        redis: RedisService,
    ) -> None:
        self.sarvam = sarvam

        # Agent instances
        self.commander = CommanderAgent(groq)
        self.researcher = ResearchAgent(groq)
        self.executor = ExecutionAgent(groq)
        self.trust = TrustAgent(groq)
        self.memory = MemoryAgent(mongo, redis)
        self.reflector = ReflectionAgent(groq, self.memory)
        self.intelligence = IntelligenceService(mongo, self.memory, self.reflector)

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════

    async def _generate_spoken_summary(
        self,
        goal_summary: str,
        subtask_count: int,
        subtask_titles: list,
        research_insights: str,
        execution_plan: str,
        confidence: float,
        risk_level: str,
        reasoning: str,
        language: str = "en-IN",
    ) -> tuple[str, str]:
        """
        Generate a concise spoken summary and return ``(text, effective_language)``.

        ``effective_language`` is the language code that should be passed to TTS —
        normally the same as ``language``, but falls back to ``en-IN`` when the
        Sarvam translation step fails so TTS still receives correctly-languaged text.

        Strategy:
        - English / Hindi: Groq generates natively (Llama handles both well).
        - All other Indian scripts (Bengali, Tamil, Punjabi, etc.):
          Groq generates in English → Sarvam translate → TTS.
          This avoids Romanised or mixed output from the LLM.

        The output is plain flowing prose (no bullet points, no markdown),
        suitable for text-to-speech and under 400 words / ~2000 characters.
        """
        import re
        from utils.helpers import get_language_name

        # Languages where Llama reliably generates native-script text.
        # All other languages are generated in English then translated by Sarvam.
        _GROQ_NATIVE_LANGS = {"en-IN", "hi-IN"}
        generate_lang = language if language in _GROQ_NATIVE_LANGS else "en-IN"
        lang_name = get_language_name(generate_lang)

        system_prompt = (
            "You are AegisAI's voice narrator. Your job is to deliver a clear, "
            "natural spoken summary of a goal-analysis report prepared by six "
            "specialised AI agents. "
            "Rules:\n"
            "1. Write ONLY in flowing spoken prose. No bullet points, no headers, "
            "no markdown, no numbered lists.\n"
            "2. Keep the total length between 200 and 350 words — this will be "
            "spoken aloud and must be concise.\n"
            "3. Cover the crux only: what the goal is, the key research finding, "
            "the top 2-3 action steps from the execution plan, the confidence "
            "level with what it means for the user, and one clear recommendation.\n"
            "4. Sound like a knowledgeable advisor briefing someone verbally — "
            "warm, direct, and actionable.\n"
            f"5. Write ENTIRELY in {lang_name}. Every word must be in {lang_name}."
        )

        subtask_sample = ", ".join(subtask_titles[:4]) if subtask_titles else "none"

        user_prompt = (
            f"GOAL: {goal_summary}\n\n"
            f"NUMBER OF SUBTASKS: {subtask_count} (sample: {subtask_sample})\n\n"
            f"RESEARCH INSIGHTS:\n{research_insights[:800]}\n\n"
            f"EXECUTION PLAN:\n{execution_plan[:800]}\n\n"
            f"CONFIDENCE: {confidence:.0f}%   RISK LEVEL: {risk_level}\n\n"
            f"TRUST REASONING:\n{reasoning[:500]}\n\n"
            "Now produce the spoken summary."
        )

        try:
            summary = await self.commander.groq.chat(
                system_prompt=system_prompt,
                user_message=user_prompt,
                temperature=0.5,
            )
            # Strip any stray markdown the LLM might add
            summary = re.sub(r"[#*_`]+", "", summary).strip()

            # Translate from English to the target regional language via Sarvam
            if generate_lang != language:
                try:
                    summary = await self.sarvam.translate(
                        text=summary,
                        source_language_code="en-IN",
                        target_language_code=language,
                    )
                    logger.info(
                        "Spoken summary translated en-IN → %s | chars=%d",
                        language, len(summary),
                    )
                    return summary, language
                except Exception as trans_exc:
                    logger.warning(
                        "Spoken summary translate en-IN → %s failed (%s); "
                        "delivering English audio instead.",
                        language, trans_exc,
                    )
                    # summary stays in English — return en-IN so TTS language matches
                    return summary, "en-IN"

            return summary, language

        except Exception as exc:
            logger.warning("Spoken summary generation failed (%s); using fallback.", exc)
            # Minimal safe English fallback — always safe for TTS
            return (
                f"Goal analysed: {goal_summary}. "
                f"{subtask_count} subtasks identified. "
                f"Confidence: {confidence:.0f} percent. Risk: {risk_level}. "
                f"{reasoning[:300]}",
                "en-IN",
            )

    # ══════════════════════════════════════════════════════════════════════════
    # Main entry point: process a text-based goal
    # ══════════════════════════════════════════════════════════════════════════

    async def process_goal(
        self,
        request: GoalRequest,
        _skip_report_tts: bool = False,
        user_id: Optional[str] = None,
    ) -> GoalResponse:
        """
        Execute the full AegisAI pipeline for a text goal.

        Returns:
            GoalResponse with task_id, plan, confidence, risk_level, and reasoning.
        """
        goal = sanitise_goal(request.goal)
        language = request.language.value
        context = request.context or {}

        logger.info("Pipeline: starting goal processing | lang=%s | len=%d", language, len(goal))

        # ── If the goal is in a non-English language, translate first ──────────
        working_goal = goal
        if language != "en-IN":
            try:
                working_goal = await self.sarvam.translate(
                    text=goal,
                    source_language_code=language,
                    target_language_code="en-IN",
                )
                logger.info("Pipeline: goal translated %s → en-IN", language)
            except Exception as exc:
                logger.warning("Translation failed (%s), proceeding in original language.", exc)
                working_goal = goal

        # ── Step 1: Commander Agent ───────────────────────────────────────────
        commander_result = await self.commander.decompose(working_goal, context, language)
        subtasks = commander_result["subtasks"]
        goal_summary = commander_result["goal_summary"]
        complexity_score = commander_result["complexity_score"]

        # ── Step 2: Research Agent ────────────────────────────────────────────
        research_result = await self.researcher.research(
            goal=working_goal,
            goal_summary=goal_summary,
            subtasks=subtasks,
            context=context,            language=language,        )
        data_completeness = research_result["data_completeness"]
        task_feasibility = research_result["task_feasibility"]
        research_insights = research_result["insights"]
        risks = research_result.get("risks", [])
        opportunities = research_result.get("opportunities", [])
        recommended_resources = research_result.get("recommended_resources", [])

        # ── Step 3: Execution Agent ───────────────────────────────────────────
        execution_result = await self.executor.generate_plan(
            goal=working_goal,
            goal_summary=goal_summary,
            subtasks=subtasks,
            research_insights=research_insights,
            risks=risks,
            context=context,            language=language,        )
        execution_plan = execution_result["execution_plan"]

        # ── Step 4: Trust Agent ───────────────────────────────────────────────
        past_success_rate = await self.memory.get_past_success_rate()
        trust_score = await self.trust.evaluate(
            past_success_rate=past_success_rate,
            data_completeness=data_completeness,
            task_feasibility=task_feasibility,
            complexity_score=complexity_score,
            goal=working_goal,
            goal_summary=goal_summary,
            language=language,
            research_insights=research_insights,
            execution_plan=execution_plan,
            risks=risks,
            context=context,
        )

        # ── Step 5: Memory Agent — persist ───────────────────────────────────
        task_doc = TaskDocument(
            user_id=user_id,
            goal=goal,
            language=language,
            subtasks=[st.model_dump() for st in subtasks],
            research_insights=research_insights,
            execution_plan=execution_plan,
            opportunities=opportunities,
            recommended_resources=recommended_resources,
            confidence=trust_score.confidence,
            risk_level=trust_score.risk_level.value,
            trust_components=trust_score.components.model_dump(),
            reasoning=trust_score.reasoning,
            status=TaskStatus.IN_PROGRESS.value,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        task_id = await self.memory.create_task(task_doc)

        # Cache confidence in Redis
        await self.memory.cache_confidence(
            task_id,
            {
                "task_id": task_id,
                "confidence": trust_score.confidence,
                "risk_level": trust_score.risk_level.value,
                "components": trust_score.components.model_dump(),
                "reasoning": trust_score.reasoning,
                "updated_at": utcnow().isoformat(),
            },
        )

        # ── Step 6: Reflection Agent (truly fire-and-forget — does NOT block response) ──

        async def _reflect_bg() -> None:
            try:
                await self.reflector.run_global_reflection(sample_size=20)
            except Exception as exc:
                logger.warning("Reflection Agent cycle failed (non-critical): %s", exc)

        asyncio.create_task(_reflect_bg())

        # ── Build response ────────────────────────────────────────────────────
        subtask_responses = [
            SubTaskResponse(
                id=st.id,
                title=st.title,
                description=st.description,
                priority=st.priority,
                estimated_duration_minutes=st.estimated_duration_minutes,
                dependencies=st.dependencies,
            )
            for st in subtasks
        ]

        plan_response = PlanResponse(
            task_id=task_id,
            goal=goal,
            subtasks=subtask_responses,
            research_insights=research_insights,
            execution_plan=execution_plan,
            opportunities=opportunities,
            recommended_resources=recommended_resources,
            confidence=trust_score.confidence,
            risk_level=trust_score.risk_level,
            components=trust_score.components,
            reasoning=trust_score.reasoning,
            language=language,
            created_at=utcnow(),
        )

        logger.info(
            "Pipeline complete | task=%s | confidence=%.1f%% | risk=%s",
            task_id,
            trust_score.confidence,
            trust_score.risk_level.value,
        )

        response = GoalResponse(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            message="Goal processed successfully.",
            plan=plan_response,
        )

        # ── Auto-TTS: generate and speak the AI-summarised crux of all agents' outputs ──
        spoken_summary = ""
        if not _skip_report_tts:
            try:
                spoken_summary, tts_lang = await self._generate_spoken_summary(
                    goal_summary=goal_summary,
                    subtask_count=len(subtasks),
                    subtask_titles=[st.title for st in subtasks],
                    research_insights=research_insights,
                    execution_plan=execution_plan,
                    confidence=trust_score.confidence,
                    risk_level=trust_score.risk_level.value,
                    reasoning=trust_score.reasoning,
                    language=language,
                )
                audio_b64 = await self.sarvam.text_to_speech(
                    text=spoken_summary[:2500],
                    language_code=tts_lang,
                )
                response.audio_response_base64 = audio_b64
                logger.info(
                    "Pipeline: spoken summary TTS generated | lang=%s | tts_lang=%s | words=%d",
                    language, tts_lang, len(spoken_summary.split()),
                )
            except Exception as exc:
                logger.warning("Auto-TTS (spoken summary) failed (non-critical): %s", exc)

        # Attach spoken summary text to plan so frontend can display it
        if response.plan:
            response.plan.spoken_summary = spoken_summary

        return response

    # ══════════════════════════════════════════════════════════════════════════
    # Voice pipeline
    # ══════════════════════════════════════════════════════════════════════════

    async def process_voice_goal(
        self,
        audio_base64: str,
        language: str = "en-IN",
        audio_format: str = "webm",
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> GoalResponse:
        """
        Full voice pipeline:
          Audio → Sarvam STT → text → AegisAI reasoning → Sarvam TTS audio response.
        """
        # Sarvam STT
        logger.info("Voice pipeline: starting STT | lang=%s", language)
        transcribed_text = await self.sarvam.speech_to_text_base64(
            audio_base64=audio_base64,
            language_code=language,
            audio_format=audio_format,
        )
        if not transcribed_text.strip():
            raise ValueError("Could not transcribe audio. Please try again with clearer audio.")

        logger.info("Voice pipeline: STT produced %d chars", len(transcribed_text))

        # Build a GoalRequest and run the standard pipeline
        from models.schemas import GoalRequest, InputModality, SupportedLanguage
        lang_enum = SupportedLanguage(language) if language in [e.value for e in SupportedLanguage] else SupportedLanguage.EN
        goal_request = GoalRequest(
            goal=transcribed_text,
            language=lang_enum,
            context=context,
            modality=InputModality.VOICE,
        )
        response = await self.process_goal(goal_request, _skip_report_tts=True, user_id=user_id)

        # Sarvam TTS -- AI-generated spoken summary of the full report
        if response.plan:
            try:
                spoken_summary, tts_lang = await self._generate_spoken_summary(
                    goal_summary=response.plan.goal,
                    subtask_count=len(response.plan.subtasks),
                    subtask_titles=[st.title for st in response.plan.subtasks],
                    research_insights=response.plan.research_insights,
                    execution_plan=response.plan.execution_plan,
                    confidence=response.plan.confidence,
                    risk_level=response.plan.risk_level.value,
                    reasoning=response.plan.reasoning,
                    language=language,
                )
                response.plan.spoken_summary = spoken_summary
                audio_b64 = await self.sarvam.text_to_speech(
                    text=spoken_summary[:2500],
                    language_code=tts_lang,
                )
                response.audio_response_base64 = audio_b64
                logger.info(
                    "Voice pipeline: spoken summary TTS generated | lang=%s | tts_lang=%s",
                    language, tts_lang,
                )
            except Exception as exc:
                logger.warning("TTS generation failed (non-critical): %s", exc)

        return response

    # ══════════════════════════════════════════════════════════════════════════
    # Outcome recording
    # ══════════════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════════════
    # Follow-up: interactive Q&A on an existing task
    # ══════════════════════════════════════════════════════════════════════════

    async def process_followup(
        self,
        task_id: str,
        message: str,
        language: str = "en-IN",
        audio_base64: Optional[str] = None,
        audio_format: str = "webm",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle a follow-up question or voice message about an existing task.
        Loads full task context from memory, runs a single Groq call,
        responds in the user's language, and optionally generates TTS audio.
        """
        from utils.helpers import language_instruction

        # Transcribe voice if provided
        user_text = message
        if audio_base64:
            try:
                user_text = await self.sarvam.speech_to_text_base64(
                    audio_base64=audio_base64,
                    language_code=language,
                    audio_format=audio_format,
                )
                logger.info("Follow-up STT produced: %d chars", len(user_text))
            except Exception as exc:
                logger.warning("Follow-up STT failed: %s — using text message.", exc)

        # Load task context from memory
        task_doc = await self.memory.get_task(task_id, user_id=user_id)
        if not task_doc:
            return {
                "reply": "Task not found. Please check the task ID.",
                "audio_base64": None,
            }

        context_block = (
            f"TASK CONTEXT:\n"
            f"Goal: {task_doc.get('goal', '')}\n"
            f"Execution Plan (summary): {str(task_doc.get('execution_plan', ''))[:600]}\n"
            f"Confidence: {task_doc.get('confidence', '?')}%  Risk: {task_doc.get('risk_level', '?')}\n"
            f"Reasoning: {str(task_doc.get('reasoning', ''))[:400]}\n"
        )

        lang_note = language_instruction(language)
        system_prompt = (
            "You are AegisAI Assistant — a helpful expert who answers follow-up questions "
            "about a previously analysed goal. Use the task context provided to give a "
            "precise, actionable answer. Keep responses clear and concise (≤ 200 words)."
            + (f"\n\n{lang_note}" if lang_note else "")
        )
        user_prompt = f"{context_block}\n\nUSER QUESTION: {user_text}"

        groq_svc = self.commander.groq  # reuse shared groq client
        try:
            reply = await groq_svc.chat(
                system_prompt=system_prompt,
                user_message=user_prompt,
                temperature=0.4,
            )
        except Exception as exc:
            logger.error("Follow-up Groq call failed: %s", exc)
            reply = "Sorry, I could not process your follow-up question. Please try again."

        # Auto-TTS the reply
        audio_out = None
        try:
            audio_out = await self.sarvam.text_to_speech(
                text=reply[:500],
                language_code=language,
            )
        except Exception as exc:
            logger.warning("Follow-up TTS failed (non-critical): %s", exc)

        return {"reply": reply, "audio_base64": audio_out}

    # ══════════════════════════════════════════════════════════════════════════
    # Outcome recording
    # ══════════════════════════════════════════════════════════════════════════

    async def record_outcome(
        self,
        task_id: str,
        status: TaskStatus,
        outcome_notes: Optional[str] = None,
        actual_duration_minutes: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Record the final outcome for a task and trigger a per-task reflection."""
        success = await self.memory.record_outcome(
            task_id=task_id,
            status=status,
            outcome_notes=outcome_notes,
            actual_duration_minutes=actual_duration_minutes,
            user_id=user_id,
        )
        if success:
            task_doc = await self.memory.get_task(task_id, user_id=user_id)
            prev_confidence = float(task_doc.get("confidence", 50.0)) if task_doc else 50.0
            try:
                await self.reflector.reflect_on_task(
                    task_id=task_id,
                    previous_confidence=prev_confidence,
                    outcome_status=status.value,
                    outcome_notes=outcome_notes,
                )
            except Exception as exc:
                logger.warning("Per-task reflection failed (non-critical): %s", exc)
        return success
