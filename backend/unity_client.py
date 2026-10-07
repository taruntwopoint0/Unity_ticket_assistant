"""Unity (SMAX) API adapter.

Set UNITY_API_BASE (and optionally UNITY_API_TOKEN) to read live data. Without it,
the bundled sample catalog is used so the app runs offline. Adjust the paths and
field mapping in this file only — the rest of the app consumes the shapes below:

  category: {id, name, description, offerings: [offering]}
  offering: {id, type: "Service"|"Support", name, description, keywords, fields}
  ticket:   {number, service_id, short, state, assigned_to, opened, updated, last_note}
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from sample_data import CATEGORIES, MY_TICKETS

API_BASE = (os.getenv("UNITY_API_BASE") or "").rstrip("/")
API_TOKEN = os.getenv("UNITY_API_TOKEN") or ""
PORTAL_BASE = (os.getenv("UNITY_PORTAL_BASE") or "https://unity.example.com").rstrip("/")


def is_live() -> bool:
    return bool(API_BASE)


def _get(path: str):
    req = urllib.request.Request(f"{API_BASE}{path}", headers={"Accept": "application/json"})
    if API_TOKEN:
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.load(res)


def _q(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def offering_url(offering_id: str) -> str:
    return f"{PORTAL_BASE}/saw/ess/offeringPage/{_q(offering_id)}"


def category_url(category_id: str) -> str:
    return f"{PORTAL_BASE}/saw/ess/categoryPage/{_q(category_id)}"


def ticket_url(number: str) -> str:
    return f"{PORTAL_BASE}/saw/ess/myRequests?search={_q(number)}"


def get_categories() -> list[dict]:
    return _get("/categories") if is_live() else CATEGORIES


def get_services() -> list[dict]:
    """Categories -> offerings, flattened with parent context, a portal link and where to raise it."""
    return [
        {**o, "category_id": c["id"], "category": c["name"], "url": offering_url(o["id"]),
         "raise_path": f"{o.get('portal') or 'Unity Service Portal'} › {c['name']} › {o['name']}"}
        for c in get_categories()
        for o in c["offerings"]
    ]


def get_my_tickets() -> list[dict]:
    tickets = _get("/requests?requester=me") if is_live() else MY_TICKETS
    return [{**t, "url": ticket_url(t["number"])} for t in tickets]


def get_ticket(number: str) -> dict | None:
    number = number.upper()
    if not is_live():
        t = next((t for t in MY_TICKETS if t["number"] == number), None)
    else:
        try:
            t = _get(f"/requests/{_q(number)}")
        except urllib.error.HTTPError:
            t = None
    return {**t, "url": ticket_url(t["number"])} if t else None
