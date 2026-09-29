"""Assistant: turns a user message into a structured reply.

Ticket lookups, menus and status questions are handled by rules. Offering
matching uses the configured LLM when an API key is set (constrained to real
catalog IDs and validated here), and falls back to the explainable keyword
matcher when no key is set or the model call fails.

Unity offering types:
  Support  — "declare an issue" (something is broken)
  Service  — request something (access, user creation, change)
"""
import logging
import re

import llm
import unity_client

log = logging.getLogger("assistant")

STOPWORDS = set(
    "a an the i me my we our is are am be to of for in on at and or not with it its this that "
    "have has from can cant cannot please need want get im ive dont do does how what which should "
    "raise ticket help".split()
)
# Words present in almost every offering name; they must not drive matching on their own.
GENERIC = {"service", "request", "support", "declare", "issue", "new", "access", "incident", "on", "an"}
ALIASES = {
    "notebook": "laptop", "system": "laptop", "machine": "laptop",
    "pwd": "password", "passwd": "password", "installation": "install", "setup": "install",
    "permission": "access", "permissions": "access", "licence": "license",
    "mails": "mail", "emails": "email",
}
ISSUE_SIGNALS = ["not working", "broken", "error", "down", "unable", "can't", "cannot", "issue", "bug",
                 "problem", "failed", "failing", "stuck", "crash", "slow", "keeps", "stopped", "not loading"]
REQUEST_SIGNALS = ["need", "request", "new", "want", "install", "access", "create", "creation", "add",
                   "apply", "get a", "require", "change", "enable", "onboard"]
TICKET_RE = re.compile(r"\b(INC|REQ|RITM|CHG|PRB|SD)\d{5,}\b", re.I)
CONFIDENT_SCORE = 5
GDPR_NOTE = "Don't include personal or confidential data in the ticket (GDPR)."

MAIN_MENU = [
    {"label": "Something isn't working", "value": "menu:issue"},
    {"label": "Access / user creation", "value": "menu:access"},
    {"label": "Browse offerings by category", "value": "menu:categories"},
    {"label": "My tickets", "value": "my tickets"},
    {"label": "Something else", "value": "menu:else"},
]


def _norm(text: str) -> str:
    return " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s'-]", " ", text.lower())).strip() + " "


def _stem(w: str) -> str:
    if len(w) > 5 and w.endswith("ing"): return w[:-3]
    if len(w) > 4 and w.endswith("ed"): return w[:-2]
    if len(w) > 4 and w.endswith("es"): return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"): return w[:-1]
    return w


def _tokens(text: str, drop_generic: bool = False) -> set[str]:
    words = {_stem(ALIASES.get(w, w)) for w in _norm(text).split() if w not in STOPWORDS}
    return words - GENERIC if drop_generic else words


def detect_type(text: str) -> str | None:
    t = _norm(text)
    issue = any(f" {s}" in t for s in ISSUE_SIGNALS)
    request = any(f" {s}" in t for s in REQUEST_SIGNALS)
    if issue != request:
        return "Support" if issue else "Service"
    return None


def score_services(query: str, services: list[dict]) -> list[dict]:
    text, toks, kind = _norm(query), _tokens(query), detect_type(query)
    ranked = []
    for s in services:
        score, reasons = 0.0, []
        for kw in s.get("keywords", []):
            hit = f" {kw} " in text if " " in kw else _stem(ALIASES.get(kw, kw)) in toks
            if hit:
                score += 4 if " " in kw else 3
                reasons.append(kw)
        name_hits = _tokens(s["name"], drop_generic=True) & toks
        score += 2 * len(name_hits)
        reasons += [w for w in name_hits if w not in reasons]
        score += 0.5 * len(_tokens(s["description"], drop_generic=True) & toks)
        if score and kind == s["type"]:
            score += 3
        if score:
            ranked.append({"service": s, "score": score, "reasons": list(dict.fromkeys(reasons))})
    return sorted(ranked, key=lambda r: r["score"], reverse=True)


def _option(s: dict) -> dict:
    return {"label": s["name"], "value": f"service:{s['id']}", "meta": f"{s['type']} Offering · {s['category']}"}


def _draft(message: str, service: dict) -> dict:
    summary = message.strip().rstrip(".")
    summary = (summary[:1].upper() + summary[1:])[:90]
    lines = [message.strip(), ""] + [f"{f}: " for f in service["fields"]]
    return {"summary": summary, "description": "\n".join(lines)}


