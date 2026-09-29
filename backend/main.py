"""Unity Service Assistant API.

Dev:   uvicorn main:app --reload --port 8020   (frontend runs on Vite, proxies /api)
Prod:  build the frontend, then uvicorn serves frontend/dist from the same origin.
"""
import os
from pathlib import Path

import env

env.load()  # must run before modules that read configuration at import time

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import assistant  # noqa: E402
import llm  # noqa: E402
import unity_client  # noqa: E402

app = FastAPI(title="Unity Service Assistant")


class Turn(BaseModel):
    role: str
    text: str


class ChatIn(BaseModel):
    message: str
    last_query: str | None = None
    history: list[Turn] = []


USER_NAME = os.getenv("APP_USER_NAME", "Guest").strip() or "Guest"  # replace with the SSO user in production


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/meta")
def meta():
    initials = "".join(w[0] for w in USER_NAME.split()[:2]).upper()
    return {"live": unity_client.is_live(), "portal": unity_client.PORTAL_BASE,
            "ai": llm.label(), "model": llm.MODEL if llm.enabled() else None,
            "user": {"name": USER_NAME, "initials": initials}}


@app.get("/api/categories")
def categories():
    return [{"id": c["id"], "name": c["name"], "description": c["description"],
             "count": len(c["offerings"]), "url": unity_client.category_url(c["id"])}
            for c in unity_client.get_categories()]


@app.get("/api/tickets")
def tickets():
    return unity_client.get_my_tickets()


@app.get("/api/tickets/{number}")
def ticket(number: str):
    t = unity_client.get_ticket(number)
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


@app.post("/api/chat")
def chat(body: ChatIn):
    if not body.message.strip():
        raise HTTPException(400, "Empty message")
    history = [t.model_dump() for t in body.history[-8:]]
    return assistant.respond(body.message, body.last_query, history)


dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
