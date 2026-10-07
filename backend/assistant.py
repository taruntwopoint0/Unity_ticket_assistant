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

import knowledge_base as kb
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
                 "problem", "won't", "wont", "doesn't", "doesnt", "failed", "failing", "stuck", "crash", "slow", "keeps", "stopped", "not loading"]
REQUEST_SIGNALS = ["need", "request", "new", "want", "install", "access", "create", "creation", "add",
                   "apply", "get a", "require", "change", "enable", "onboard"]
WEAK_REQUEST = {"need", "want", "new", "create"}  # also common in "I want to raise a ticket for ... not working"
TICKET_RE = re.compile(r"\b(INC|REQ|RITM|CHG|PRB|SD)\d{5,}\b", re.I)
CONFIDENT_SCORE = 5
GDPR_NOTE = "Don't include personal or confidential data in the ticket (GDPR)."

GUIDE_RE = re.compile(r"\b(create|raise|open|log|submit|file|make)\b.{0,25}\b(ticket|incident|request|case)\b|\b(guide|walk) me\b", re.I)
# "I want to raise a support ticket", "show me the incident tickets", "what service requests are there?"
SUPPORT_LIST_RE = re.compile(r"\b(support|incident|issue)s?\b.{0,15}\b(ticket|offering|type|option|categor)|"
                             r"\b(raise|open|log|declare|report|create)\b.{0,12}\b(an? )?(support|incident|issue)\b", re.I)
SERVICE_LIST_RE = re.compile(r"\bservice (request|offering|ticket)s?\b|\b(request|req) (ticket|offering)s?\b", re.I)
LIST_WORDS = {"support", "incident", "issue", "service", "request", "req", "ticket", "offering", "type", "kind", "option",
              "list", "show", "see", "available", "all", "raise", "open", "log", "declare", "report", "create", "want",
              "like", "you", "there", "exist", "categor", "category", "different", "give", "tell", "about", "could", "would"}
# "who supports Eloqua?", "which support group handles CRM issues?", "where do I raise a VPN ticket?"
ROUTING_RE = re.compile(r"\b(who (supports|handles|owns|looks after|manages|fixes|is responsible)|support (group|team)|"
                        r"which (team|group)|assignment group|resolver group|responsible team|"
                        r"(where|which portal) (do|should|can) i (raise|log|open|create|submit))\b", re.I)
QUESTION_RE = re.compile(r"^ (how|what|where|why|when|who|can|could|do|does|is|are|should|which) ")
KB_CONFIDENT = 4