def _recommend(service: dict, message: str, reasons: list[str], alternatives: list[dict]) -> dict:
    if service["type"] == "Support":
        text = f"This sounds like an issue to declare. Raise **{service['name']}** — a Support Offering in {service['category']}."
    else:
        text = f"This is a request. Raise **{service['name']}** — a Service Offering in {service['category']}."
    return {
        "type": "recommendation", "text": text, "service": service, "reasons": reasons,
        "draft": _draft(message, service), "alternatives": alternatives, "notice": GDPR_NOTE,
    }


def _menu(value: str, services: list[dict]) -> dict | None:
    kind = value.split(":", 1)[1]
    if kind == "issue":
        return {"type": "text", "text": "Sorry to hear that. Which application or area is affected? You can also just describe the problem.",
                "options": [_option(s) for s in services if s["type"] == "Support"][:8]}
    if kind == "access":
        picks = [s for s in services if s["type"] == "Service" and re.search(r"access|user|par", s["name"], re.I)]
        return {"type": "text", "text": "Which application do you need access to?", "options": [_option(s) for s in picks][:8]}
    if kind == "categories":
        return {"type": "text", "text": "Pick a category to see its offerings.",
                "options": [{"label": c["name"], "value": f"category:{c['id']}", "meta": f"{len(c['offerings'])} offerings"}
                            for c in unity_client.get_categories()]}
    if kind == "else":
        return {"type": "text", "text": "No problem — describe what you need in a sentence, e.g. *\"Eloqua campaign won't publish\"* or *\"I need a DocuSign account\"*."}
    return None


def _category(cid: str, services: list[dict]) -> dict | None:
    items = [s for s in services if s["category_id"] == cid]
    if not items:
        return None
    return {"type": "text", "text": f"Offerings in **{items[0]['category']}**:",
            "options": [_option(s) for s in items],
            "link": {"label": "Open category in Unity", "url": unity_client.category_url(cid)}}


AI_SYSTEM = f"""You are the Unity Assistant, an internal helpdesk assistant on the Unity Service Portal.
Employees raise tickets in Unity by choosing an offering inside a category (e.g. Business Applications).
Offerings are either:
  - Support Offering: declare an issue — something that worked is broken, erroring, slow or down.
  - Service Offering: request something — access, user creation, a change, a new item.
Your job: work out which offering the user should raise, help phrase the ticket, and answer
general questions about which offering to use.

Rules:
- Only use offering IDs from CATALOG. Never invent offerings, teams, SLAs or links.
- If the user names an application that has both a Service and a Support offering, pick by intent
  (broken → Support; needs something → Service). If intent is unclear, "clarify" between the two.
- "recommend" when one offering clearly fits. "clarify" when 2-4 could fit — ask one short question.
  "answer" for general questions, or when nothing fits (say so; suggest browsing categories).
- You never raise tickets yourself. Don't claim you did.
- Remind users not to paste personal or confidential data only when relevant.
- "reply": 1-3 short, plain, professional sentences. **bold** allowed.
- "summary": one-line ticket title in the user's terms (max 90 chars).
- "details": only facts the user actually gave, as short lines. Never invent details.

Respond with JSON only:
{{"action": "recommend" | "clarify" | "answer", "reply": "...", "service_id": "<ID or null>",
 "alternative_ids": ["<ID>"], "option_ids": ["<ID>"], "summary": "...", "details": "..."}}"""


def _catalog_lines(services: list[dict], ranked: list[dict]) -> str:
    # Keyword-ranked candidates first so the model sees the likeliest offerings up top;
    # the rest of the catalog follows while it is small enough to fit comfortably.
    ordered = [r["service"] for r in ranked[:10]]
    if len(services) <= 250:
        ordered += [s for s in services if s not in ordered]
    return "\n".join(f"{s['id']} | {s['category']} | {s['type']} | {s['name']} — {s['description']}" for s in ordered)


