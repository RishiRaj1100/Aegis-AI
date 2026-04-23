# AegisAI

**Trust-Aware Autonomous Multi-Agent Decision System**

AegisAI accepts user goals via text or voice, decomposes them into actionable plans, evaluates feasibility, assigns a confidence score, stores outcomes, and learns from past executions — with full multilingual support.

The current build also includes an Intelligence Lab for execution graphs, similar-task retrieval, outcome prediction, simulation, workflow parsing, drift reports, and model registry actions.

---

## Architecture

```
User Goal (text / voice)
        │
        ▼
┌───────────────────┐
│  Sarvam STT       │  ← voice input transcription
└────────┬──────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                   AegisAI Pipeline                      │
│                                                         │
│  1. Commander Agent  → Goal decomposition into subtasks │
│  2. Research Agent   → Contextual insights + feasibility│
│  3. Execution Agent  → Actionable execution plan        │
│  4. Trust Agent      → Confidence (0–100) + Risk Level  │
│  5. Memory Agent     → MongoDB (long) + Redis (short)   │
│  6. Reflection Agent → Learn from past outcomes         │
└───────────────────────────────┬─────────────────────────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │  Sarvam TTS      │  ← voice output
                     └──────────────────┘
```

### Trust Formula

```
confidence =
  ( goal_clarity         × 0.15 ) +
  ( information_quality  × 0.20 ) +
  ( execution_feasibility× 0.25 ) +
  ( risk_manageability   × 0.15 ) +
  ( resource_adequacy    × 0.15 ) +
  ( external_uncertainty × 0.10 )

Final score scaled to 0–100.
Risk Level: HIGH (<45) | MEDIUM (45–71.9) | LOW (≥72)
```

---

## Project Structure

```
AegisAI/
├── main.py                     # FastAPI app entry point
├── requirements.txt
├── .env.example                # Environment variable template
│
├── config/
│   └── settings.py             # Pydantic BaseSettings
│
├── models/
│   └── schemas.py              # All Pydantic request/response/DB models
│
├── core/
│   └── pipeline.py             # Master orchestrator — coordinates all agents
│
├── agents/
│   ├── commander_agent.py      # Goal → subtask decomposition
│   ├── research_agent.py       # Contextual intelligence
│   ├── execution_agent.py      # Execution plan generation
│   ├── trust_agent.py          # Confidence scoring + risk level
│   ├── memory_agent.py         # MongoDB + Redis persistence facade
│   └── reflection_agent.py     # Continuous learning from outcomes
│
├── services/
│   ├── groq_service.py         # Groq LLM async wrapper
│   ├── sarvam_service.py       # Sarvam AI: STT / TTS / Translation
│   ├── mongodb_service.py      # Async Motor (MongoDB) client
│   └── redis_service.py        # Async Redis client
│
├── routers/
│   ├── goal_router.py          # POST /goal, POST /goal/voice, PUT /goal/outcome
│   ├── plan_router.py          # GET /plan/{id}, list, translate
│   ├── confidence_router.py    # GET /confidence/{id}, stats, refresh
│   └── intelligence_router.py  # /intelligence overview, graphs, predictions, drift
│
├── utils/
│   └── helpers.py              # Shared text, audio, hashing utilities
│
└── tests/
    └── test_pipeline.py        # Pytest unit + integration tests
```

---

## Prerequisites

| Service | Version |
| ------- | ------- |
| Python  | 3.11+   |
| MongoDB | 6.0+    |
| Redis   | 7.0+    |

---

## Quick Start

### 1. Clone & set up environment

