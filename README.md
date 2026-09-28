# Multi-LLM Custom ChatGPT

Academic project for the IIT Patna AI/ML program (Project 1).

## Overview

This is a ChatGPT-like application. One user question is sent to OpenAI, Claude, and Gemini at the same time. The three answers appear side-by-side. The user can continue the conversation with one selected model. Each model keeps its own independent history.

## Objective

Compare responses from multiple LLMs and continue with a selected model.

## Features

- Parallel OpenAI / Claude / Gemini comparison
- Side-by-side responses
- Independent conversation histories
- Continue with selected model
- Response latency
- Provider error handling

The project does not include authentication, a database, Redis, streaming, or RAG.

## Tech Stack

**Frontend**

- React
- TypeScript
- Vite
- Tailwind CSS

**Backend**

- Python
- FastAPI
- Pydantic

**LLMs**

- OpenAI
- Anthropic Claude
- Google Gemini

## Architecture

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

The browser talks only to FastAPI. Provider SDKs and API keys stay on the backend.

See [docs/architecture.md](docs/architecture.md) for a viva-oriented explanation.

## Deployment

Frontend → **Vercel**. Backend → **Render** Web Service.

The browser calls FastAPI over HTTPS. OpenAI, Claude, and Gemini keys stay on Render.

See [docs/deployment.md](docs/deployment.md) for the exact Render/Vercel settings. Do not deploy secrets in Git.

## Local Setup

Prerequisites: Node.js 18+, Python 3.10+, npm.

On some Windows machines the Python launcher is `py` rather than `python`.

**Backend**

```bash
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is at [http://127.0.0.1:8000](http://127.0.0.1:8000).

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

The UI is at [http://localhost:5173](http://localhost:5173).

Copy `backend/.env.example` to `backend/.env` and add provider keys for live answers. The backend starts with empty keys. A comparison without keys returns structured provider errors instead of fake answers.

## Environment Variables

Documented names only. Never put real keys in this file or in frontend code.

Backend (`backend/.env.example`):

```
OPENAI_API_KEY=
OPENAI_MODEL=

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=

GEMINI_API_KEY=
GEMINI_MODEL=
```

Also available:

- `APP_NAME`
- `APP_VERSION`
- `API_PREFIX`
- `CORS_ORIGINS`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_OUTPUT_TOKENS`
- `MAX_PROMPT_LENGTH`
- `ANTHROPIC_WORKSPACE_ID` (leave empty for a workspace-scoped Anthropic key)

Frontend (`frontend/.env.example`):

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Default models (used when a model variable is omitted):

- OpenAI: `gpt-4o-mini`
- Claude: `claude-sonnet-4-5`
- Gemini: `gemini-3.8-flash`

## API Endpoints

- `GET /health`
- `POST /api/session`
- `DELETE /api/session/{session_id}`
- `POST /api/chat/compare`
- `POST /api/chat/continue`

OpenAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Testing

```bash
cd backend
pytest
```

```bash
cd frontend
npm run lint
npm run build
```

Automated backend tests use mocked SDK clients. They do not make paid API calls.

## Limitations

- Sessions are in-memory
- Sessions disappear after a backend restart (including Render restarts)
- Provider keys are required for real answers (local `.env` or Render env vars)
- There is no authentication or persistent storage

## Future Improvements

These are optional later ideas, not part of the current project:

- persistent storage
- authentication
- streaming

## Demo

See [docs/demo-guide.md](docs/demo-guide.md) for the viva walkthrough.