def _ai_respond(message: str, history: list[dict], services: list[dict], ranked: list[dict]) -> dict | None:
    by_id = {s["id"]: s for s in services}
    turns = [{"role": "assistant" if h["role"] == "assistant" else "user", "content": h["text"]}
             for h in history if h.get("text")]
    while turns and turns[0]["role"] != "user":  # providers require a user turn first
        turns.pop(0)
    turns.append({"role": "user", "content": f"CATALOG:\n{_catalog_lines(services, ranked)}\n\nUSER MESSAGE:\n{message}"})

    out = llm.complete_json(AI_SYSTEM, turns)
    action, text = out.get("action"), (out.get("reply") or "").strip()

    if action == "recommend" and out.get("service_id") in by_id:
        s = by_id[out["service_id"]]
        reasons = next((r["reasons"] for r in ranked if r["service"]["id"] == s["id"]), [])
        alts = [by_id[i] for i in out.get("alternative_ids") or [] if i in by_id and i != s["id"]][:2]
        reply = _recommend(s, message, reasons, alts)
        if text:
            reply["text"] = text
        if out.get("summary"):
            details = (out.get("details") or message).strip()
            reply["draft"] = {"summary": out["summary"][:90],
                              "description": "\n".join([details, ""] + [f"{f}: " for f in s["fields"]])}
        reply["source"] = "ai"
        return reply

    if action == "clarify":
        ids = [i for i in out.get("option_ids") or [] if i in by_id][:4]
        if len(ids) >= 2:
            return {"type": "text", "source": "ai", "query": message,
                    "text": text or "A few offerings could fit. Which one describes it best?",
                    "options": [_option(by_id[i]) for i in ids]}

    if action == "answer" and text:
        return {"type": "text", "source": "ai", "text": text, "options": MAIN_MENU[:3]}

    return None  # unusable output — caller falls back to rules


def respond(message: str, last_query: str | None = None, history: list[dict] | None = None) -> dict:
    message = message.strip()
    t = _norm(message)
    services = unity_client.get_services()

    if message.startswith("service:"):
        s = next((s for s in services if s["id"] == message.split(":", 1)[1]), None)
        if s:
            return _recommend(s, last_query or s["name"], [], [])
    if message.startswith("menu:") and (reply := _menu(message, services)):
        return reply
    if message.startswith("category:") and (reply := _category(message.split(":", 1)[1], services)):
        return reply

    if m := TICKET_RE.search(message):
        number = m.group(0).upper()
        ticket = unity_client.get_ticket(number)
        if not ticket:
            return {"type": "text", "text": f"I couldn't find **{number}** among your tickets. Check the number, or search for it in Unity.",
                    "link": {"label": f"Search {number} in Unity", "url": unity_client.ticket_url(number)}}
        svc = next((s for s in services if s["id"] == ticket.get("service_id")), None)
        return {"type": "ticket", "text": f"Here's the latest on **{number}**.", "ticket": ticket, "service": svc}

    if re.search(r"\b(my (tickets|requests|incidents|support cases)|open tickets|ticket status|status of my)\b", t):
        tickets = unity_client.get_my_tickets()
        open_ = [x for x in tickets if x["state"] not in ("Resolved", "Closed", "Cancelled")]
        return {"type": "tickets", "text": f"You have **{len(open_)} open** of {len(tickets)} recent tickets. Select one for details.", "tickets": tickets}

    if re.match(r"^ (hi|hello|hey|good (morning|afternoon|evening))\b", t) and len(t.split()) <= 4:
        return {"type": "text", "text": "Hello! How can I help you today?", "options": MAIN_MENU}
    if re.search(r"\b(thanks|thank you|thx|cheers|merci)\b", t):
        return {"type": "text", "text": "You're welcome. Anything else I can help with?", "options": MAIN_MENU[:3]}
    if re.search(r"\b(what can you do|how does this work|capabilities)\b", t):
        return {"type": "text", "text": (
            "I can:\n- Find the right Unity offering for your issue or request\n"
            "- Tell you what to keep ready and draft the ticket text\n"
            "- Take you straight to the offering in Unity\n"
            "- Check a ticket's status — just paste its number")}

    ranked = score_services(message, services)

    if llm.enabled():
        try:
            if reply := _ai_respond(message, history or [], services, ranked):
                return reply
        except Exception as exc:  # network, quota, bad JSON — fall back to rules
            log.warning("LLM call failed, using rule-based matcher: %s", exc)

    if not ranked:
        return {"type": "text", "text": "I couldn't match that to an offering yet. Could you name the application, or pick an option below?",
                "options": MAIN_MENU}

    top = ranked[0]
    close = [r for r in ranked[1:4] if r["score"] >= top["score"] * 0.8]
    if top["score"] < CONFIDENT_SCORE or close:
        picks = [top, *close][:4]
        same_app = len(picks) == 2 and {p["service"]["type"] for p in picks} == {"Service", "Support"}
        question = ("Is something not working, or do you need something set up?" if same_app
                    else "A few offerings could fit. Which one describes it best?")
        return {"type": "text", "text": question, "options": [_option(r["service"]) for r in picks], "query": message}

    alternatives = [r["service"] for r in ranked[1:3] if r["score"] >= 3]
    return _recommend(top["service"], message, top["reasons"], alternatives)
