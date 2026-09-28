# Deployment

This project deploys as two services. Do not put LLM API keys in the frontend.

```
Vercel (React / Vite)
        |
        | HTTPS  VITE_API_BASE_URL
        v
Render (FastAPI / Uvicorn)
        |
        +-- OpenAI
        +-- Claude
        +-- Gemini
```

## 1. Architecture

The browser talks only to FastAPI. Provider SDKs and secrets stay on Render.

- Frontend: Vercel, Root Directory `frontend/`
- Backend: Render Web Service, Root Directory `backend/`
- Sessions: in-memory on the Render process (see section 9)

## 2. GitHub source

Push this repository to GitHub. Connect the same repo to Render and Vercel.

Do not commit `backend/.env`. It is gitignored.

## 3. Render backend

Create a **Web Service** from the GitHub repo.

| Setting | Value |
|---|---|
| Language | Python |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Python | 3.11 or newer |

`$PORT` is provided by Render. Do not hardcode `8000` in the start command.

Confirm `GET https://<your-service>.onrender.com/health` returns `{"status":"ok"}`.

## 4. Render environment variables

Set these in the Render dashboard. Do not paste real keys into GitHub or this file.

```
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5
ANTHROPIC_WORKSPACE_ID=

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash

LLM_TIMEOUT_SECONDS=30
LLM_MAX_OUTPUT_TOKENS=2048
MAX_PROMPT_LENGTH=8000

CORS_ORIGINS=https://<your-vercel-app>.vercel.app
```

Leave `ANTHROPIC_WORKSPACE_ID` **empty** when using a workspace-scoped Anthropic key (the current local setup). A wrong value here will break Claude.

After the Vercel URL is known, set `CORS_ORIGINS` to that origin with **no trailing slash**. Multiple origins are comma-separated.

Do not use `allow_origins=["*"]`.

## 5. Vercel frontend

Import the GitHub repo in Vercel.

| Setting | Value |
|---|---|
| Framework Preset | Vite |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

The app is a single page. No extra routing setup is required.

## 6. Vercel environment variable

Set **before** the production build. Vite inlines this at build time.

```
VITE_API_BASE_URL=https://<your-service>.onrender.com
```

No trailing slash. Never put `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY` on Vercel.

Redeploy the frontend after changing `VITE_API_BASE_URL`.

## 7. CORS

Render `CORS_ORIGINS` must include the exact Vercel origin, for example:

```
https://your-app.vercel.app
```

Local development still uses:

```
http://localhost:5173,http://127.0.0.1:5173
```

If the browser shows a CORS error, the Vercel origin is missing or has a trailing slash.

## 8. Production testing

1. `GET /health` on Render → HTTP 200
2. Open the Vercel URL → header shows Connected
3. Compare a short prompt → three cards (OpenAI, Claude, Gemini)
4. Continue with one model → only that provider is called
5. New Comparison → fresh frontend session

Free Render instances may cold-start for 30–60 seconds.

## 9. In-memory sessions

`SessionManager` stores conversations in the FastAPI process.

- A Render restart, deploy, or spin-down **clears all sessions**
- Continue after a restart returns HTTP 404; start a new comparison
- This is acceptable for the academic demo

There is no Redis or database by design.

## 10. Secret handling

- Keys live only in Render environment variables (and a local gitignored `.env`)
- Frontend never receives provider keys
- Do not commit `.env`, screenshots of keys, or keys in chat/docs
- Rotate any key that was pasted into chat or committed by mistake
