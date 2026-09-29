"""Sample catalog shaped like the Unity (SMAX) Service Portal.

Unity groups offerings into categories (the tiles on the portal home page). Each
offering is either a "Service" offering (request something: access, users, changes)
or a "Support" offering (declare an issue). Used whenever UNITY_API_BASE is not set.

All entries are generic placeholders — connect the real Unity API (see unity_client.py)
to load your organisation's catalog.
"""


def _svc(id, name, description, keywords=(), fields=None):
    return {"id": id, "type": "Service", "name": name, "description": description,
            "keywords": list(keywords), "fields": fields or ["Application / resource", "What you need and why"]}


def _sup(id, name, description, keywords=(), fields=None):
    return {"id": id, "type": "Support", "name": name, "description": description,
            "keywords": list(keywords),
            "fields": fields or ["Application affected", "What happens and since when", "Error message or screenshot (no personal data)", "Number of users affected"]}


CATEGORIES = [
    {
        "id": "business-apps",
        "name": "Business Applications",
        "description": "Line-of-business applications used across the organisation.",
        "offerings": [
            _svc("CRM-SR", "CRM - Service Request", "CRM Service Request", ["crm", "salesforce", "customer record"]),
            _sup("CRM-SUP", "CRM - Support", "Declare an issue on the CRM", ["crm", "salesforce", "customer record"]),
            _svc("SALESPORTAL-SR", "Sales Portal - Service Request", "Sales Portal Service Request",
                 ["sales portal", "remarketing", "quote", "pricing"]),
            _sup("SALESPORTAL-SUP", "Sales Portal - Support", "Declare an issue on the Sales Portal",
                 ["sales portal", "remarketing", "quote", "pricing"]),
            _sup("PROCUREMENT-INC", "Procurement - Incident", "Report an application error, bug or unusual behaviour on the procurement tool",
                 ["procurement", "purchase order", "po", "supplier", "vendor"]),
            _svc("DOCUSIGN-SR", "DocuSign - Service Request", "DocuSign - Service Request", ["docusign", "e-signature", "esignature", "envelope"]),
            _svc("DOCUSIGN-USER", "DocuSign - User Creation", "Create a new DocuSign user account",
                 ["docusign", "new user", "user creation", "create user", "account"],
                 ["User's name and entity", "Role / permission profile", "Manager approval"]),
            _svc("ELOQUA-SR", "Eloqua - Service Request", "Eloqua Service Request", ["eloqua", "marketing", "campaign"]),
            _sup("ELOQUA-SUP", "Eloqua - Support", "Declare an issue on Eloqua", ["eloqua", "marketing", "campaign"]),
            _svc("ICONTROLLER-ACC", "iController - Access", "New access, change in access request for iController",
                 ["icontroller", "i-controller", "credit", "collections"],
                 ["Access type (new / change / removal)", "Role required", "Manager approval"]),
            _svc("WIN-PAR", "[WIN] Local admin (PAR) access", "Request temporary local administrator rights on your Windows machine",
                 ["par", "admin rights", "local admin", "privileged access", "windows"],
                 ["Machine name", "Duration needed", "Business justification"]),
        ],
    },
    {
        "id": "server-compute",
        "name": "Server & Compute",
        "description": "Servers, virtual machines and compute capacity.",
        "offerings": [
            _svc("INFRA-VM-NEW", "Virtual machine - New / resize", "Provision a new VM or change CPU, RAM or disk on an existing one",
                 ["server", "vm", "virtual machine", "cpu", "ram", "memory", "resize", "provision"],
                 ["Environment (dev / uat / prod)", "Sizing required", "Cost centre"]),
            _sup("INFRA-SRV-INC", "Server - Incident", "Declare an issue on a server: down, unreachable, degraded performance",
                 ["server", "down", "unreachable", "reboot", "high cpu", "vm"],
                 ["Server hostname", "Impact and since when", "Monitoring alert (if any)"]),
        ],
    },
    {
        "id": "storage-backup",
        "name": "Storage & Backup",
        "description": "File shares, storage and backup / restore.",
        "offerings": [
            _svc("INFRA-RESTORE", "Backup - Restore request", "Restore deleted or overwritten files from backup",
                 ["restore", "backup", "deleted file", "recover", "recovery"],
                 ["Full path of the file / folder", "Date to restore from"]),
            _svc("INFRA-SHARE", "File share - Access / quota", "Access to a shared folder or increase of quota",
                 ["shared drive", "share", "folder", "quota", "storage", "disk space"],
                 ["Share path", "Access level (read / modify)", "Owner approval"]),
        ],
    },
    {
        "id": "workplace",
        "name": "Digital Workplace",
        "description": "Workstation, accounts and collaboration tools.",
        "offerings": [
            _svc("WP-GENERIC", "Workplace - Generic Service Request", "Generic request for the Digital Workplace team",
                 ["workplace", "laptop", "workstation", "software", "install", "teams", "outlook"],
                 ["What you need", "Machine name", "Business justification"]),
            _sup("WP-INC", "Workplace - Workstation incident", "Declare an issue on your laptop, Outlook, Teams or other workplace tools",
                 ["laptop", "pc", "slow", "crash", "outlook", "teams", "email", "vpn", "printer", "password", "locked"],
                 ["Machine name", "What happens and since when", "Error message or screenshot (no personal data)"]),
            _svc("LEARN-ACC", "Learning platform - Access", "Request access to the IT service management learning platform",
                 ["training", "learning", "course", "e-learning"]),
        ],
    },
]

MY_TICKETS = [
    {"number": "INC0048213", "service_id": "WP-INC", "short": "VPN drops every 10 minutes from home", "state": "In progress", "assigned_to": "Workplace Support", "opened": "2026-09-26T09:14:00", "updated": "2026-09-28T16:02:00", "last_note": "Engineer requested client logs; awaiting your reply."},
    {"number": "REQ0031977", "service_id": "ICONTROLLER-ACC", "short": "iController read access", "state": "Awaiting approval", "assigned_to": "iController Admins", "opened": "2026-09-27T11:40:00", "updated": "2026-09-27T11:40:00", "last_note": "Pending line-manager approval."},
    {"number": "REQ0031502", "service_id": "WIN-PAR", "short": "PAR access for Visual Studio install", "state": "Resolved", "assigned_to": "Workplace Security", "opened": "2026-08-25T10:05:00", "updated": "2026-08-26T14:30:00", "last_note": "PAR granted for 7 days."},
]
