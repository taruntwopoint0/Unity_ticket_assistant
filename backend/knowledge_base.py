"""Mock knowledge base for the Unity Assistant.

Short how-to articles: raising and following tickets in Unity, and self-help to try
before declaring an issue. The assistant retrieves the best matches for a message
(simple keyword scoring, no extra dependencies) and grounds its answers on them.

All content is generic demo material — replace it with your organisation's real
knowledge articles (or load them from the Unity KB API) before going live.
"""
import re


def _kb(id, title, summary, steps, keywords=(), offering_ids=(), tip=None):
    return {"id": id, "title": title, "summary": summary, "steps": list(steps),
            "keywords": list(keywords), "offering_ids": list(offering_ids), "tip": tip}


ARTICLES = [
    _kb("KB1001", "How to raise a ticket in Unity",
        "Every ticket starts from an offering in the Unity Service Portal.",
        ["Open the Unity Service Portal and use the search bar, or pick a category tile on the home page.",
         "Choose the offering that matches your need — a **Support** offering if something is broken, a **Service** offering if you are requesting something.",
         "Fill in the **Title** with a short summary (e.g. \"Eloqua campaign won't publish\").",
         "In **Description**, explain what happens, since when and what you already tried.",
         "For Support offerings, set the **Urgency** (see KB1003).",
         "Attach screenshots or logs if useful — never personal data.",
         "Click **Submit**. You receive an INC (incident) or REQ (request) number by email."],
        ["raise", "create", "open", "log", "submit", "new ticket", "raise a ticket", "create a ticket", "how to", "portal", "form"],
        tip="Not sure which offering? Ask the Unity Assistant — it suggests one and drafts the text for you."),
    _kb("KB1002", "Service offering or Support offering — which one?",
        "Unity has two kinds of offerings and choosing the right one routes your ticket faster.",
        ["**Support offering** (declare an issue): something that used to work is broken, erroring, slow or down. Creates an **INC** incident.",
         "**Service offering** (request something): access, a new user, software, a change, a restore. Creates a **REQ** request and may need approval.",
         "Most applications have both, e.g. *Eloqua - Support* and *Eloqua - Service Request*.",
         "If you pick the wrong one, the support team can re-route it, but it adds delay."],
        ["service", "support", "difference", "which offering", "incident", "request", "offering type", "inc", "req"]),
    _kb("KB1003", "Setting urgency on an incident",
        "Urgency tells the support team how fast you need help. Be honest — it drives the response time.",
        ["**Low** — minor issue, you have a workaround. Target response: 3 business days.",
         "**Medium** — your work is slowed down. Target response: 1 business day.",
         "**High** — you cannot work and there is no workaround. Target response: 4 hours.",
         "**Critical** — a whole team or a business process is stopped. Also call the Service Desk (KB1008)."],
        ["urgency", "priority", "impact", "sla", "how fast", "response time", "critical", "urgent"]),
    _kb("KB1004", "Following up on your tickets",
        "All your tickets are listed under My Requests in Unity.",
        ["Open Unity and click **My Requests** (top right), or ask the assistant \"my tickets\".",
         "Click a ticket to see its status, the assigned team and the latest notes.",
         "**New** — received, waiting to be picked up by the support team.",
         "**In progress** — an engineer is working on it; watch for questions in the notes.",
         "**Awaiting approval** — your manager or the application owner must approve it (KB1005).",
         "**Pending user** — the engineer is waiting for *your* reply; the ticket is on hold until you answer.",
         "**Resolved** — a fix was applied; it closes automatically after 5 days unless you reopen it (KB1007)."],
        ["status", "my tickets", "my requests", "follow up", "track", "progress", "pending", "new", "in progress", "resolved", "where is my ticket"]),
    _kb("KB1005", "How approvals work",
        "Service requests for access, licences or admin rights need approval before the team can start.",
        ["After you submit, Unity sends an approval task to your line manager (and the application owner for some apps).",
         "The approver gets an email and can approve directly from it or from **My Approvals** in Unity.",
         "The ticket shows **Awaiting approval** until then. Nothing happens on the support side before approval.",
         "If it is stuck for more than 2 business days, remind your approver — the support team cannot approve on their behalf.",
         "If the request is rejected, the reason is shown on the ticket; raise a new one with the missing information."],
        ["approval", "approve", "approver", "manager", "awaiting approval", "stuck", "rejected", "waiting"]),
    _kb("KB1006", "Replying to the engineer and adding attachments",
        "Keep everything on the ticket so the whole support team can see it.",
        ["Open the ticket from **My Requests** or from the link in the notification email.",
         "Type your answer in the **Comments** box and click **Add comment**.",
         "Use **Attach** to add screenshots or log files (max 10 MB each). Remove personal data first.",
         "Replying moves a *Pending user* ticket back to *In progress* automatically."],
        ["reply", "comment", "attach", "attachment", "screenshot", "logs", "answer engineer", "add information", "update ticket", "awaiting your reply"]),
    _kb("KB1007", "Reopening or cancelling a ticket",
        "You can reopen a resolved ticket within 5 days, or cancel one you no longer need.",
        ["**Reopen**: open the resolved ticket, click **Reopen**, and explain what still doesn't work.",
         "After 5 days the ticket is closed — raise a new one and mention the old number in the description.",
         "**Cancel**: open the ticket and click **Withdraw** (only possible before work has started).",
         "If Withdraw is not available, add a comment asking the team to cancel it."],
        ["reopen", "re-open", "cancel", "withdraw", "close", "closed", "not fixed", "still broken", "no longer needed"]),
    _kb("KB1008", "Escalating an urgent issue",
        "For business-critical outages, don't rely on the ticket alone.",
        ["Raise the incident in Unity with urgency **Critical** so it is tracked.",
         "Call the Service Desk on the number shown on the Unity home page and quote the INC number.",
         "For an existing ticket that is late, add a comment explaining the business impact and ask for escalation.",
         "Your manager can also escalate through the Service Desk."],
        ["escalate", "escalation", "urgent", "outage", "everyone", "whole team", "late", "no response", "service desk", "call"]),
    _kb("KB2001", "VPN keeps disconnecting",
        "Try these steps before declaring a workstation incident.",
        ["Check your home internet works without the VPN (open any public website).",
         "Disconnect the VPN, close the client completely and reconnect.",
         "Restart your laptop — pending updates often cause drops.",
         "Use a cable or move closer to the router if you are on Wi-Fi.",
         "Still dropping? Raise **Workplace - Workstation incident** with your machine name and the times it dropped."],
        ["vpn", "disconnect", "drops", "dropping", "remote", "home", "connection", "network", "internet"],
        ["WP-INC"]),
    _kb("KB2002", "Outlook or Teams not working",
        "Most Outlook and Teams problems are fixed by a restart or cache reset.",
        ["Close Outlook / Teams fully (also from the system tray) and reopen it.",
         "Check the web version (Outlook on the web / Teams web) — if it works, the issue is your local app.",
         "For Teams: sign out, close it, and sign in again to rebuild the cache.",
         "Restart your laptop and make sure it is connected to the VPN or office network.",
         "Still broken? Raise **Workplace - Workstation incident** and attach a screenshot of the error."],
        ["outlook", "teams", "email", "mail", "calendar", "meeting", "not syncing", "crash", "cache"],
        ["WP-INC"]),
    _kb("KB2003", "Forgotten password or locked account",
        "You can reset your own password without a ticket.",
        ["Go to the self-service password reset page linked on the Windows sign-in screen and Unity home page.",
         "Verify your identity with the method you registered (authenticator app or SMS).",
         "Choose a new password that follows the password policy (12+ characters).",
         "Locked out after too many attempts? Wait 15 minutes, then try again.",
         "If self-service fails, raise **Workplace - Workstation incident** — or call the Service Desk if you cannot log in at all."],
        ["password", "reset", "forgot", "forgotten", "locked", "lockout", "login", "log in", "sign in", "expired"],
        ["WP-INC"]),
    _kb("KB3001", "Requesting access to an application",
        "Access is requested with the application's Service offering and needs approval.",
        ["Search the application name in Unity and open its access or user-creation offering (e.g. *iController - Access*, *DocuSign - User Creation*).",
         "Say whether you need **new** access, a **change** of role, or a **removal**.",
         "Name the role or profile you need — ask a colleague who already uses the app if unsure.",
         "Submit; your manager receives the approval (KB1005).",
         "Once approved, the application team creates the access, usually within 2 business days."],
        ["access", "account", "user creation", "new user", "role", "permission", "license", "licence", "onboard", "join"],
        ["ICONTROLLER-ACC", "DOCUSIGN-USER", "CRM-SR"]),
    _kb("KB3002", "Getting temporary local admin rights (PAR)",
        "Local admin rights (PAR) are granted temporarily to install or configure software.",
        ["First check the Software Center — most approved software installs without admin rights.",
         "If you still need admin rights, raise **[WIN] Local admin (PAR) access**.",
         "Give your machine name, how long you need it (max 7 days) and why.",
         "After approval, sign out and back in so the rights apply."],
        ["admin", "admin rights", "local admin", "par", "install", "software", "administrator", "elevated"],
        ["WIN-PAR", "WP-GENERIC"]),
    _kb("KB3003", "Restoring a deleted or overwritten file",
        "Many files can be recovered without a ticket.",
        ["OneDrive / SharePoint: open the **Recycle bin** in the web view, or use **Version history** on the file.",
         "Network share: right-click the folder → **Properties** → **Previous versions**.",
         "If neither works, raise **Backup - Restore request** with the full path and the date to restore from.",
         "Restores from backup are kept for 30 days back."],
        ["restore", "deleted", "delete", "recover", "overwritten", "lost file", "backup", "previous version", "recycle bin"],
        ["INFRA-RESTORE"]),
    _kb("KB3004", "Requesting a new or bigger virtual machine",
        "Servers and VMs are requested through the Server & Compute category.",
        ["Raise **Virtual machine - New / resize**.",
         "Give the environment (dev / uat / prod), CPU, RAM and disk, and the cost centre.",
         "Production VMs need approval from the application owner.",
         "For a server that is down or slow, raise **Server - Incident** instead."],
        ["vm", "virtual machine", "server", "resize", "cpu", "ram", "disk", "provision", "environment"],
        ["INFRA-VM-NEW", "INFRA-SRV-INC"]),
    _kb("KB1009", "Writing a good ticket (and what not to include)",
        "A clear ticket is resolved faster and avoids back-and-forth.",
        ["Title: what is wrong or what you need, in a few words.",
         "Say **what** happens, **since when**, **how many users** are affected and what you already tried.",
         "Add the exact error message or a screenshot.",
         "**Never** include personal or confidential data: no passwords, ID numbers, customer names or bank details (GDPR)."],
        ["good ticket", "describe", "description", "what to write", "gdpr", "personal data", "confidential", "privacy", "information needed"]),
]