```bash
git clone https://github.com/your-org/aegisai.git
cd "Aegis AI"

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required keys:

- `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com)
- `SARVAM_API_KEY` — from [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
- `MONGODB_URI` — local or Atlas connection string
- `REDIS_HOST` / `REDIS_PORT` — local or managed Redis

### 3. Start MongoDB & Redis (local)

```bash
# MongoDB
mongod --dbpath ./data/db

# Redis
redis-server
```

### 4. Run the server

```bash
python main.py
# or with hot reload:
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## REST API Reference

### POST `/goal` — Submit a text goal

```json
{
  "goal": "Launch a SaaS product for AI-based resume screening within 3 months",
  "language": "en-IN",
  "context": { "budget": "50000 USD", "team_size": 4 },
  "modality": "text"
}
```

**Response:**

```json
{
  "task_id": "uuid",
  "status": "IN_PROGRESS",
  "message": "Goal processed successfully.",
  "plan": {
    "task_id": "uuid",
    "goal": "...",
    "subtasks": [...],
    "research_insights": "...",
    "execution_plan": "...",
    "confidence": 68.5,
    "risk_level": "MEDIUM",
    "reasoning": "..."
  }
}
```

---

### POST `/goal/voice` — Submit a voice goal

```json
{
  "audio_base64": "<base64-encoded WAV/MP3>",
  "language": "hi-IN"
}
```

Pipeline: `Audio → Sarvam STT → AegisAI → Sarvam TTS`

Response includes `audio_response_base64` with spoken output.

---

### GET `/plan/{task_id}` — Retrieve execution plan

Returns the full plan, subtasks, confidence score, and risk level for a stored task.

---

### GET `/plan/{task_id}/translate?target_language=hi-IN` — Translate plan

Uses Sarvam AI Translation to return the execution plan in any supported Indic language.

---

### GET `/confidence/{task_id}` — Confidence score

```json
{
  "task_id": "uuid",
  "confidence": 68.5,
  "risk_level": "MEDIUM",
  "components": {
    "goal_clarity": 0.7,
    "information_quality": 0.75,
    "execution_feasibility": 0.7,
    "risk_manageability": 0.6,
    "resource_adequacy": 0.65,
    "external_uncertainty": 0.55
  },
  "reasoning": "..."
}
```

---

### GET `/confidence/{task_id}/components` — Trust formula breakdown

Returns each of the six trust dimensions, its weight, and weighted contribution to the final score.

For backward compatibility, legacy tasks stored with old 4-component data are automatically mapped to the new 6-component schema.

---

### GET `/confidence/stats/summary` — System-wide stats

Aggregate confidence statistics across all stored tasks.

---

### PUT `/goal/outcome` — Record outcome (triggers reflection)

```json
{
  "task_id": "uuid",
  "status": "COMPLETED",
  "outcome_notes": "All phases completed on schedule.",
  "actual_duration_minutes": 5040
}
```

Triggers the **Reflection Agent** to log a lesson and update historical confidence calibration.

---

### POST `/confidence/{task_id}/refresh` — Re-evaluate confidence

Re-calculates the confidence score using the latest outcome history from MongoDB.

---

### POST `/intelligence/predict` — Explainable success prediction

Runs the success predictor with explainability enabled:

- Uses `shap.TreeExplainer` for the XGBoost catalyst model.
- Computes per-prediction feature contribution values (`shap_values`).
- Retrieves top 5 similar historical tasks using FAISS-based vector similarity.
- Returns human-readable key positive and negative decision factors.

```json
{
  "goal": "Launch an AI-powered resume screening SaaS in 3 months with a 4-member team",
  "context": { "budget": "50000 USD", "team_size": 4 },
  "language": "en-IN"
}
```

**Response (excerpt):**

```json
{
  "success_probability": 0.78,
  "predicted_success_probability": 0.78,
  "explanation": {
    "positive_factors": [
      "Execution decomposition supported the success prediction",
      "Information quality supported the success prediction"
    ],
    "negative_factors": ["External uncertainty reduced expected success"]
  },
  "shap_values": {
    "goal_length_words": 0.01234,
    "num_subtasks": 0.18422,
    "clarity": 0.09102
  },
  "similar_cases": [
    {
      "task": "Launch an AI-powered resume screening SaaS with staged rollout",
      "outcome": "success"
    },
    {
      "task": "Deploy recruitment automation pipeline for resume triage",
      "outcome": "failed"
    }
  ]
}
```

Notes:

- `success_probability` is provided for explainability-friendly clients.
- `predicted_success_probability` is retained for backward compatibility.
- `similar_cases` contains top matches with outcome labels (`success`, `failed`, or `unknown`).

---

## Supported Languages (Sarvam AI)

| Code    | Language        |
| ------- | --------------- |
| `en-IN` | English (India) |
| `hi-IN` | Hindi           |
| `bn-IN` | Bengali         |
| `ta-IN` | Tamil           |
| `te-IN` | Telugu          |
| `kn-IN` | Kannada         |
| `ml-IN` | Malayalam       |
| `mr-IN` | Marathi         |
| `gu-IN` | Gujarati        |
| `pa-IN` | Punjabi         |

---

## Frontend Performance Optimizations

The web UI includes several production-ready performance optimizations:

- **Route-level lazy loading** using `React.lazy` + `Suspense` so auth/dashboard pages are loaded only when needed.
- **Manual vendor chunking** in Vite (`vendor-core`, `vendor-radix`, `vendor-motion`) to avoid oversized single bundles.
- **Intent-based prefetching** (hover/focus/touch) for key navigation links such as Sign In / Register.
- **Idle-time prefetching** for high-probability routes from landing and auth flows.
- **Post-auth redirect prefetching** so destination routes are warmed just before login/register redirects.

These changes reduce initial JS payload pressure and improve perceived route transition speed, especially on first-time navigation paths.

---

## Performance Verification

Use the following checks to validate frontend performance behavior after changes:

1. **Production build sanity**

- Run `npm run build` inside `frontend/`.
- Confirm build completes without chunk-size warnings.

2. **Chunk profile check**

- Inspect `frontend/dist/assets` output.
- Ensure route files are split (`Login-*`, `Register-*`, `Dashboard-*`, etc.) and vendor chunks are separated (`vendor-core-*`, `vendor-radix-*`, `vendor-motion-*`).

3. **SPA navigation check**

- Start app and navigate from landing to Sign In/Register.
- Confirm navigation happens client-side (no full page refresh).

4. **Prefetch behavior check**

- Open browser DevTools Network tab.
- On hover/focus/touch over auth CTAs, verify route chunks are requested before click.
- After login/register action, verify destination chunk is prefetched before redirect.

5. **Cold-path user journey check**

- Hard-refresh landing page and navigate to auth routes.
- Confirm faster first transition due to idle + intent prefetching.

6. **Dev route timing logs (measurable transitions)**

- Run the frontend in dev mode and open browser console.
- Navigate between key routes (`/`, `/login`, `/register`, `/dashboard`, `/analytics`).
- Confirm logs in this format appear: `[route-perf] <trigger> <from> -> <to> in <N>ms`.
- After every 10 transitions, confirm summary log appears: `[route-perf-summary] ... p50=... p95=... click:p95=... pushstate:p95=... routes=/dashboard:p95=... families=auth:p95=...`.
- Optional dev controls:
  - `window.__routePerf.reset()` clears current sample window.
  - `window.__routePerf.snapshot()` returns total queued samples, per-trigger counts, and per-route counts.
  - `window.__routePerf.dump()` prints per-trigger counts in a table.
  - `window.__routePerf.export()` returns a JSON report with overall metrics plus by-trigger, by-route, and by-family distributions.
  - `window.__routePerf.exportCsv()` returns a CSV string for easy sharing in sheets/reports.
  - `window.__routePerf.copyCsv()` copies the CSV report to the clipboard when clipboard access is available.
  - `window.__routePerf.history()` returns the buffered summary windows with timestamps and window indexes.
  - `window.__routePerf.clearHistory()` clears the buffered summary history.
  - `window.__routePerf.exportHistoryCsv()` returns a CSV view of the buffered summary history.
  - `window.__routePerf.copyHistoryCsv()` copies the history CSV report to the clipboard.
  - `window.__routePerf.exportHistoryJson()` returns a JSON report for the buffered summary history.
  - `window.__routePerf.copyHistoryJson()` copies the history JSON report to the clipboard.
  - `window.__routePerf.exportLatestWindowCsv()` returns the newest summary window as CSV.
  - `window.__routePerf.copyLatestWindowCsv()` copies the newest summary window CSV to the clipboard.
  - `window.__routePerf.exportLatestWindowJson()` returns the newest summary window as JSON.
  - `window.__routePerf.copyLatestWindowJson()` copies the newest summary window JSON to the clipboard.
  - `window.__routePerf.exportSnapshotJson()` returns the current live snapshot as JSON.
  - `window.__routePerf.copySnapshotJson()` copies the current live snapshot JSON to the clipboard.
  - `window.__routePerf.exportBundleJson()` returns a combined JSON bundle of the snapshot, latest window, and history.
  - `window.__routePerf.copyBundleJson()` copies the combined JSON bundle to the clipboard.
  - `window.__routePerf.downloadSnapshotJson()` downloads the current live snapshot as a JSON file.
  - `window.__routePerf.downloadBundleJson()` downloads the combined JSON bundle as a JSON file.
  - `window.__routePerf.downloadCsv()` downloads the full CSV report.
  - `window.__routePerf.downloadHistoryCsv()` downloads the history CSV report.
  - `window.__routePerf.downloadHistoryJson()` downloads the history JSON report.
  - `window.__routePerf.downloadLatestWindowCsv()` downloads the latest summary window as CSV.
  - `window.__routePerf.downloadLatestWindowJson()` downloads the latest summary window as JSON.
  - The dev-only overlay in the bottom-right corner shows live samples, latest p95 values, and history length.
  - The overlay badge shows buffered history usage as `current/20`.
  - Press `Ctrl+Alt+R` in dev mode to toggle the overlay.
  - Press `Ctrl+Alt+J` in dev mode to copy the history JSON report.
  - Press `Ctrl+Alt+L` in dev mode to copy the latest summary window JSON.
  - Press `Ctrl+Alt+K` in dev mode to copy the latest summary window CSV.
  - Press `Ctrl+Alt+S` in dev mode to copy the current snapshot JSON.
  - Press `Ctrl+Alt+A` in dev mode to copy the combined JSON bundle.
  - Press `Ctrl+Alt+O` in dev mode to download the current snapshot JSON.
  - Press `Ctrl+Alt+W` in dev mode to download the combined JSON bundle.
  - Press `Ctrl+Alt+D` in dev mode to download the full CSV report.
  - Press `Ctrl+Alt+H` in dev mode to download the history CSV report.
  - Press `Ctrl+Alt+I` in dev mode to download the history JSON report.
  - Press `Ctrl+Alt+Y` in dev mode to download the latest summary window CSV.
  - Press `Ctrl+Alt+U` in dev mode to download the latest summary window JSON.
  - Use the overlay `Download History CSV`, `Download History JSON`, `Download Latest Window CSV`, and `Download Latest Window JSON` buttons for file-based sharing.
  - Downloaded files include a timestamped filename so repeated exports do not overwrite each other.
  - Use the overlay `Reset Copy State` button to clear the footer status message.
  - Use the overlay `Clear History` button to reset buffered summary windows instantly.
  - Copy status auto-clears back to idle after about 2.5 seconds.
  - The footer names the last action, such as `copied history JSON` or `downloaded bundle JSON`.
  - Use the overlay `Copy Latest Window JSON` button to copy just the newest summary window.
  - Use the overlay `Copy Latest Window CSV` button to copy the newest summary window in CSV form.
  - Use the overlay `Download Snapshot JSON` and `Download Bundle JSON` buttons for file-based sharing.
  - Use the overlay `Download CSV`, `Download History CSV`, `Download History JSON`, `Download Latest Window CSV`, and `Download Latest Window JSON` buttons for file-based sharing.
- Compare first navigation timing vs repeated navigation timing to validate cache/prefetch effects.

---

## Performance Troubleshooting

| Symptom                                             | Likely Cause                                                                   | Suggested Fix                                                                                      |
| --------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Build shows `Some chunks are larger than 500 kB`    | Manual chunk rules removed or new heavy dependency landed in app entry chunk   | Re-check `frontend/vite.config.ts` `manualChunks` rules and rebuild.                               |
| Clicking Sign In / Register causes full-page reload | Link rendered as `<a href>` instead of SPA `Link`                              | Replace with `Link` from `react-router-dom` in landing/auth components.                            |
| First auth page load still feels slow               | Prefetch handlers not firing due to missing hover/focus/touch bindings         | Verify prefetch handlers are attached to CTA links and check Network tab for early chunk requests. |
| Login redirect feels delayed                        | Redirect target is not prefetched before navigation                            | Ensure post-auth flow calls route prefetch helper before setting `window.location.href`.           |
| No prefetch requests after landing load             | Idle callback path not triggered or one-time guard already set in same session | Hard refresh the page, then verify idle requests in Network tab.                                   |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## System Endpoints

| Endpoint      | Description                     |
| ------------- | ------------------------------- |
| `GET /`       | System info + endpoint map      |
| `GET /health` | MongoDB + Redis health check    |
| `GET /agents` | List all agents and their roles |
| `GET /docs`   | Swagger UI                      |
| `GET /redoc`  | ReDoc UI                        |

---

## Environment Variables Reference

| Variable                             | Required | Default                     | Description                         |
| ------------------------------------ | -------- | --------------------------- | ----------------------------------- |
| `GROQ_API_KEY`                       | ✅       | —                           | Groq API key                        |
| `GROQ_MODEL`                         |          | `llama-3.3-70b-versatile`   | Groq model name                     |
| `SARVAM_API_KEY`                     | ✅       | —                           | Sarvam AI API key                   |
| `MONGODB_URI`                        | ✅       | `mongodb://localhost:27017` | MongoDB connection string           |
| `MONGODB_DB_NAME`                    |          | `aegisai`                   | Database name                       |
| `REDIS_HOST`                         |          | `localhost`                 | Redis host                          |
| `REDIS_PORT`                         |          | `6379`                      | Redis port                          |
| `REDIS_TTL_SECONDS`                  |          | `3600`                      | Short-term context TTL              |
| `TRUST_WEIGHT_GOAL_CLARITY`          |          | `0.15`                      | 6D trust weight                     |
| `TRUST_WEIGHT_INFORMATION_QUALITY`   |          | `0.20`                      | 6D trust weight                     |
| `TRUST_WEIGHT_EXECUTION_FEASIBILITY` |          | `0.25`                      | 6D trust weight                     |
| `TRUST_WEIGHT_RISK_MANAGEABILITY`    |          | `0.15`                      | 6D trust weight                     |
| `TRUST_WEIGHT_RESOURCE_ADEQUACY`     |          | `0.15`                      | 6D trust weight                     |
| `TRUST_WEIGHT_EXTERNAL_UNCERTAINTY`  |          | `0.10`                      | 6D trust weight                     |
| `TRUST_WEIGHT_SUCCESS_RATE`          |          | `0.4`                       | Legacy trust weight (compatibility) |
| `TRUST_WEIGHT_DATA_COMPLETENESS`     |          | `0.3`                       | Legacy trust weight (compatibility) |
| `TRUST_WEIGHT_FEASIBILITY`           |          | `0.2`                       | Legacy trust weight (compatibility) |
| `TRUST_WEIGHT_COMPLEXITY_INVERSE`    |          | `0.1`                       | Legacy trust weight (compatibility) |
| `RISK_HIGH_THRESHOLD`                |          | `45.0`                      | Confidence below this → HIGH risk   |
| `RISK_MEDIUM_THRESHOLD`              |          | `72.0`                      | Confidence below this → MEDIUM risk |
| `DEBUG`                              |          | `false`                     | Enable hot reload                   |
| `LOG_LEVEL`                          |          | `INFO`                      | Logging verbosity                   |
| `OPENROUTER_API_KEY`                 |          | —                           | OpenRouter fallback key (debate)    |
| `OPENROUTER_MODEL`                   |          | `openai/gpt-4o-mini`        | OpenRouter fallback model           |

---

## License

MIT © AegisAI
