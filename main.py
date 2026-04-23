"""
AegisAI - FastAPI Application Entry Point
Wires together all services, agents, and routers with proper lifespan management.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from services.groq_service import get_groq_service
from services.sarvam_service import get_sarvam_service
from services.mongodb_service import get_mongodb_service
from services.pinecone_service import initialize_pinecone, shutdown_pinecone
from services.redis_service import get_redis_service
from core.pipeline import AegisAIPipeline

settings = get_settings()

# ── Logging configuration ─────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aegisai")

# ── Singleton pipeline reference ──────────────────────────────────────────────

_pipeline: AegisAIPipeline | None = None
_intelligence_scheduler_task: asyncio.Task[None] | None = None


def get_pipeline() -> AegisAIPipeline:
    """FastAPI dependency: returns the shared AegisAIPipeline instance."""
    if _pipeline is None:
        raise RuntimeError("AegisAI pipeline not initialised. Check app startup.")
    return _pipeline


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Startup: connect services, initialise pipeline.
    Shutdown: gracefully close all connections.
    """
    global _pipeline, _intelligence_scheduler_task

    logger.info("=" * 60)
    logger.info("  %s v%s  — starting up …", settings.APP_NAME, settings.APP_VERSION)
    logger.info("=" * 60)

    # ── Connect data stores ───────────────────────────────────────────────────
    mongo = get_mongodb_service()
    redis = get_redis_service()

    await mongo.connect()
    await redis.connect()
    await initialize_pinecone()

    # ── Initialise service singletons ─────────────────────────────────────────
    groq = get_groq_service()
    sarvam = get_sarvam_service()

    # ── Build the shared pipeline ─────────────────────────────────────────────
    _pipeline = AegisAIPipeline(
        groq=groq,
        sarvam=sarvam,
        mongo=mongo,
        redis=redis,
    )

    async def _scheduled_reflection_reports() -> None:
        interval_seconds = max(1, settings.INTELLIGENCE_REFLECTION_INTERVAL_HOURS) * 3600
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                if _pipeline is not None:
                    await _pipeline.intelligence.ensure_scheduled_report()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Scheduled reflection report failed: %s", exc)

    _intelligence_scheduler_task = asyncio.create_task(_scheduled_reflection_reports())

    logger.info("AegisAI pipeline ready. All agents initialised.")
    logger.info("=" * 60)

    yield  # ── Application running ───────────────────────────────────────────

    # ── Teardown ──────────────────────────────────────────────────────────────
    logger.info("AegisAI shutting down …")
    if _intelligence_scheduler_task is not None:
        _intelligence_scheduler_task.cancel()
        try:
            await _intelligence_scheduler_task
        except asyncio.CancelledError:
            pass
    await redis.close()
    await mongo.close()
    await shutdown_pinecone()
    logger.info("All connections closed. Goodbye.")


# ── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**AegisAI** — Trust-Aware Autonomous Multi-Agent Decision System.\n\n"
        "Accepts goals via text or voice, decomposes them into actionable plans, "
        "evaluates feasibility, assigns confidence scores, stores outcomes, "
        "learns from past executions, and supports multilingual interaction.\n\n"
        "### Pipeline\n"
        "```\n"
        "User Goal (text/voice)\n"
        "  → [Sarvam STT]          – voice transcription\n"
        "  → [Commander Agent]     – goal decomposition\n"
        "  → [Research Agent]      – contextual insights\n"
        "  → [Execution Agent]     – actionable plan\n"
        "  → [Trust Agent]         – confidence score + risk level\n"
        "  → [Memory Agent]        – MongoDB + Redis persistence\n"
        "  → [Reflection Agent]    – continuous learning\n"
        "  → Response [Sarvam TTS] – voice output (optional)\n"
        "```\n\n"
        "### Trust Formula\n"
        "`confidence = (goal_clarity × 0.15) + (information_quality × 0.20) "
        "+ (execution_feasibility × 0.25) + (risk_manageability × 0.15) + "
        "(resource_adequacy × 0.15) + (external_uncertainty × 0.10)`\n"
        "Risk: HIGH (<45), MEDIUM (<72), LOW (>=72)."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS middleware ───────────────────────────────────────────────────────────

cors_origins = [
    "http://localhost:3000",      # Frontend dev server (Vite)
    "http://localhost:8000",      # Backend served frontend
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]
if settings.FRONTEND_URL:
    cors_origins.extend(
        [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request timing middleware ─────────────────────────────────────────────────

_PIPELINE_TIMEOUT_SECONDS = 90  # hard ceiling: /goal may call Groq 5× sequentially

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    # Apply a generous but finite timeout to every pipeline request.
    # Static assets and health checks resolve instantly so they won't hit this.
    try:
        response = await asyncio.wait_for(
            call_next(request),
            timeout=_PIPELINE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        process_time = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Request timeout after %.0fs | %s %s",
            _PIPELINE_TIMEOUT_SECONDS, request.method, request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "detail": (
                    f"The pipeline took longer than {_PIPELINE_TIMEOUT_SECONDS}s to respond. "
                    "This usually means the AI rate-limit quota is exhausted. "
                    "Please wait a few minutes and try again."
                )
            },
            headers={"X-Process-Time-Ms": f"{process_time:.2f}"},
        )
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred.", "error": str(exc)},
    )


# ── Register routers ──────────────────────────────────────────────────────────