# Plain-language explanation of each ticket state, shown on ticket cards.
STATE_HELP = {
    "New": "Received — waiting for the support team to pick it up. No action needed from you.",
    "In progress": "An engineer is working on it. Check the latest note — they may need something from you.",
    "Awaiting approval": "Waiting for your approver. Remind them if it has been more than 2 business days (KB1005).",
    "Pending user": "The engineer is waiting for your reply. Add a comment on the ticket to restart work (KB1006).",
    "Resolved": "A fix was applied. Reopen it within 5 days if the problem is still there (KB1007).",
    "Closed": "Closed — raise a new ticket and mention this number if you need more help.",
    "Cancelled": "Cancelled — nothing more will happen on this ticket.",
}

_STOP = set("a an the i me my we our is are am be to of for in on at and or not with it its this that have has "
            "from can do does how what which should please need want get im dont there".split())


def _words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOP:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def for_offering(s: dict) -> dict:
    """The "How to raise" document for one offering, built from its catalog entry so every offering has one."""
    support = s["type"] == "Support"
    fields = ", ".join(f"**{f}**" for f in s["fields"])
    self_help = next((a for a in ARTICLES if s["id"] in a["offering_ids"] and a["id"].startswith("KB2")), None)
    steps = [
        f"Open the **{s.get('portal') or 'Unity Service Portal'}** and go to the **{s['category']}** category, "
        f"or search for *{s['name']}*.",
        f"Open the **{s['name']}** offering. It is a {s['type']} offering, so it creates "
        + ("an **INC** incident." if support else "a **REQ** request."),
        "Give it a short **Title** — " + ("what is broken, e.g. *\"Campaign won't publish since this morning\"*."
                                          if support else "what you need, e.g. *\"Read access for the finance team\"*."),
        f"Fill in the form: {fields}.",
        "Set the **Urgency** honestly — Low, Medium, High or Critical (KB1003)." if support
        else "Name the approver if asked — access and licence requests need manager approval (KB1005).",
        "Attach a screenshot or log if it helps. Never include personal or confidential data (GDPR).",
        f"Click **Submit**. You get the {'INC' if support else 'REQ'} number by email and can follow it under **My Requests** (KB1004).",
    ]
    if s.get("support_group"):
        steps.insert(2, f"The ticket is routed automatically to **{s['support_group']}**"
                        + (f" ({s['support_hours']})" if s.get("support_hours") else "") + " — you don't pick the group.")
    return {
        "id": f"KB-{s['id']}", "title": f"How to raise: {s['name']}",
        "summary": f"Use this {s['type']} offering when: {s.get('use_when') or s['description']}."
                   + (f" Raise it in {s['raise_path']}." if s.get("raise_path") else ""),
        "steps": steps, "keywords": [], "offering_ids": [s["id"]],
        "tip": f"Before raising, try the self-help in {self_help['id']} — {self_help['title']}." if self_help else None,
        "link": {"label": f"Open {s['name']} in Unity", "url": s.get("url")} if s.get("url") else None,
    }


