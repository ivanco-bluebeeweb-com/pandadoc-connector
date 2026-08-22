"""PandaDoc REST API client -- API Key auth against the user's own PandaDoc
workspace. Thin async wrappers over Documents/Templates/Forms/Content
Library/Folders/Contacts/Members/Webhooks/Catalog/Quotes/Notary endpoints.
Built on the SDK's ctx.http.* async client, same pattern as CircleCI
Connector's circleci_client.py / GitLab CI/CD Connector's client.

WHY "Authorization: API-Key <key>" HEADER -- PandaDoc's own docs
(developers.pandadoc.com/reference/api-key-authentication-process,
read 2026-08-22) document exactly this header shape for API Key auth,
the BYOK method chosen for this connector (see app.py docstring).

WHY 401 vs 404 ARE HANDLED DIFFERENTLY, SAME PRINCIPLE AS OTHER
CONNECTORS IN THIS PORTFOLIO.

A 401 means the API Key itself is not accepted (missing, revoked, wrong,
or belongs to a removed user). A 404 on a document/template/folder lookup
usually means the id is wrong OR the key's owner lacks access to that
particular resource -- both are surfaced as a single not-found ClientFail.

WHY base_url IS FIXED ON api.pandadoc.com -- PandaDoc is a pure SaaS
product, no self-managed/on-prem variant exists.
"""
from __future__ import annotations

from typing import Any

BASE_URL = "https://api.pandadoc.com/public/v1"
BASE_URL_V2 = "https://api.pandadoc.com/public/v2"


