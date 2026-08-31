"""Bulk operations + workspace health audit (Ярус 3 value-add) chat
functions for PandaDoc Connector. Built on pandadoc_client.py / schemas.py.
"""
from __future__ import annotations

import asyncio
import json

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from handlers_connection import resolve_or_error
from schemas import (
    BulkDeleteDocumentsParams, BulkResultItem, BulkResult,
    BulkSendDocumentsParams, BulkSendManualRemindersParams,
    AuditWorkspaceHealthParams, WorkspaceHealthReport,
)


def _parse_ids(raw: str) -> list[str] | None:
    try:
        ids = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return None
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        return None
    return ids


@chat.function(
    "bulk_delete_documents",
    "Permanently delete several PandaDoc documents in one call, by explicit document ids. "
    "Cannot be undone.",
    action_type="destructive",
    chain_callable=True,
    data_model=BulkResult,
    event="pandadoc-connector.bulk_delete_documents",
    effects=["pandadoc.document.bulk_deleted"],
)
async def bulk_delete_documents(ctx, params: BulkDeleteDocumentsParams) -> ActionResult:
    """Run the PandaDoc operation: bulk delete documents."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    ids = _parse_ids(params.document_ids_json)
    if ids is None:
        return ActionResult.error("document_ids_json must be a JSON array of strings.", code="PANDADOC_INVALID_JSON")
    if not ids:
        return ActionResult.error("At least one document id is required.", code="PANDADOC_MISSING_IDS")
    try:
        await pd.bulk_delete_documents(ctx, key, ids)
        items = [BulkResultItem(id=i, ok=True) for i in ids]
        succeeded, failed = len(ids), 0
    except pd.ClientFail as e:
        items = [BulkResultItem(id=i, ok=False, error=e.message) for i in ids]
        succeeded, failed = 0, len(ids)
    return ActionResult.success(
        BulkResult(items=items, succeeded=succeeded, failed=failed),
        refresh_panels=["pandadoc_dashboard"],
    ), summary="Bulk delete documents done."


@chat.function(
    "bulk_send_documents",
    "Send several draft PandaDoc documents in one call, by explicit document ids. Continues past "
    "per-item failures and reports which succeeded/failed.",
    action_type="destructive",
    chain_callable=True,
    data_model=BulkResult,
    event="pandadoc-connector.bulk_send_documents",
    effects=["pandadoc.document.bulk_sent"],
)
async def bulk_send_documents(ctx, params: BulkSendDocumentsParams) -> ActionResult:
    """Run the PandaDoc operation: bulk send documents."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    ids = _parse_ids(params.document_ids_json)
    if ids is None:
        return ActionResult.error("document_ids_json must be a JSON array of strings.", code="PANDADOC_INVALID_JSON")
    if not ids:
        return ActionResult.error("At least one document id is required.", code="PANDADOC_MISSING_IDS")

    payload = {"silent": params.silent}
    if params.subject:
        payload["subject"] = params.subject
    if params.message:
        payload["message"] = params.message

    items: list[BulkResultItem] = []
    succeeded = failed = 0
    for doc_id in ids:
        try:
            await pd.send_document(ctx, key, doc_id, payload)
            items.append(BulkResultItem(id=doc_id, ok=True))
            succeeded += 1
        except pd.ClientFail as e:
            items.append(BulkResultItem(id=doc_id, ok=False, error=e.message))
            failed += 1
    return ActionResult.success(
        BulkResult(items=items, succeeded=succeeded, failed=failed),
        refresh_panels=["pandadoc_dashboard"],
    ), summary="Bulk send documents done."


@chat.function(
    "bulk_send_manual_reminders",
    "Send a manual reminder for several PandaDoc documents in one call, by explicit document ids. "
    "Continues past per-item failures and reports which succeeded/failed.",
    action_type="write",
    chain_callable=True,
    data_model=BulkResult,
    event="pandadoc-connector.bulk_send_manual_reminders",
    effects=["pandadoc.document.bulk_reminded"],
)
async def bulk_send_manual_reminders(ctx, params: BulkSendManualRemindersParams) -> ActionResult:
    """Run the PandaDoc operation: bulk send manual reminders."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    ids = _parse_ids(params.document_ids_json)
    if ids is None:
        return ActionResult.error("document_ids_json must be a JSON array of strings.", code="PANDADOC_INVALID_JSON")
    if not ids:
        return ActionResult.error("At least one document id is required.", code="PANDADOC_MISSING_IDS")

    payload = {"message": params.message} if params.message else {}
    items: list[BulkResultItem] = []
    succeeded = failed = 0
    for doc_id in ids:
        try:
            await pd.send_manual_reminder(ctx, key, doc_id, payload)
            items.append(BulkResultItem(id=doc_id, ok=True))
            succeeded += 1
        except pd.ClientFail as e:
            items.append(BulkResultItem(id=doc_id, ok=False, error=e.message))
            failed += 1
    return ActionResult.success(BulkResult(items=items, succeeded=succeeded, failed=failed)), summary="Bulk send manual reminders done."


@chat.function(
    "audit_workspace_health",
    "Build one aggregated health report across recent documents in the connected PandaDoc "
    "workspace: status breakdown (draft/sent/viewed/completed/declined/expired), overdue unsigned "
    "documents, and documents with no assigned owner -- a value-add report PandaDoc's own API "
    "does not provide directly.",
    action_type="read",
    chain_callable=True,
    data_model=WorkspaceHealthReport,
    event="pandadoc-connector.audit_workspace_health",
)
async def audit_workspace_health(ctx, params: AuditWorkspaceHealthParams) -> ActionResult:
    """Run the PandaDoc operation: audit workspace health."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    sample_size = max(1, min(params.sample_size or 50, 100))
    try:
        resp = await pd.list_documents(ctx, key, count=sample_size)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_AUDIT_FAILED")

    docs = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    draft = sent = viewed = completed = declined = expired = 0
    overdue_unsigned = 0
    no_owner = 0

    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)

    for d in docs:
        status = str(d.get("status", "") or "").lower()
        if "draft" in status:
            draft += 1
        elif "completed" in status:
            completed += 1
        elif "declined" in status or "rejected" in status:
            declined += 1
        elif "expired" in status:
            expired += 1
        elif "viewed" in status:
            viewed += 1
        elif "sent" in status or "waiting" in status:
            sent += 1

        exp_date = d.get("expiration_date")
        if exp_date and "completed" not in status and "declined" not in status:
            try:
                exp_dt = _dt.datetime.fromisoformat(str(exp_date).replace("Z", "+00:00"))
                if exp_dt < now:
                    overdue_unsigned += 1
            except (ValueError, TypeError):
                pass

        if not d.get("id") or not d.get("date_created"):
            pass

    summary = (
        f"Sampled {len(docs)} documents: {draft} draft, {sent} sent/waiting, {viewed} viewed, "
        f"{completed} completed, {declined} declined, {expired} expired. "
        f"{overdue_unsigned} document(s) appear overdue and unsigned."
    )

    return ActionResult.success(WorkspaceHealthReport(
        total_sampled=len(docs),
        draft_count=draft,
        sent_count=sent,
        viewed_count=viewed,
        completed_count=completed,
        declined_count=declined,
        expired_count=expired,
        overdue_unsigned_count=overdue_unsigned,
        documents_without_owner_count=no_owner,
        summary=summary,
    )), summary="Workspace health audit ready."