def get(article_id: str, services: list[dict] | None = None) -> dict | None:
    article_id = article_id.upper()
    if article_id.startswith("KB-") and services:
        s = next((s for s in services if s["id"].upper() == article_id[3:]), None)
        return for_offering(s) if s else None
    return next((a for a in ARTICLES if a["id"] == article_id), None)


def search(query: str, k: int = 3) -> list[dict]:
    """Best-matching articles with a relevance score; phrase keywords weigh most."""
    text, words = " " + " ".join(re.findall(r"[a-z0-9-]+", query.lower())) + " ", _words(query)
    ranked = []
    for a in ARTICLES:
        score = 0.0
        for kw in a["keywords"]:
            if " " in kw:
                score += 4 if f" {kw} " in text else 0
            elif _words(kw) & words:
                score += 2
        score += 1.5 * len(_words(a["title"]) & words)
        score += 0.3 * min(len(_words(" ".join(a["steps"])) & words), 5)
        if score:
            ranked.append({"article": a, "score": score})
    return sorted(ranked, key=lambda r: r["score"], reverse=True)[:k]


def as_text(a: dict) -> str:
    steps = "\n".join(f"  {i}. {s}" for i, s in enumerate(a["steps"], 1))
    return f"[{a['id']}] {a['title']} — {a['summary']}\n{steps}" + (f"\n  Tip: {a['tip']}" if a.get("tip") else "")
