# Demo Guide

Use this walkthrough for the IIT Patna Project 1 viva.

## Step 1

Start the backend:

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

## Step 2

Start the frontend:

```bash
cd frontend
npm run dev
```

## Step 3

Open [http://localhost:5173](http://localhost:5173). Confirm **Backend Connected**.

## Step 4

Ask:

"Explain RAG to a beginner."

## Step 5

Show:

- OpenAI answer
- Claude answer
- Gemini answer
- latency and status on each card

If a provider key is missing, that card shows a configuration error. The other cards still appear.

## Step 6

Click **Continue with Claude** (or OpenAI / Gemini if Claude is unavailable).

## Step 7

Ask:

"Give me a simple real-world example."

Only the selected model answers.

## Step 8

Explain during viva:

"The same initial question is sent concurrently to three providers. When the user chooses Claude, only Claude receives the follow-up, and Claude uses its own conversation history."

Then click **New Comparison** and ask a different question to show a fresh session.

## Screenshots to capture manually

1. Empty / home state
2. Three side-by-side responses
3. Continue with selected model
4. Follow-up response

Do not fabricate screenshots.

## Short viva questions

- **Why asyncio?** Provider calls wait on network I/O. Async lets the event loop overlap those waits.
- **Why parallel requests?** Sequential calls would add the three latencies together. Parallel calls finish in about the time of the slowest model.
- **Why separate provider classes?** OpenAI, Anthropic, and Gemini have different SDKs. Isolation keeps FastAPI on a shared `Message` / `LLMResponse` shape.
- **How are API keys protected?** They live only in backend environment variables. The browser never sees them and never calls vendor APIs.
- **How does Continue with this model work?** The frontend sends `POST /api/chat/continue` with `model` set to `openai`, `claude`, or `gemini`. The backend calls only that provider.
- **Why are histories separate?** Each model produced a different answer. Mixing those answers would leak another model’s wording into the next prompt.
- **What happens if one provider fails?** The comparison still returns HTTP 200. The failed card shows an error; successful cards still show answers.
- **Why use FastAPI?** It is a small Python HTTP API with async support, Pydantic validation, and automatic OpenAPI docs.
- **Why keep sessions in memory?** This is an academic prototype. A process-local store is enough to prove independent histories without a database.