class ClientFail(Exception):
    """Raised for any non-2xx PandaDoc response, carrying a human message."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.message = message
        self.status = status


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"API-Key {api_key}",
        "Content-Type": "application/json",
    }


def _check(resp) -> Any:
    status = getattr(resp, "status_code", 0)
    if status == 401:
        raise ClientFail(
            "PandaDoc rejected this API Key -- it may be wrong, revoked, or its "
            "owning user was removed from the workspace.",
            status,
        )
    if status == 403:
        raise ClientFail(
            "PandaDoc refused this request -- the API Key's owning user lacks "
            "permission for this action (role/license restriction).",
            status,
        )
    if status == 404:
        raise ClientFail(
            "Not found on PandaDoc -- check the id, or the API Key's owner may "
            "lack access to this resource.",
            status,
        )
    if status == 429:
        raise ClientFail(
            "Rate limited by PandaDoc (per-user, sliding 60s window; Sandbox "
            "keys are capped at 10 requests/minute) -- try again shortly.",
            status,
        )
    if status == 413:
        raise ClientFail("File too large for PandaDoc (max 50 MB for PDF uploads).", status)
    if status >= 400:
        try:
            body = resp.json()
            msg = body.get("detail") or body.get("type") or str(body)
        except Exception:
            msg = getattr(resp, "text", "") or f"HTTP {status}"
        raise ClientFail(f"PandaDoc API error ({status}): {msg}", status)
    if status == 204:
        return None
    try:
        return resp.json()
    except Exception:
        return None


async def _get(ctx, api_key: str, path: str, *, params: dict | None = None, base: str = BASE_URL) -> Any:
    clean = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    resp = await ctx.http.get(f"{base}{path}", headers=_headers(api_key), params=clean)
    return _check(resp)


async def _post(ctx, api_key: str, path: str, *, json: dict | None = None, base: str = BASE_URL) -> Any:
    resp = await ctx.http.post(f"{base}{path}", headers=_headers(api_key), json=json or {})
    return _check(resp)


async def _patch(ctx, api_key: str, path: str, *, json: dict | None = None, base: str = BASE_URL) -> Any:
    resp = await ctx.http.patch(f"{base}{path}", headers=_headers(api_key), json=json or {})
    return _check(resp)


async def _put(ctx, api_key: str, path: str, *, json: dict | None = None, base: str = BASE_URL) -> Any:
    resp = await ctx.http.put(f"{base}{path}", headers=_headers(api_key), json=json or {})
    return _check(resp)


async def _delete(ctx, api_key: str, path: str, *, json: dict | None = None, base: str = BASE_URL) -> Any:
    resp = await ctx.http.delete(f"{base}{path}", headers=_headers(api_key), json=json or {})
    return _check(resp)


async def check_connection(ctx, api_key: str) -> dict:
    """Verify the API key works by listing workspace members (cheap, always-available)."""
    try:
        await list_members(ctx, api_key)
    except ClientFail as e:
        if e.status == 401:
            return {
                "ok": False,
                "error": "PandaDoc rejected this API Key. Double-check it was copied correctly and hasn't been revoked.",
                "error_code": "PANDADOC_KEY_INVALID",
            }
        return {"ok": False, "error": e.message, "error_code": "PANDADOC_CONNECT_FAILED"}
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────────────────

async def list_documents(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/documents", params=filters)


async def create_document(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/documents", json=payload)


async def create_document_from_upload(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/documents?upload", json=payload)


async def bulk_delete_documents(ctx, api_key: str, document_ids: list[str]) -> Any:
    return await _delete(ctx, api_key, "/documents", json={"uuids": document_ids})


async def get_document_status(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}")


async def delete_document(ctx, api_key: str, document_id: str) -> Any:
    return await _delete(ctx, api_key, f"/documents/{document_id}")


async def update_document(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _patch(ctx, api_key, f"/documents/{document_id}", json=payload)


async def get_document_details(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}/details")


async def send_document(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/send", json=payload)


async def change_document_status(ctx, api_key: str, document_id: str, status: int) -> dict:
    return await _patch(ctx, api_key, f"/documents/{document_id}/status", json={"status": status})


async def download_document(ctx, api_key: str, document_id: str, params: dict | None = None) -> bytes:
    resp = await ctx.http.get(
        f"{BASE_URL}/documents/{document_id}/download",
        headers=_headers(api_key),
        params={k: v for k, v in (params or {}).items() if v not in (None, "")},
    )
    _check(resp)
    return resp.content


async def get_document_esign_disclosure(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}/esign-disclosure")


async def get_document_audit_trail(ctx, api_key: str, document_id: str) -> Any:
    return await _get(ctx, api_key, f"/documents/{document_id}/audit-trail", base=BASE_URL_V2)


async def get_document_settings(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}/settings", base=BASE_URL_V2)


async def update_document_settings(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _patch(ctx, api_key, f"/documents/{document_id}/settings", json=payload, base=BASE_URL_V2)


async def move_document_to_folder(ctx, api_key: str, document_id: str, folder_id: str) -> Any:
    return await _post(ctx, api_key, f"/documents/{document_id}/move-to-folder/{folder_id}")


async def get_document_ownership(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}/ownership")


async def update_document_ownership(ctx, api_key: str, document_id: str, member_id: str) -> dict:
    return await _patch(ctx, api_key, f"/documents/{document_id}/ownership", json={"member_id": member_id})


# ──────────────────────────────────────────────────────────────────────────
# Document fields, recipients, reminders, attachments, sections, linked objects
# ──────────────────────────────────────────────────────────────────────────

async def get_document_fields(ctx, api_key: str, document_id: str) -> Any:
    return await _get(ctx, api_key, f"/documents/{document_id}/fields")


async def update_document_fields(ctx, api_key: str, document_id: str, fields: list[dict]) -> Any:
    return await _post(ctx, api_key, f"/documents/{document_id}/fields", json={"fields": fields})


async def list_document_recipients(ctx, api_key: str, document_id: str) -> Any:
    return await _get(ctx, api_key, f"/documents/{document_id}/recipients")


async def add_document_recipient(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/recipients", json=payload)


async def update_document_recipient(ctx, api_key: str, document_id: str, recipient_id: str, payload: dict) -> dict:
    return await _patch(ctx, api_key, f"/documents/{document_id}/recipients/recipient/{recipient_id}", json=payload)


async def delete_document_recipient(ctx, api_key: str, document_id: str, recipient_id: str) -> Any:
    return await _delete(ctx, api_key, f"/documents/{document_id}/recipients/{recipient_id}")


async def reassign_document_recipient(ctx, api_key: str, document_id: str, recipient_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/recipients/{recipient_id}/reassign", json=payload)


async def send_manual_reminder(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/send-reminder", json=payload)


async def get_auto_reminder_settings(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}/auto-reminders")


async def update_auto_reminder_settings(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _patch(ctx, api_key, f"/documents/{document_id}/auto-reminders", json=payload)


async def get_auto_reminder_status(ctx, api_key: str, document_id: str) -> dict:
    return await _get(ctx, api_key, f"/documents/{document_id}/auto-reminders/status")


async def list_document_attachments(ctx, api_key: str, document_id: str) -> Any:
    return await _get(ctx, api_key, f"/documents/{document_id}/attachments")


async def add_document_attachment(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/attachments", json=payload)


async def delete_document_attachment(ctx, api_key: str, document_id: str, attachment_id: str) -> Any:
    return await _delete(ctx, api_key, f"/documents/{document_id}/attachments/{attachment_id}")


async def list_document_sections(ctx, api_key: str, document_id: str) -> Any:
    return await _get(ctx, api_key, f"/documents/{document_id}/sections")


async def add_document_section_from_template(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/sections", json=payload)


async def list_linked_objects(ctx, api_key: str, document_id: str) -> Any:
    return await _get(ctx, api_key, f"/documents/{document_id}/linked-objects")


async def link_object_to_document(ctx, api_key: str, document_id: str, payload: dict) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/linked-objects", json=payload)


async def unlink_object_from_document(ctx, api_key: str, document_id: str, linked_object_id: str) -> Any:
    return await _delete(ctx, api_key, f"/documents/{document_id}/linked-objects/{linked_object_id}")


async def append_content_library_item(ctx, api_key: str, document_id: str, item_id: str) -> dict:
    return await _post(ctx, api_key, f"/documents/{document_id}/append-content-library-item", json={"content_library_item_id": item_id})


# ──────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────

async def list_templates(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/templates", params=filters)


async def get_template_details(ctx, api_key: str, template_id: str) -> dict:
    return await _get(ctx, api_key, f"/templates/{template_id}/details")


async def update_template(ctx, api_key: str, template_id: str, payload: dict) -> dict:
    return await _patch(ctx, api_key, f"/templates/{template_id}", json=payload)


async def delete_template(ctx, api_key: str, template_id: str) -> Any:
    return await _delete(ctx, api_key, f"/templates/{template_id}")


async def duplicate_template(ctx, api_key: str, template_id: str) -> dict:
    return await _post(ctx, api_key, f"/templates/{template_id}/copy")


# ──────────────────────────────────────────────────────────────────────────
# Forms
# ──────────────────────────────────────────────────────────────────────────

async def list_forms(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/forms", params=filters)


async def get_form_details(ctx, api_key: str, form_id: str) -> dict:
    return await _get(ctx, api_key, f"/forms/{form_id}")


# ──────────────────────────────────────────────────────────────────────────
# Content Library
# ──────────────────────────────────────────────────────────────────────────

async def list_content_library_items(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/content-library-items", params=filters)


async def get_content_library_item(ctx, api_key: str, item_id: str) -> dict:
    return await _get(ctx, api_key, f"/content-library-items/{item_id}/details")


# ──────────────────────────────────────────────────────────────────────────
# Folders
# ──────────────────────────────────────────────────────────────────────────

async def list_document_folders(ctx, api_key: str) -> Any:
    return await _get(ctx, api_key, "/documents/folders")


async def create_document_folder(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/documents/folders", json=payload)


async def rename_document_folder(ctx, api_key: str, folder_id: str, name: str) -> dict:
    return await _patch(ctx, api_key, f"/documents/folders/{folder_id}", json={"name": name})


async def list_template_folders(ctx, api_key: str) -> Any:
    return await _get(ctx, api_key, "/templates/folders")


async def create_template_folder(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/templates/folders", json=payload)


async def rename_template_folder(ctx, api_key: str, folder_id: str, name: str) -> dict:
    return await _patch(ctx, api_key, f"/templates/folders/{folder_id}", json={"name": name})


# ──────────────────────────────────────────────────────────────────────────
# Contacts
# ──────────────────────────────────────────────────────────────────────────

async def list_contacts(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/contacts", params=filters)


async def create_contact(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/contacts", json=payload)


async def update_contact(ctx, api_key: str, contact_id: str, payload: dict) -> dict:
    return await _put(ctx, api_key, f"/contacts/{contact_id}", json=payload)


async def delete_contact(ctx, api_key: str, contact_id: str) -> Any:
    return await _delete(ctx, api_key, f"/contacts/{contact_id}")


# ──────────────────────────────────────────────────────────────────────────
# Members / Workspace
# ──────────────────────────────────────────────────────────────────────────

async def list_members(ctx, api_key: str) -> Any:
    return await _get(ctx, api_key, "/members")


# ──────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────

async def list_webhook_subscriptions(ctx, api_key: str) -> Any:
    return await _get(ctx, api_key, "/webhook-subscriptions", base=BASE_URL_V2)


async def get_webhook_subscription(ctx, api_key: str, webhook_id: str) -> dict:
    return await _get(ctx, api_key, f"/webhook-subscriptions/{webhook_id}", base=BASE_URL_V2)


async def create_webhook_subscription(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/webhook-subscriptions", json=payload, base=BASE_URL_V2)


async def update_webhook_subscription(ctx, api_key: str, webhook_id: str, payload: dict) -> dict:
    return await _put(ctx, api_key, f"/webhook-subscriptions/{webhook_id}", json=payload, base=BASE_URL_V2)


async def delete_webhook_subscription(ctx, api_key: str, webhook_id: str) -> Any:
    return await _delete(ctx, api_key, f"/webhook-subscriptions/{webhook_id}", base=BASE_URL_V2)


async def list_webhook_events(ctx, api_key: str) -> Any:
    return await _get(ctx, api_key, "/webhook-subscriptions/events", base=BASE_URL_V2)


# ──────────────────────────────────────────────────────────────────────────
# Product Catalog (pricing tables / items)
# ──────────────────────────────────────────────────────────────────────────

async def list_catalog_items(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/product-catalog", params=filters, base=BASE_URL_V2)


async def create_catalog_item(ctx, api_key: str, payload: dict) -> dict:
    return await _post(ctx, api_key, "/product-catalog", json=payload, base=BASE_URL_V2)


async def get_catalog_item(ctx, api_key: str, item_id: str) -> dict:
    return await _get(ctx, api_key, f"/product-catalog/{item_id}", base=BASE_URL_V2)


async def update_catalog_item(ctx, api_key: str, item_id: str, payload: dict) -> dict:
    return await _patch(ctx, api_key, f"/product-catalog/{item_id}", json=payload, base=BASE_URL_V2)


async def delete_catalog_item(ctx, api_key: str, item_id: str) -> Any:
    return await _delete(ctx, api_key, f"/product-catalog/{item_id}", base=BASE_URL_V2)


# ──────────────────────────────────────────────────────────────────────────
# API logs
# ──────────────────────────────────────────────────────────────────────────

async def list_api_logs(ctx, api_key: str, **filters) -> Any:
    return await _get(ctx, api_key, "/api-logs", params=filters, base=BASE_URL_V2)
