# Unity Assistant

A chat assistant for the Unity Service Portal. It helps employees find the right offering
(Service Offering = request something, Support Offering = declare an issue), shows the ticket to
raise with a "How to raise" knowledge document for its steps, and links straight to the offering in Unity. It answers how-to
questions from a small knowledge base, explains what a ticket's status means and what to do next,
and answers general IT questions when the AI is on.

**Stack:** FastAPI (2 dependencies) + React/Vite. No database. AI optional, any provider.

> **New machine or deploying to Render?** See [SETUP.md](SETUP.md) for what to install,
> office-network troubleshooting, and Render deployment steps.

## Run it

```bash
# backend — http://127.0.0.1:8020
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env          # add your LLM key here (optional)
.venv\Scripts\python -m uvicorn main:app --reload --port 8020

# frontend — http://localhost:5180 (proxies /api to :8020)
cd frontend
npm install
npm run dev
```

Production: `npm run build` in `frontend/`, then the backend serves `frontend/dist` itself.

## AI (`backend/.env`)

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `gemini`, `openai`, `azure_openai` or `anthropic` |
| `LLM_API_KEY` | Your key. Empty = AI off; the guided menus + keyword matcher still work |
| `LLM_MODEL` | Optional model override (Gemini default: `gemini-3.5-flash`) |
| `LLM_FALLBACK_MODELS` | Comma-separated models tried when the main one is busy (Gemini default: `gemini-3.5-flash-lite,gemini-flash-lite-latest`) |
| `LLM_BASE_URL` | Azure OpenAI deployment URL, or an internal LLM gateway |

The model is given the catalog and must answer with a real offering ID. The backend
rejects anything not in the catalog, and falls back to the keyword matcher if the model
call fails — so the assistant never recommends an offering that doesn't exist.
It first classifies the message (needs a ticket, wants to create one, how-to, about my tickets,
general IT, small talk) and answers how-to questions from the knowledge base, citing article IDs.

## Knowledge base

`backend/knowledge_base.py` builds a "How to raise" document for every offering (`KB-<offering id>`)
from the catalog, and holds ~16 mock articles (raising and following tickets, approvals,
urgency, reopening, plus self-help for VPN, Outlook/Teams, passwords, access, admin rights, restores)
and the plain-language meaning of each ticket state. The best matches for each message are given to
the AI; without the AI, how-to questions are answered with the matching article. Replace the
articles with your organisation's own (or load them from the Unity KB API) before going live.

## Unity API

All Unity calls live in `backend/unity_client.py`. Set `UNITY_API_BASE` / `UNITY_API_TOKEN`
and adjust the paths + field mapping there so it returns the shapes in `backend/sample_data.py`.
`UNITY_PORTAL_BASE` (your portal's base URL) builds the links:
`/saw/ess/offeringPage/<id>` and `/saw/ess/categoryPage/<id>`.

The bundled sample catalog is generic placeholder data until the API is connected.

## Layout

```
backend/   main.py (routes) · assistant.py (decisions) · knowledge_base.py (KB articles) · llm.py (providers) · unity_client.py (Unity API)
frontend/  src/components/ChatWidget.jsx (the assistant) · Portal.jsx (demo stand-in for the Unity home page)
```

Only `ChatWidget` is meant to be embedded in the real portal; `Portal.jsx` exists for demos.
Nothing is ever submitted to Unity from this app — the user raises the ticket via the link.
