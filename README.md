# Unity Assistant

A chat assistant for the Unity Service Portal. It helps employees find the right offering
(Service Offering = request something, Support Offering = declare an issue), drafts the ticket
text, and links straight to the offering in Unity. It can also check a ticket's status by number.

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
| `LLM_MODEL` | Optional model override |
| `LLM_BASE_URL` | Azure OpenAI deployment URL, or an internal LLM gateway |

The model is given the catalog and must answer with a real offering ID. The backend
rejects anything not in the catalog, and falls back to the keyword matcher if the model
call fails — so the assistant never recommends an offering that doesn't exist.

## Unity API

All Unity calls live in `backend/unity_client.py`. Set `UNITY_API_BASE` / `UNITY_API_TOKEN`
and adjust the paths + field mapping there so it returns the shapes in `backend/sample_data.py`.
`UNITY_PORTAL_BASE` (your portal's base URL) builds the links:
`/saw/ess/offeringPage/<id>` and `/saw/ess/categoryPage/<id>`.

The bundled sample catalog is generic placeholder data until the API is connected.

## Layout

```
backend/   main.py (routes) · assistant.py (decisions) · llm.py (providers) · unity_client.py (Unity API)
frontend/  src/components/ChatWidget.jsx (the assistant) · Portal.jsx (demo stand-in for the Unity home page)
```

Only `ChatWidget` is meant to be embedded in the real portal; `Portal.jsx` exists for demos.
Nothing is ever submitted to Unity from this app — the user raises the ticket via the link.