from routers.auth import router as auth_router
from routers.goal_router import router as goal_router
from routers.plan_router import router as plan_router
from routers.confidence_router import router as confidence_router
from routers.analytics_router import router as analytics_router
from routers.intelligence_router import router as intelligence_router
from routers.recommendations_router import router as recommendations_router
from routers.search_router import router as search_router
from routers.batch_router import router as batch_router
from routers.security_router import router as security_router
from routers.webhooks_router import router as webhooks_router
from routers.monitoring_router import router as monitoring_router
from routers.websocket_router import router as websocket_router

app.include_router(auth_router)
app.include_router(goal_router)
app.include_router(plan_router)
app.include_router(confidence_router)
app.include_router(analytics_router)
app.include_router(intelligence_router)
app.include_router(recommendations_router)
app.include_router(search_router)
app.include_router(batch_router)
app.include_router(security_router)
app.include_router(webhooks_router)
app.include_router(monitoring_router)
app.include_router(websocket_router)

# ── Frontend static files and SPA routing ────────────────────────────────────

_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
_index_path = os.path.join(_frontend_dir, "index.html")

# Mount static assets (CSS, JS, etc. from dist/assets)
if os.path.isdir(_frontend_dir):
    assets_dir = os.path.join(_frontend_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/ui", tags=["System"], summary="AegisAI Web Dashboard", include_in_schema=False)
async def serve_ui():
    """Serve the AegisAI single-page frontend application at /ui."""
    if not os.path.isfile(_index_path):
        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend not built. Run 'npm run build' in frontend directory."},
        )
    return FileResponse(_index_path, media_type="text/html")


# ── Health & system routes ────────────────────────────────────────────────────

@app.get("/", tags=["System"], summary="Root - system info / frontend", include_in_schema=False)
async def root(request: Request):
    """
    Root endpoint: serves frontend for browser requests, API info for API requests.
    Detects request type via Accept header.
    """
    accept_header = request.headers.get("accept", "").lower()

    # If browser is requesting HTML, serve the frontend
    if "text/html" in accept_header or "application/xhtml" in accept_header:
        if os.path.isfile(_index_path):
            return FileResponse(_index_path, media_type="text/html")
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "Frontend not available."},
            )

    # Otherwise return API info
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "submit_goal": "POST /goal",
            "submit_voice_goal": "POST /goal/voice",
            "record_outcome": "PUT /goal/outcome",
            "get_plan": "GET /plan/{task_id}",
            "list_plans": "GET /plan/",
            "translate_plan": "GET /plan/{task_id}/translate",
            "get_confidence": "GET /confidence/{task_id}",
            "confidence_components": "GET /confidence/{task_id}/components",
            "confidence_stats": "GET /confidence/stats/summary",
            "refresh_confidence": "POST /confidence/{task_id}/refresh",
            "intelligence_overview": "GET /intelligence/overview",
            "intelligence_graph": "GET /intelligence/graph/{task_id}",
            "intelligence_predict": "POST /intelligence/predict",
            "intelligence_simulate": "POST /intelligence/simulate",
        },
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    from services.mongodb_service import get_mongodb_service as _mongo
    from services.redis_service import get_redis_service as _redis

    mongo_ok = False
    redis_ok = False

    try:
        m = _mongo()
        await m.db.command("ping")
        mongo_ok = True
    except Exception:
        pass

    try:
        r = _redis()
        redis_ok = r.is_connected
    except Exception:
        redis_ok = False

    # Redis is optional — system is healthy as long as MongoDB is up
    return JSONResponse(
        status_code=status.HTTP_200_OK if mongo_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if mongo_ok else "degraded",
            "mongodb": "connected" if mongo_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected (optional)",
        },
    )


@app.get("/agents", tags=["System"], summary="List all agents and their roles")
async def list_agents():
    return {
        "agents": [
            {
                "name": "CommanderAgent",
                "role": "Goal decomposition",
                "description": "Breaks user goals into ordered, prioritised subtasks with dependency mapping.",
            },
            {
                "name": "ResearchAgent",
                "role": "Contextual intelligence",
                "description": "Gathers domain insights, feasibility signals, and data completeness scores using Groq LLM.",
            },
            {
                "name": "ExecutionAgent",
                "role": "Plan generation",
                "description": "Synthesises subtasks and research insights into a phased, milestone-driven execution plan.",
            },
            {
                "name": "TrustAgent",
                "role": "Confidence scoring",
                "description": "Performs a six-dimension holistic trust evaluation to calculate confidence (0-100) and risk level.",
            },
            {
                "name": "MemoryAgent",
                "role": "Persistence (MongoDB + Redis)",
                "description": "Long-term storage in MongoDB; short-term context caching in Redis with TTL.",
            },
            {
                "name": "ReflectionAgent",
                "role": "Continuous learning",
                "description": "Analyses past outcomes to surface patterns, lessons, and calibration recommendations.",
            },
        ]
    }


# ── SPA Fallback: serve index.html for all unmatched frontend routes ──────────

@app.get("/{path_name:path}", include_in_schema=False)
async def spa_fallback(request: Request, path_name: str):
    """
    Catch-all route: serves index.html for any route not handled by API endpoints.
    This allows React Router to handle client-side routing (e.g., /login, /register, /dashboard).
    """
    # Skip if path looks like an API endpoint or known non-SPA route
    if path_name.startswith(("api/", "docs", "redoc", "openapi")):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    # Serve index.html for all other routes
    if os.path.isfile(_index_path):
        return FileResponse(_index_path, media_type="text/html")
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend not available."},
    )


    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend not available"},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
