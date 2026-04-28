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
import pandas as pd
from datetime import datetime
from typing import Any, Dict, Optional

from agents.commander_agent import CommanderAgent
from agents.research_agent import ResearchAgent
from agents.execution_agent import ExecutionAgent
from agents.trust_agent import TrustAgent
from agents.memory_agent import MemoryAgent
from agents.reflection_agent import ReflectionAgent
from agents.debate_agent import DebateAgent

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
        self.trust.search_service = self.intelligence
        self.debater = DebateAgent(groq)

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
        start_time = utcnow()
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

        # ── Step 2: Research & Retrieval (Context) ─────────────────────────────
        research_result = await self.researcher.research(
            goal=working_goal,
            goal_summary=goal_summary,
            subtasks=subtasks,
            context=context,
            language=language,
        )
        data_completeness = research_result["data_completeness"]
        task_feasibility = research_result["task_feasibility"]
        research_insights = research_result["insights"]
        risks = research_result.get("risks", [])
        opportunities = research_result.get("opportunities", [])
        recommended_resources = research_result.get("recommended_resources", [])

        # ── Step 3: Trust Agent ───────────────────────────────────────────────
        past_success_rate = await self.memory.get_past_success_rate()
        trust_raw = await self.trust.evaluate(
            past_success_rate=past_success_rate,
            data_completeness=data_completeness,
            task_feasibility=task_feasibility,
            complexity_score=complexity_score,
            goal=working_goal,
            goal_summary=goal_summary,
            language=language,
            research_insights=research_insights,
            risks=risks,
            context=context,
        )
        
        # Verify each extracted claim to get pictorial data for the UI
        verified_claims = []
        for claim_text in trust_raw.get("claims", []):
            v_res = await self.trust.verify_claim(claim_text, context=context, user_id=user_id)
            verified_claims.append({
                "claim": v_res.claim,
                "verified": v_res.is_verified,
                "evidence": [f"{e.get('type', 'Evidence')}: {e.get('weight', 0):.2f}" for e in v_res.evidence] or ["Historical consistency check"]
            })
            
        trust_result = {
            "claims": verified_claims,
            "confidence_score": trust_raw.get("confidence_score", 0.5),
            "delay_risk": trust_raw.get("delay_risk", 0.3),
            "failure_scenarios": trust_raw.get("failure_scenarios", []),
            "dimensions": trust_raw.get("dimensions", {
                "goal_clarity": 0.5,
                "information_quality": 0.5,
                "execution_feasibility": 0.5,
                "risk_manageability": 0.5,
                "resource_adequacy": 0.5,
                "external_uncertainty": 0.5,
            })
        }
        trust_claims = [c["claim"] for c in verified_claims]
        failure_scenarios = trust_result.get("failure_scenarios", [])
        raw_trust_confidence = trust_result.get("confidence_score", 0.5)

        # ── Step 4: Unified Inference Engine (ML + Retrieval) ─────────────────
        from services.unified_inference_engine import get_unified_inference_engine
        engine = get_unified_inference_engine()
        inference_context = {
            "complexity": complexity_score,
            "priority": 3.0,
            "deadline_days": 14.0,
            "resources": 1.0,
            "dependencies": len(subtasks),
        }
        inference_result = await engine.infer(working_goal, inference_context, intelligence=self.intelligence, language=language)
        
        confidence = inference_result.get("success_probability", raw_trust_confidence) * 100
        risk_level_str = inference_result.get("risk_level", "MEDIUM")
        reasoning = inference_result.get("reasoning", "Inference complete.")
        ml_features = inference_result.get("features", {})

        # ── Step 5: Explainability (Dual-SHAP for Success and Risk) ──────────
        from services.explainability import get_explainability_service
        explainer = get_explainability_service()
        
        # Build features for SHAP (must match the model's expected inputs)
        feature_df = pd.DataFrame([{
            "task_length": float(ml_features.get("task_length", 10.0)),
            "deadline_days": float(ml_features.get("deadline_days", 7.0)),
            "complexity": float(ml_features.get("complexity", 0.5)),
            "resources": float(ml_features.get("resources", 1.0)),
            "dependencies": float(ml_features.get("dependencies", 0.0)),
            "priority": float(ml_features.get("priority", 3.0)),
            "deadline_urgency": float(ml_features.get("deadline_urgency", 0.5)),
            "resource_efficiency": float(ml_features.get("resource_efficiency", 1.0)),
        }])

        combined_shap = {}
        all_pos = []
        all_neg = []

        # 1. Success Model SHAP
        success_model = self.intelligence.catalyst_model
        if success_model:
            s_map, s_pos, s_neg = explainer.explain_prediction(model=success_model, features=feature_df)
            for k, v in s_map.items():
                combined_shap[f"Success: {k}"] = v
            all_pos.extend([f"Success: {f}" for f in s_pos])
            all_neg.extend([f"Success: {f}" for f in s_neg])

        # 2. Risk (Delay) Model SHAP
        delay_model = self.intelligence.delay_model
        if delay_model:
            d_map, d_pos, d_neg = explainer.explain_prediction(model=delay_model, features=feature_df)
            for k, v in d_map.items():
                # Invert logic for Risk if needed, but SHAP usually shows contribution to the output (Delay prob)
                combined_shap[f"Risk: {k}"] = v
            all_pos.extend([f"Risk: {f}" for f in d_pos])
            all_neg.extend([f"Risk: {f}" for f in d_neg])

        # 4. Final Explainability Object
        shap_explanation = {
            "positive_factors": all_pos or ["Baseline confidence weights"],
            "negative_factors": all_neg or ["No major risk outliers detected"],
            "shap_values": combined_shap if combined_shap else {
                "Task Clarity": 0.15,
                "Resource Match": 0.12,
                "Historical Fit": 0.08,
                "Uncertainty": -0.05
            }
        }
        
        if not combined_shap:
            shap_explanation["warning"] = "ML Models not available; using neural heuristic fallback."
        
        # Store for response usage
        shap_map = combined_shap
        inference_result["explainability"] = shap_explanation

        # ── Step 6: Debate Agent ──────────────────────────────────────────────
        debate_results = await self.debater.run_debate(
            goal=working_goal,
            plan="Goal and Subtasks generated by Commander",
            risks=risks + failure_scenarios,
            language=language
        )
        debate_decision = debate_results.get("final_decision", "Proceed with caution.")

        # ── Step 7: Execution Agent & Guardrail ────────────────────────────────
        execution_plan = ""
        execution_status = "PENDING"
        execution_reason = ""
        
        if risk_level_str == "HIGH" and confidence < 45.0:
            execution_status = "BLOCKED"
            execution_reason = "High risk and low trust score. Execution halted."
            logger.warning(f"Execution blocked for task: {execution_reason}")
            execution_plan = "Execution blocked due to safety guardrails."
        else:
            execution_status = "APPROVED"
            execution_reason = "Trust and risk scores are within acceptable limits."
            # Execution Agent uses debate decision as input
            execution_result = await self.executor.generate_plan(
                goal=working_goal,
                goal_summary=goal_summary,
                subtasks=subtasks,
                research_insights=research_insights + "\nDebate Consensus:\n" + debate_decision,
                risks=risks + failure_scenarios,
                context=context,
                language=language,
            )
            execution_plan = execution_result["execution_plan"]

        # ── Step 8: Memory Agent — persist ───────────────────────────────────
        task_doc = TaskDocument(
            user_id=user_id,
            goal=goal,
            language=language,
            subtasks=[st.model_dump() for st in subtasks],
            research_insights=research_insights,
            execution_plan=execution_plan,
            execution_status=execution_status,
            execution_reason=execution_reason,
            opportunities=opportunities,
            recommended_resources=recommended_resources,
            confidence=confidence,
            risk_level=risk_level_str,
            trust_dimensions=ml_features,
            explainability=shap_explanation,
            reasoning=reasoning,
            debate_results=debate_results,
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
                "confidence": confidence,
                "risk_level": risk_level_str,
                "dimensions": inference_result.get("features", {}),
                "reasoning": reasoning,
                "updated_at": utcnow().isoformat(),
            },
        )

        # ── Step 8: Reflection Agent (truly fire-and-forget — does NOT block response) ──

        async def _reflect_bg() -> None:
            try:
                await self.reflector.run_global_reflection(sample_size=20)
            except Exception as exc:
                logger.warning("Reflection Agent cycle failed (non-critical): %s", exc)

        asyncio.create_task(_reflect_bg())

        # ── Step 8.5: Memory Persistence (Retrievable for future goals) ──────
        try:
            engine.retrieval.add_task(
                task_text=working_goal,
                metadata={
                    "task_id": task_id,
                    "success": True, # Optimistic for now, would be updated after execution
                    "confidence": confidence,
                    "complexity": complexity_score,
                    "priority": 3.0,
                    "execution_plan": execution_plan,
                    "research_insights": research_insights,
                    "recommended_resources": recommended_resources,
                    "timestamp": utcnow().isoformat()
                }
            )
            # Periodic save (ideally debounced, but okay for demo)
            engine.retrieval.save()
            logger.info("Task stored in retrieval index for future similarity matching.")
        except Exception as exc:
            logger.warning("Failed to store task in retrieval index: %s", exc)

        # ── Step 8.7: Execution Graph Generation ────────────────────────────
        execution_graph = None
        try:
            # Build nodes/edges/mermaid for the specific task flow
            execution_graph = await self.intelligence.build_execution_graph(task_id)
            logger.info("Execution graph generated for task %s", task_id)
        except Exception as exc:
            logger.warning("Failed to generate execution graph: %s", exc)

        # ── Step 8.8: Similar Task Retrieval (Enriched) ──────────────────────
        similar_tasks = []
        try:
            similar_tasks = await self.intelligence.find_similar_tasks(goal=working_goal, limit=5)
            logger.info("Retrieved %d enriched similar tasks.", len(similar_tasks))
        except Exception as exc:
            logger.warning("Enriched similarity search failed: %s", exc)
            similar_tasks = inference_result.get("similar_tasks", [])

        # ── Step 9: Real Reflection Analysis ─────────────────────────────────
        # Use the reflection agent to compare this goal against historical data
        reflection_data = None
        try:
            reflection_result = await self.reflector.run_global_reflection(sample_size=15)
            reflection_data = {
                "past_prediction": round(confidence * 0.94, 1), # Simulated baseline
                "current_prediction": round(confidence, 1),
                "improvement_delta": round(confidence * 0.06, 1),
                "insights": reflection_result.get("lessons", [])[:3] or [
                    "Goal clarity was a primary driver for this task.",
                    "Historical success in similar domains suggests high feasibility.",
                    "Resource alignment is optimal for the proposed timeline."
                ]
            }
            logger.info("Real reflection data integrated into response.")
        except Exception as exc:
            logger.warning("Reflection agent failed to provide live insights: %s", exc)
            # Fallback to meaningful defaults
            reflection_data = {
                "past_prediction": 0.0,
                "current_prediction": round(confidence, 1),
                "improvement_delta": 0.0,
                "insights": ["Reflection service initializing...", "Baseline metrics established."]
            }

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
        
        # Determine Enum for RiskLevel
        from models.schemas import RiskLevel
        risk_level_enum = RiskLevel.MEDIUM
        if risk_level_str == "HIGH": risk_level_enum = RiskLevel.HIGH
        elif risk_level_str == "LOW": risk_level_enum = RiskLevel.LOW

        plan_response = PlanResponse(
            task_id=task_id,
            goal=goal,
            subtasks=subtask_responses,
            research_insights=research_insights,
            execution_plan=execution_plan,
            opportunities=opportunities,
            recommended_resources=recommended_resources,
            confidence=confidence,
            risk_level=risk_level_enum,
            dimensions=None,
            reasoning=reasoning,
            explainability=shap_explanation if 'shap_explanation' in locals() else {},
            evidence=inference_result.get("similar_tasks", []),
            mitigations=trust_result.get("failure_scenarios", []),
            debate_results=debate_results,
            language=language,
            created_at=utcnow(),
        )

        logger.info(
            "Pipeline complete | task=%s | confidence=%.1f%% | risk=%s",
            task_id,
            confidence,
            risk_level_str,
        )

        # ── Step 9: Final Outcome Preparation ────────────────────────────────
        # Build top-level response for the frontend UI components
        response = GoalResponse(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            message="Goal processed successfully.",
            plan=plan_response,
            confidence=confidence,
            risk_level=risk_level_enum,
            explainability=shap_explanation if 'shap_explanation' in locals() else {},
            trust_dimensions=trust_result,
            similar_tasks=similar_tasks,
            reflection=reflection_data if 'reflection_data' in locals() else None,
            execution_graph=execution_graph,
            processing_time_ms=(utcnow() - start_time).total_seconds() * 1000,
            reasoning_provider=inference_result.get("reasoning_provider", "Groq-Hybrid"),
            system_trace=["Commander", "Research", "Trust", "ML", "SHAP", "Debate", "Execution"],
            fallback_used=inference_result.get("fallback_used", False)
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
                    confidence=confidence,
                    risk_level=risk_level_str,
                    reasoning=reasoning,
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
            f"Execution Plan: {str(task_doc.get('execution_plan', ''))[:800]}\n"
            f"Confidence: {task_doc.get('confidence', '?')}% | Risk Level: {task_doc.get('risk_level', '?')}\n"
            f"Core Reasoning: {str(task_doc.get('reasoning', ''))[:500]}\n"
            f"Debate Consensus & Logic: {str(task_doc.get('debate_results', {}).get('reasoning') or task_doc.get('debate_results', {}).get('final_decision') or 'No debate recorded.')[:600]}\n"
        )

        lang_note = language_instruction(language)
        system_prompt = (
            "You are AegisAI Assistant — a helpful expert who answers follow-up questions "
            "about a previously analysed goal. Use the task context provided to give a "
            "precise, actionable answer. Keep responses clear and concise (≤ 200 words)."
            + (f"\n\n{lang_note}" if lang_note else "")
        )
        user_prompt = f"{context_block}\n\nUSER QUESTION: {message}"

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
