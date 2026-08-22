"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), SAME REASONING AS CircleCI Connector /
GitLab CI/CD Connector / n8n Connector. PandaDoc lives inside the USER'S
OWN workspace -- Imperal cannot and should not broker access to someone
else's PandaDoc account centrally.

WHY API KEY, NOT OAUTH2 (unlike HubSpot/Notion/Slack CONNECTORS).

PandaDoc documents two auth mechanisms (developers.pandadoc.com/reference/
api-key-authentication-process + .../authentication-process, both read
2026-08-22): API Key (self-serve Sandbox key, Production key requires
PandaDoc Sales approval) and OAuth2 (`/oauth2/access_token`, meant for
apps acting on behalf of a THIRD-PARTY user -- i.e. PandaDoc's own
marketplace-app model, not a "connect my own workspace" BYOK flow). Since
this connector manages the CONNECTING USER'S OWN workspace (not someone
else's, via a multi-tenant OAuth app), API Key is the documented, simpler,
correct choice -- same principle as CircleCI Connector's Personal API
Token over an OAuth app it does not have.

WHY "Authorization: API-Key <key>" HEADER, EXACTLY AS DOCUMENTED.

Built exactly as PandaDoc's own docs specify rather than assumed to be a
generic Bearer token -- same principle as CircleCI's `Circle-Token` /
GitLab CI/CD's `PRIVATE-TOKEN` header choices.

WHY `base_url` IS FIXED ON api.pandadoc.com, UNLIKE GitLab CI/CD / n8n /
UiPath / MuleSoft / Automation Anywhere / Blue Prism CONNECTORS.

PandaDoc is a pure SaaS product -- there is no self-managed/on-prem
variant to point at a different host.

WHAT THIS CONNECTOR COVERS (see CONNECTOR_DISCOVERY.md for the full
three-tier breakdown against PandaDoc's official OpenAPI spec v8.11.1):
Documents (create/send/status/update/delete/download/bulk-delete),
Document Fields/Recipients/Reminders/Attachments/Sections/Linked-Objects,
Templates, Forms, Content Library, Folders (documents + templates),
Contacts, Workspace Members, Webhooks, Product/Pricing Catalog, API Logs,
plus Imperal-side value-add: bulk send/remind, and a workspace health
audit report PandaDoc's own API has no equivalent single endpoint for.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "pandadoc-connector",
    version="0.1.0",
    display_name="PandaDoc",
    description=(
        "Connect your own PandaDoc workspace to create, send, and track "
        "documents from templates or PDF uploads; manage document fields, "
        "recipients, reminders, attachments, sections, and linked objects; "
        "manage templates, forms, Content Library items, and folders; "
        "manage contacts and workspace members; manage webhooks and the "
        "product/pricing catalog; read API logs; plus bulk operations "
        "(delete/send/remind) and a workspace health audit across many "
        "documents at once. Uses your own PandaDoc API Key -- nothing is "
        "hosted or proxied by Imperal beyond the request itself."
    ),
    icon="icon.svg",
    capabilities=[
        "pandadoc:read",
        "pandadoc:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="pandadoc",
    description=(
        "PandaDoc Connector -- connect your own PandaDoc workspace via an "
        "API Key, then create/send/track documents, manage fields, "
        "recipients, reminders, attachments, sections, linked objects, "
        "templates, forms, Content Library items, folders, contacts, "
        "workspace members, webhooks, the product/pricing catalog, and API "
        "logs, plus run bulk operations and workspace health audits."
    ),
)

ext.secret(
    "pandadoc_connections",
    (
        "Your connected PandaDoc workspaces -- stored as a JSON array, one "
        "entry per workspace, each with its own API Key and an optional "
        "friendly label. Managed through connect_pandadoc / "
        "disconnect_pandadoc -- you should not need to edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one connection is stored, same shape as CircleCI Connector's /
    GitLab CI/CD Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("pandadoc_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} PandaDoc workspace(s) connected." if count
            else "Not connected yet -- run connect_pandadoc."
        ),
    }
