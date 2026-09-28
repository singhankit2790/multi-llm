# Architecture

This document is for explaining the IIT Patna Project 1 implementation in a viva.

The application sends one question to OpenAI, Claude, and Gemini in parallel, shows the answers side-by-side, and lets the user continue with one model. Each model has its own conversation history.

```
React
  |
  v
FastAPI
  |
  +-- OpenAI
  +-- Claude
  +-- Gemini
  |
  v
Comparison
  |
  v
Side-by-side UI
  |
  v
Selected-model continuation
```

## 1. System overview

The frontend is a single-page React app. The backend is FastAPI. The browser never calls vendor APIs. FastAPI creates an in-memory session, fans the prompt out to three provider adapters, and returns normalized results.

Main routes:

- `GET /health`
- `POST /api/session`
- `DELETE /api/session/{session_id}`
- `POST /api/chat/compare`
- `POST /api/chat/continue`

## 2. Frontend

React + TypeScript + Vite + Tailwind CSS.

`useChat` holds `sessionId`, comparison results, and continuation state. The first compare omits `session_id` so FastAPI creates a session. **Continue** calls `/api/chat/continue` with `openai`, `claude`, or `gemini`. **New Comparison** clears the stored session ID. **Back to results** restores the previous cards without another API call.

Cards render in a stable order: OpenAI, Claude, Gemini. A failed provider stays on its own card.

## 3. FastAPI backend

FastAPI loads settings from the process environment. A local `backend/.env` is used in development when present; Render supplies the same variable names. OS environment variables override the file. CORS is configured with `CORS_ORIGINS` (local Vite origins by default; the Vercel origin in production). Pydantic validates prompts (non-empty, max 8000 characters). Missing sessions return HTTP 404. Individual provider failures still return HTTP 200 with structured error results.

## 4. Provider abstraction

`BaseLLMProvider.generate(messages)` is the common interface. Vendor SDK code lives only in:

- `openai_provider.py`
- `claude_provider.py`
- `gemini_provider.py`

Each adapter converts the shared `Message` list into the vendor request shape and returns a normalized `LLMResponse`:

- `provider`
- `model`
- `content`
- `status`
- `latency_ms`
- `error`

A missing API key becomes a configuration error, not a fake answer.

## 5. Parallel orchestration

`LLMOrchestrator` uses `asyncio.gather(..., return_exceptions=True)` so OpenAI, Claude, and Gemini overlap in time. Results are always returned in the order OpenAI → Claude → Gemini, even if Gemini finishes first. `total_latency_ms` is wall-clock time around the gather, not the sum of the three latencies.

## 6. Session / history architecture

`SessionManager` stores one session as three lists: OpenAI history, Claude history, Gemini history. Compare appends the same user prompt to all three, then each provider is called with **only** its own messages. A successful assistant reply is appended only to that provider. Failed providers keep the user turn and do not get a fake assistant error message.

Sessions live in process memory. They disappear on restart.

## 7. Continue-with-model flow

`POST /api/chat/continue` with `model=claude` appends the follow-up only to Claude, calls Claude once, and leaves OpenAI and Gemini unchanged. The same applies for `openai` and `gemini`.

If the user later compares again on the **same** `session_id`, each provider receives its own prior transcript plus the new question.

## 8. Error handling

- Empty or oversized prompts: HTTP 422
- Unknown session: HTTP 404
- One provider timeout or missing key: that card is `status=error`; the others can still succeed
- All providers failing: HTTP 200 with three error results and no fabricated text

The UI maps network failure to a backend-offline message and session 404 to a “start a new comparison” message.

## 9. Security

API keys are backend environment variables. They are not sent to the React app, not returned by endpoints, and not written into frontend source. Tests use mocked SDKs. `backend/.env` is gitignored.

## 10. Current limitations

- In-memory sessions only
- No authentication, database, Redis, streaming, or RAG
- Real answers require provider keys on the backend (local `.env` or Render env vars)
- Production deploy: Vercel frontend + Render backend ([docs/deployment.md](deployment.md))
- A page refresh starts a new frontend session

Those limits are intentional for this academic prototype.
