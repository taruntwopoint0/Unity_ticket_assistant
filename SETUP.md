# Setup guide — running Unity Assistant on a new machine

This guide covers (1) what to install, (2) running it locally on your office laptop,
and (3) deploying it to Render.

---

## 1. What to install

| Tool | Version | Why | Download |
|---|---|---|---|
| **Git** | any recent | clone the repository | https://git-scm.com/download/win |
| **Python** | **3.11 or 3.12** | runs the backend (FastAPI) | https://www.python.org/downloads/ |
| **Node.js** | **20 LTS or newer** (includes npm) | builds/runs the React frontend | https://nodejs.org/ |
| A code editor (optional) | — | VS Code recommended | https://code.visualstudio.com/ |

That's the whole tech stack. There is **no database, no Docker needed locally**, and no paid services.

When installing **Python**, tick **"Add python.exe to PATH"** on the first screen.
No admin rights? Choose *"Install for current user only"* (Python) and use the Node.js
**.zip** download (extract it and add the folder to your user PATH).

Check the installs in a new terminal:

```bash
git --version
python --version
node --version
npm --version
```

### Libraries (installed automatically in step 2)

| Part | Packages |
|---|---|
| Backend (`backend/requirements.txt`) | `fastapi`, `uvicorn` |
| Frontend (`frontend/package.json`) | `react`, `react-dom`, `vite`, `@vitejs/plugin-react` |

The AI providers are called over plain HTTPS — no extra SDK is required.

---

## 2. Run it on your laptop

### Get the code

```bash
git clone https://github.com/taruntwopoint0/unity-assistant.git
cd unity-assistant
```

### Backend (terminal 1)

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

Open `backend/.env` in an editor and fill in what you have (all optional):

```
LLM_PROVIDER=gemini
LLM_API_KEY=<your Gemini key>     # from https://aistudio.google.com/apikey
UNITY_PORTAL_BASE=<your Unity portal URL>
APP_USER_NAME=<your name>
```

Start it:

```bash
.venv\Scripts\python -m uvicorn main:app --reload --port 8020
```

### Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5180**.

### Or run it as one process (like production)

```bash
cd frontend && npm install && npm run build && cd ..
backend\.venv\Scripts\python -m uvicorn main:app --app-dir backend --port 8020
```

Open **http://localhost:8020**.

### Office-network troubleshooting

| Problem | Fix |
|---|---|
| `pip install` / `npm install` time out | You're behind a corporate proxy. Set it for the session: `set HTTPS_PROXY=http://proxy.company:port` and `npm config set proxy http://proxy.company:port` (ask IT for the address). |
| SSL certificate errors in pip/npm | Corporate TLS inspection. Ask IT for the root certificate, then `pip config set global.cert <path.pem>` and `npm config set cafile <path.pem>`. |
| `Activate.ps1 cannot be loaded` | You don't need to activate — the commands above call `.venv\Scripts\python` directly. |
| Header shows **"Online · guided mode"** | No LLM key, or the AI endpoint is blocked by the office firewall. The assistant still works (menus + keyword matching). |
| Port 8020 or 5180 already in use | Change `--port` for the backend and `server.port` / `proxy` in `frontend/vite.config.js`. |

---

## 3. Deploy to Render

The repo includes a `Dockerfile` and `render.yaml`, so Render builds the frontend and the API
into a single web service.

1. Push the repo to GitHub (already done if you cloned it from there).
2. In Render: **New → Blueprint** → connect GitHub → choose this repository.
3. Render reads `render.yaml` and asks for the secret values:
   - `LLM_API_KEY` — your Gemini key
   - `UNITY_PORTAL_BASE` — your Unity portal URL (for the "Request" links)
   - `UNITY_API_BASE`, `UNITY_API_TOKEN` — leave empty until the Unity API is available
4. Click **Apply**. The first build takes ~3–5 minutes. Your app is at `https://unity-assistant-xxxx.onrender.com`.

Every push to `main` redeploys automatically.

**Manual alternative** (without Blueprint): New → Web Service → pick the repo →
Runtime **Docker** → Health check path `/api/health` → add the same environment variables.

**Free-plan note:** free services sleep after ~15 minutes of inactivity; the first request
afterwards takes ~30–50 seconds to wake up.

### Keep your keys safe

- Never commit `backend/.env` — it is already in `.gitignore`.
- Put keys only in `backend/.env` (local) or Render → *Environment* (hosted).
- If a key is ever pasted somewhere public, revoke it in Google AI Studio and create a new one.