MAIN_MENU = [
    {"label": "Raise a new ticket", "value": "menu:raise"},
    {"label": "Something isn't working (incident)", "value": "menu:issue"},
    {"label": "I need something (request)", "value": "menu:request"},
    {"label": "Access / user creation", "value": "menu:access"},
    {"label": "How do I…?", "value": "menu:howto"},
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
    if re.search(r" (support (ticket|offering|case)|incident)", t):
        return "Support"
    if re.search(r" service (request|ticket|offering)", t):
        return "Service"
    issue = any(f" {s}" in t for s in ISSUE_SIGNALS)
    request = any(f" {s}" in t for s in REQUEST_SIGNALS if s not in WEAK_REQUEST)
    if issue and not request:
        return "Support"
    request = request or any(f" {s}" in t for s in WEAK_REQUEST)
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


def _recommend(service: dict, message: str, reasons: list[str], alternatives: list[dict]) -> dict:
    doc = kb.for_offering(service)
    if service["type"] == "Support":
        text = f"Raise **{service['name']}** — the Support Offering in {service['category']} for declaring this issue."
    else:
        text = f"Raise **{service['name']}** — the Service Offering in {service['category']} for this request."
    text += f" The steps are in **{doc['id']} – {doc['title']}** below."
    docs = [_article(doc)]
    self_help = next((a for a in kb.ARTICLES if service["id"] in a["offering_ids"] and a["id"].startswith("KB2")), None)
    if self_help:
        docs.append(_article(self_help))
    return {
        "type": "recommendation", "text": text, "service": service, "reasons": reasons,
        "alternatives": alternatives, "notice": GDPR_NOTE, "articles": docs,
    }


def _offerings_list(kind: str | None, services: list[dict], category_id: str | None = None, ids: list[str] | None = None) -> dict:
    """Offerings of one type (or the given IDs), grouped by category, each with a plain "raise this when…" line."""
    picks = [s for s in services if (not kind or s["type"] == kind) and (not category_id or s["category_id"] == category_id)
             and (not ids or s["id"] in ids)]
    n = f"{len(picks)} {kind + ' ' if kind else ''}offering{'' if len(picks) == 1 else 's'}"
    groups: dict[str, list] = {}
    for s in picks:
        groups.setdefault(s["category"], []).append(
            {"id": s["id"], "name": s["name"], "type": s["type"], "use_when": s.get("use_when") or s["description"],
             "support_group": s.get("support_group")})
    if kind == "Support":
        text = (f"Here {'is' if len(picks) == 1 else 'are'} the **{n}** — raise one when something is broken or not working; "
                "it creates an **INC** incident. Pick the one that matches, or just tell me what's wrong and I'll choose for you.")
    elif kind == "Service":
        text = (f"Here {'is' if len(picks) == 1 else 'are'} the **{n}** — raise one when you need something (access, a change, "
                "a new item); it creates a **REQ** request and may need approval. Pick one, or tell me what you need.")
    else:
        text = f"Here {'is' if len(picks) == 1 else 'are'} the **{n}**. Pick one, or tell me what you need and I'll choose for you."
    return {"type": "offerings", "text": text, "kind": kind,
            "groups": [{"category": c, "offerings": o} for c, o in groups.items()]}


def _routing(service: dict, alternatives: list[dict] | None = None) -> dict:
    """Answer "who handles / where do I raise" for one offering: its support group, hours and portal path."""
    reply = _recommend(service, service["name"], [], alternatives or [])
    group = service.get("support_group") or "the team behind this offering"
    hours = f" ({service['support_hours']})" if service.get("support_hours") else ""
    reply["text"] = (f"**{service['name']}** tickets go to **{group}**{hours}. Raise it in "
                     f"**{service.get('raise_path') or service['category']}** — Unity routes it to them automatically. "
                     f"The steps are in **{reply['articles'][0]['id']} – {reply['articles'][0]['title']}** below.")
    return reply


def _menu(value: str, services: list[dict]) -> dict | None:
    kind = value.split(":", 1)[1]
    if kind == "raise":
        return _offerings_list(None, services)
    if kind == "howto":
        picks = ["KB1001", "KB1002", "KB1003", "KB1004", "KB1005", "KB1007", "KB1009"]
        return {"type": "text", "text": "Here are the most common questions. Pick one, or just ask in your own words.",
                "options": [{"label": kb.get(i)["title"], "value": f"kb:{i}"} for i in picks]}
    if kind == "issue":
        return _offerings_list("Support", services)
    if kind == "request":
        return _offerings_list("Service", services)
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


def _article(a: dict) -> dict:
    return {k: a.get(k) for k in ("id", "title", "summary", "steps", "tip", "link")}


def _article_reply(a: dict, services: list[dict], text: str | None = None) -> dict:
    by_id = {s["id"]: s for s in services}
    offerings = [by_id[i] for i in a["offering_ids"] if i in by_id]
    reply = {"type": "text", "text": text or f"See **{a['id']} – {a['title']}** below for the steps.",
             "articles": [_article(a)]}
    if offerings:
        reply["options"] = [_option(s) for s in offerings[:3]]
        reply["options_label"] = "Still need help? Raise"
    return reply


AI_SYSTEM = f"""You are the Unity Assistant, an internal IT helpdesk assistant on the Unity Service Portal.
Employees raise tickets in Unity by choosing an offering inside a category (e.g. Business Applications).
Offerings are either:
  - Support Offering: declare an issue — something that worked is broken, erroring, slow or down (creates an INC).
  - Service Offering: request something — access, user creation, a change, a new item (creates a REQ).

STEP 1 — understand the message before answering. Use the conversation so far for context
(e.g. "and for Teams?" continues the previous topic). Decide the intent:
  - "ticket_need": the user has a problem or needs something that requires a ticket.
  - "create_ticket": the user explicitly wants to create/raise/open a ticket now.
  - "how_to": a question about using Unity or the ticket process (statuses, approvals, urgency, reopening...).
  - "my_tickets": a question about one of the user's existing tickets (see MY TICKETS).
  - "general": a general IT or workplace question (e.g. "what is a VPN?", "how do I clear the Teams cache?").
  - "browse": the user wants to see which tickets / offerings exist (e.g. "what support tickets can I raise?",
    "which incident tickets are there for servers?") rather than solving a specific problem.
  - "other": small talk or off-topic.

STEP 2 — answer:
  - ticket_need → "recommend" when one offering clearly fits; "clarify" when 2-4 could fit (ask one short question).
    If the KNOWLEDGE BASE has self-help steps for the problem, mention them briefly in "reply" and cite the article.
  - create_ticket → "recommend" when you know the offering. If the application has both a Support and a
    Service offering and the type is unclear, "clarify" with both. If you can't tell the area at all, "list".
  - how_to → "answer" grounded on the KNOWLEDGE BASE; cite the article IDs you used.
  - my_tickets → "answer" using MY TICKETS: the state, what it means and what the user should do next.
  - general → "answer" from your general IT knowledge, practical and short. If it might need a ticket, set service_id.
  - browse → "list" with "list_type" "Support" (broken / incidents), "Service" (requests) or null (both), and
    "category_id" if they named a category (business-apps, server-compute, storage-backup, workplace), else null.
    If they asked about a specific area or application (e.g. "marketing tools" → Eloqua), put the matching
    offering IDs in "option_ids"; leave it empty to list everything of that type / category.
  - other → "answer" briefly and politely, then steer back to what you can help with.

Rules:
- Only use offering IDs from CATALOG and article IDs from KNOWLEDGE BASE. Never invent offerings, teams,
  SLAs, phone numbers, links or ticket numbers. Facts about Unity must come from the KNOWLEDGE BASE.
- If the user names an application with both a Service and a Support offering, pick by intent
  (broken → Support; needs something → Service). If intent is unclear, "clarify" between the two.
- Questions about who supports something, which support group / team handles it, or where (which portal)
  to raise it → "recommend" that offering; in "reply" name its support group, support hours and "raise in"
  path exactly as given in CATALOG. Users never pick the group themselves — Unity routes the ticket.
- You never raise, change or close tickets yourself. Don't claim you did.
- Remind users not to share personal or confidential data only when relevant (GDPR).
- Don't ask the user questions or interview them for ticket details — show the right ticket or list instead.
- "reply": plain and professional, 1-2 sentences. Never write out steps or procedures from the KNOWLEDGE BASE —
  the app shows the cited document next to your reply, so refer to it by ID and title instead
  (e.g. "The steps are in KB1005 – How approvals work."). For a recommend, the app attaches the offering's
  "How to raise" document automatically. For general IT questions with no matching article, up to ~4 short lines
  are fine. **bold** allowed. No headings, no links.
- "summary": one-line ticket title in the user's terms (max 90 chars) — recommend only.
- "details": only facts the user actually gave, as short lines. Never invent details.

Respond with JSON only:
{{"intent": "...", "action": "recommend" | "clarify" | "answer" | "list", "list_type": null, "category_id": null, "reply": "...", "service_id": "<ID or null>",
 "alternative_ids": ["<ID>"], "option_ids": ["<ID>"], "article_ids": ["<KB ID>"],
 "summary": "...", "details": "..."}}"""


def _catalog_lines(services: list[dict], ranked: list[dict]) -> str:
    # Keyword-ranked candidates first so the model sees the likeliest offerings up top;
    # the rest of the catalog follows while it is small enough to fit comfortably.
    ordered = [r["service"] for r in ranked[:10]]
    if len(services) <= 250:
        ordered += [s for s in services if s not in ordered]
    return "\n".join(f"{s['id']} | {s['category']} | {s['type']} | {s['name']} — {s.get('use_when') or s['description']}"
                     f" | support group: {s.get('support_group') or 'unknown'} ({s.get('support_hours') or '-'})"
                     f" | raise in: {s.get('raise_path') or s['category']}" for s in ordered)


def _ai_respond(message: str, history: list[dict], services: list[dict], ranked: list[dict]) -> dict | None:
    by_id = {s["id"]: s for s in services}
    turns = [{"role": "assistant" if h["role"] == "assistant" else "user", "content": h["text"]}
             for h in history if h.get("text")]
    while turns and turns[0]["role"] != "user":  # providers require a user turn first
        turns.pop(0)
    context = message + " " + " ".join(t["content"] for t in turns[-2:])
    articles = [r["article"] for r in kb.search(context, k=4)]
    others = ", ".join(f"{a['id']} {a['title']}" for a in kb.ARTICLES if a not in articles)
    tickets = "\n".join(f"{t['number']} | {t['state']} | {t['short']} | team: {t['assigned_to']} | last note: {t['last_note']}"
                        for t in unity_client.get_my_tickets())
    found = "\n".join(kb.as_text(a) for a in articles) or "(no match)"
    turns.append({"role": "user", "content": (
        f"CATALOG:\n{_catalog_lines(services, ranked)}\n\n"
        f"KNOWLEDGE BASE (most relevant first):\n{found}\nOther articles: {others}\n\n"
        f"MY TICKETS:\n{tickets or '(none)'}\n\nUSER MESSAGE:\n{message}")})

    out = llm.complete_json(AI_SYSTEM, turns)
    action, text = out.get("action"), (out.get("reply") or "").strip()
    cited = [_article(a) for i in out.get("article_ids") or [] if (a := kb.get(str(i), services))][:2]

    if action == "recommend" and out.get("service_id") in by_id:
        s = by_id[out["service_id"]]
        reasons = next((r["reasons"] for r in ranked if r["service"]["id"] == s["id"]), [])
        alts = [by_id[i] for i in out.get("alternative_ids") or [] if i in by_id and i != s["id"]][:2]
        reply = _recommend(s, message, reasons, alts)
        if text:
            doc = reply["articles"][0]
            reply["text"] = text if doc["id"] in text else f"{text} The steps are in **{doc['id']} – {doc['title']}** below."
        reply["source"] = "ai"
        reply["articles"] += [a for a in cited if a["id"] not in {d["id"] for d in reply["articles"]}][:1]
        return reply

    if action == "list":
        kind = out.get("list_type") if out.get("list_type") in ("Support", "Service") else None
        cat = out.get("category_id") if any(s["category_id"] == out.get("category_id") for s in services) else None
        ids = [i for i in out.get("option_ids") or [] if i in by_id]
        reply = _offerings_list(kind, services, cat, ids)
        if not reply["groups"]:
            reply = _offerings_list(kind, services, cat)
        reply["source"] = "ai"
        return reply

    if action == "clarify":
        ids = [i for i in out.get("option_ids") or [] if i in by_id][:4]
        if len(ids) >= 2:
            reply = _offerings_list(None, services, ids=ids)
            reply.update(source="ai", query=message, text=text or "These tickets fit — raise the one that matches.")
            return reply

    if action == "answer" and text:
        reply = {"type": "text", "source": "ai", "text": text}
        if cited:
            reply["articles"] = cited
        if out.get("service_id") in by_id:
            reply["options"] = [_option(by_id[out["service_id"]])]
            reply["options_label"] = "If you need a ticket"
        elif not cited and out.get("intent") in ("other", None):
            reply["options"] = MAIN_MENU[:4]
        numbers = {m.group(0).upper() for m in TICKET_RE.finditer(text)}
        if len(numbers) == 1 and (ticket := unity_client.get_ticket(numbers.pop())):
            reply.update(type="ticket", ticket=ticket, help=kb.STATE_HELP.get(ticket["state"]),
                         service=by_id.get(ticket.get("service_id")))
        return reply

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
    if message.startswith("kb:") and (a := kb.get(message[3:], services)):
        return _article_reply(a, services, f"Here's how it works: **{a['title']}**.")
    if message.startswith("category:") and (reply := _category(message.split(":", 1)[1], services)):
        return reply

    if m := TICKET_RE.search(message):
        number = m.group(0).upper()
        ticket = unity_client.get_ticket(number)
        if not ticket:
            return {"type": "text", "text": f"I couldn't find **{number}** among your tickets. Check the number, or search for it in Unity.",
                    "link": {"label": f"Search {number} in Unity", "url": unity_client.ticket_url(number)}}
        svc = next((s for s in services if s["id"] == ticket.get("service_id")), None)
        return {"type": "ticket", "text": f"Here's the latest on **{number}**.", "ticket": ticket, "service": svc,
                "help": kb.STATE_HELP.get(ticket["state"])}

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
            "- Show you the ticket to raise, with the knowledge document that explains the steps\n"
            "- List the Support (incident) and Service (request) tickets you can raise\n"
            "- Tell you which support group handles a ticket and where to raise it\n"
            "- Answer how-to questions from the knowledge base\n"
            "- Take you straight to the offering in Unity\n"
            "- Check a ticket's status — just paste its number")}

    if ROUTING_RE.search(message):
        ranked = score_services(message, services)
        named = [r for r in ranked if r["score"] >= 3]
        if named:
            apps = [r["service"] for r in named if _tokens(r["service"]["name"], drop_generic=True) & _tokens(message)] or [named[0]["service"]]
            kind = detect_type(message) or "Support"
            main = next((s for s in apps if s["type"] == kind), apps[0])
            others = [s for s in apps if s is not main and s.get("support_group") == main.get("support_group")][:1]
            return _routing(main, others)
        if not llm.enabled():
            groups = sorted({s.get("support_group") for s in services if s.get("support_group")})
            return {"type": "offerings", "text": f"Every ticket in Unity is routed to one of **{len(groups)} support groups**. "
                    "Here is which group handles each one — or name the application and I'll tell you.",
                    "groups": _offerings_list(None, services)["groups"]}

    list_kind = "Support" if SUPPORT_LIST_RE.search(message) else "Service" if SERVICE_LIST_RE.search(message) else None
    if list_kind and not _tokens(message, drop_generic=True) - LIST_WORDS:
        return _offerings_list(list_kind, services)

    wants_ticket = bool(GUIDE_RE.search(message))
    vague = not _tokens(message, drop_generic=True) - LIST_WORDS - {"new", "make", "file", "submit", "case", "i'd"}
    if wants_ticket and vague and not QUESTION_RE.match(t):
        return _offerings_list(None, services)  # "I want to create a ticket" — show every ticket to pick from
    ranked = score_services(message, services)

    if llm.enabled():
        try:
            if reply := _ai_respond(message, history or [], services, ranked):
                return reply
        except Exception as exc:  # network, quota, bad JSON — fall back to rules
            log.warning("LLM call failed, using rule-based matcher: %s", exc)

    # "my VPN ticket", "why is my iController request not done?" — find the ticket the user means.
    if re.search(r"\bmy\b.{0,40}\b(ticket|request|incident|case)\b", t):
        words = _tokens(message, drop_generic=True) - {"ticket", "case"}
        mine = [x for x in unity_client.get_my_tickets()
                if words & _tokens(f"{x['short']} {x['service_id']} {x['assigned_to']}", drop_generic=True)]
        if len(mine) == 1:
            svc = next((s for s in services if s["id"] == mine[0].get("service_id")), None)
            return {"type": "ticket", "text": f"Here's the latest on **{mine[0]['number']}**.", "ticket": mine[0],
                    "service": svc, "help": kb.STATE_HELP.get(mine[0]["state"])}

    hits = kb.search(message)
    top_kb =hits[0] if hits and hits[0]["score"] >= KB_CONFIDENT else None
    if top_kb and (QUESTION_RE.match(t) or "?" in message) and (not ranked or top_kb["score"] >= ranked[0]["score"] - 2):
        return _article_reply(top_kb["article"], services)

    if not ranked:
        if wants_ticket:
            return _offerings_list(None, services)
        return {"type": "text", "text": "I couldn't match that to an offering yet. Could you name the application, or pick an option below?",
                "options": MAIN_MENU}

    top = ranked[0]
    close = [r for r in ranked[1:4] if r["score"] >= top["score"] * 0.8]
    if top["score"] < CONFIDENT_SCORE or close:
        picks = [top, *close][:4]
        same_app = len(picks) == 2 and {p["service"]["type"] for p in picks} == {"Service", "Support"}
        reply = _offerings_list(None, services, ids=[p["service"]["id"] for p in picks])
        reply.update(query=message, text=(
            "There's a **Support** ticket (something is broken) and a **Service** ticket (you need something) — raise the one that matches."
            if same_app else "These tickets fit — raise the one that matches."))
        return reply

    alternatives = [r["service"] for r in ranked[1:3] if r["score"] >= 3]
    return _recommend(top["service"], message, top["reasons"], alternatives)
