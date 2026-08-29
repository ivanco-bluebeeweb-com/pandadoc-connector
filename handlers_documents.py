"""Core Document chat functions for PandaDoc Connector: list/create/status/
update/delete/send/download/details/settings/ownership/audit-trail/bulk
delete. Built on pandadoc_client.py / schemas.py.
"""
from __future__ import annotations

import base64
import json

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from handlers_connection import resolve_or_error
from schemas import (
    ListDocumentsParams, DocumentSummary, DocumentList,
    CreateDocumentParams, CreateDocumentFromUploadParams,
    BulkDeleteDocumentsParams, BulkResult, BulkResultItem,
    GetDocumentParams, DocumentStatus,
    DeleteDocumentParams, DeleteResult,
    UpdateDocumentParams, DocumentDetails,
    GetDocumentDetailsParams,
    SendDocumentParams, ChangeDocumentStatusParams,
    DownloadDocumentParams, DownloadedDocument,
    GetEsignDisclosureParams, EsignDisclosure,
    GetAuditTrailParams, AuditTrailEntry, AuditTrailList,
    GetDocumentSettingsParams, DocumentSettings,
    UpdateDocumentSettingsParams,
    MoveDocumentToFolderParams,
    GetDocumentOwnershipParams, DocumentOwnership,
    UpdateDocumentOwnershipParams,
)


@chat.function(
    "list_documents", "List documents in the connected PandaDoc workspace, optionally filtered by "
    "parent template/form/folder/contact.", action_type="read", chain_callable=True,
    data_model=DocumentList, event="pandadoc-connector.list_documents",
)
async def list_documents(ctx, params: ListDocumentsParams) -> ActionResult:
    """Run the PandaDoc operation: list documents."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    filters = {
        "template_id": params.template_id, "form_id": params.form_id,
        "folder_uuid": params.folder_uuid, "contact_id": params.contact_id,
        "count": params.count, "page": params.page,
    }
    try:
        resp = await pd.list_documents(ctx, key, **filters)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_DOCUMENTS_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.ok(DocumentList(items=[
        DocumentSummary(
            id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
            date_created=d.get("date_created", ""), date_modified=d.get("date_modified", ""),
        ) for d in items
    ]))


@chat.function(
    "create_document", "Create a new PandaDoc document from a template (template_uuid + recipients) "
    "or from a publicly reachable PDF URL. Pass exactly the fields PandaDoc expects as raw JSON in "
    "payload_json (see CONNECTOR_DISCOVERY.md for the two request shapes).",
    action_type="write", chain_callable=True, data_model=DocumentSummary,
    event="pandadoc-connector.create_document", effects=["pandadoc.document.created"],
)
async def create_document(ctx, params: CreateDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: create document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        payload = json.loads(params.payload_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("payload_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    try:
        d = await pd.create_document(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_CREATE_DOCUMENT_FAILED")
    return ActionResult.ok(DocumentSummary(
        id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
        date_created=d.get("date_created", ""), date_modified=d.get("date_modified", ""),
    ))


@chat.function(
    "create_document_from_upload", "Create a new PandaDoc document by uploading a PDF/DOCX file "
    "(base64-encoded content_b64) with a name and recipients, instead of starting from a template.",
    action_type="write", chain_callable=True, data_model=DocumentSummary,
    event="pandadoc-connector.create_document_from_upload", effects=["pandadoc.document.created"],
)
async def create_document_from_upload(ctx, params: CreateDocumentFromUploadParams) -> ActionResult:
    """Run the PandaDoc operation: create document from upload."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        recipients = json.loads(params.recipients_json or "[]")
    except (TypeError, ValueError):
        return ActionResult.error("recipients_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    payload = {
        "name": params.name,
        "file": params.content_b64,
        "recipients": recipients,
    }
    try:
        d = await pd.create_document_from_upload(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_CREATE_DOCUMENT_FAILED")
    return ActionResult.ok(DocumentSummary(
        id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
        date_created=d.get("date_created", ""), date_modified=d.get("date_modified", ""),
    ))


@chat.function(
    "get_document_status", "Read one document's current status by id (draft/sent/completed/viewed/etc).",
    action_type="read", chain_callable=True, data_model=DocumentStatus,
    event="pandadoc-connector.get_document_status",
)
async def get_document_status(ctx, params: GetDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: get document status."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.get_document_status(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DOCUMENT_NOT_FOUND")
    return ActionResult.ok(DocumentStatus(id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", "")))


@chat.function(
    "delete_document", "Permanently delete a PandaDoc document. Cannot be undone.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_document", effects=["pandadoc.document.deleted"],
)
async def delete_document(ctx, params: DeleteDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: delete document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.delete_document(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DELETE_DOCUMENT_FAILED")
    return ActionResult.ok(DeleteResult(id=params.document_id, deleted=True))


@chat.function(
    "bulk_delete_documents", "Permanently delete several PandaDoc documents in one call, by explicit "
    "document ids. Cannot be undone.", action_type="destructive", chain_callable=True,
    data_model=DeleteResult, event="pandadoc-connector.bulk_delete_documents",
    effects=["pandadoc.document.bulk_deleted"],
)
async def bulk_delete_documents(ctx, params: BulkDeleteDocumentsParams) -> ActionResult:
    """Run the PandaDoc operation: bulk delete documents."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        ids = json.loads(params.document_ids_json or "[]")
    except (TypeError, ValueError):
        return ActionResult.error("document_ids_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    if not isinstance(ids, list) or not ids:
        return ActionResult.error("At least one document id is required.", code="PANDADOC_MISSING_IDS")
    try:
        await pd.bulk_delete_documents(ctx, key, ids)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_BULK_DELETE_FAILED")
    return ActionResult.ok(DeleteResult(id=",".join(ids), deleted=True))


@chat.function(
    "update_document", "Update selected fields of an existing PandaDoc document (name, tags, "
    "metadata). Pass changed fields as raw JSON in fields_json.", action_type="write",
    chain_callable=True, data_model=DocumentSummary, event="pandadoc-connector.update_document",
    effects=["pandadoc.document.updated"],
)
async def update_document(ctx, params: UpdateDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: update document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        payload = json.loads(params.fields_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("fields_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    try:
        d = await pd.update_document(ctx, key, params.document_id, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_DOCUMENT_FAILED")
    return ActionResult.ok(DocumentSummary(
        id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
        date_created=d.get("date_created", ""), date_modified=d.get("date_modified", ""),
    ))


@chat.function(
    "get_document_details", "Read one document in full: recipients, pricing tables, tokens, fields, "
    "and full metadata.", action_type="read", chain_callable=True, data_model=DocumentDetails,
    event="pandadoc-connector.get_document_details",
)
async def get_document_details(ctx, params: GetDocumentDetailsParams) -> ActionResult:
    """Run the PandaDoc operation: get document details."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.get_document_details(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DOCUMENT_NOT_FOUND")
    return ActionResult.ok(DocumentDetails(
        id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
        raw_json=json.dumps(d)[:8000],
    ))


@chat.function(
    "send_document", "Send an existing draft document to its recipients for signing, optionally "
    "with a custom subject/message.", action_type="write", chain_callable=True,
    data_model=DocumentSummary, event="pandadoc-connector.send_document",
    effects=["pandadoc.document.sent"],
)
async def send_document(ctx, params: SendDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: send document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {}
    if params.subject:
        payload["subject"] = params.subject
    if params.message:
        payload["message"] = params.message
    payload["silent"] = params.silent
    try:
        d = await pd.send_document(ctx, key, params.document_id, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_SEND_DOCUMENT_FAILED")
    return ActionResult.ok(DocumentSummary(
        id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
        date_created=d.get("date_created", ""), date_modified=d.get("date_modified", ""),
    ))


@chat.function(
    "change_document_status", "Move a document to a specific PandaDoc status code (e.g. mark a "
    "draft document.draft as sent). Use PandaDoc's documented numeric status codes.",
    action_type="write", chain_callable=True, data_model=DocumentSummary,
    event="pandadoc-connector.change_document_status", effects=["pandadoc.document.status_changed"],
)
async def change_document_status(ctx, params: ChangeDocumentStatusParams) -> ActionResult:
    """Run the PandaDoc operation: change document status."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.change_document_status(ctx, key, params.document_id, params.status)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_STATUS_CHANGE_FAILED")
    return ActionResult.ok(DocumentSummary(
        id=d.get("id", ""), name=d.get("name", ""), status=d.get("status", ""),
        date_created=d.get("date_created", ""), date_modified=d.get("date_modified", ""),
    ))


@chat.function(
    "download_document", "Download a completed/draft document's PDF content as base64.",
    action_type="read", chain_callable=True, data_model=DownloadedDocument,
    event="pandadoc-connector.download_document",
)
async def download_document(ctx, params: DownloadDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: download document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        content = await pd.download_document(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DOWNLOAD_FAILED")
    b64 = base64.b64encode(content).decode() if isinstance(content, (bytes, bytearray)) else ""
    return ActionResult.ok(DownloadedDocument(document_id=params.document_id, content_b64=b64))


@chat.function(
    "get_document_esign_disclosure", "Read the eSign disclosure text shown to signers for one "
    "document.", action_type="read", chain_callable=True, data_model=EsignDisclosure,
    event="pandadoc-connector.get_document_esign_disclosure",
)
async def get_document_esign_disclosure(ctx, params: GetEsignDisclosureParams) -> ActionResult:
    """Run the PandaDoc operation: get document esign disclosure."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.get_document_esign_disclosure(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_ESIGN_DISCLOSURE_FAILED")
    return ActionResult.ok(EsignDisclosure(document_id=params.document_id, text=d.get("text", "") if isinstance(d, dict) else ""))


@chat.function(
    "get_document_audit_trail", "Read the tamper-evident audit trail (who viewed/signed/declined "
    "and when) for one document.", action_type="read", chain_callable=True, data_model=AuditTrailList,
    event="pandadoc-connector.get_document_audit_trail",
)
async def get_document_audit_trail(ctx, params: GetAuditTrailParams) -> ActionResult:
    """Run the PandaDoc operation: get document audit trail."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_document_audit_trail(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_AUDIT_TRAIL_FAILED")
    events = resp if isinstance(resp, list) else (resp.get("results", []) if isinstance(resp, dict) else [])
    return ActionResult.ok(AuditTrailList(items=[
        AuditTrailEntry(event=e.get("event", ""), actor=e.get("actor", ""), timestamp=e.get("timestamp", ""))
        for e in events
    ]))


@chat.function(
    "get_document_settings", "Read per-document settings (e.g. recipient signing order enforcement, "
    "language).", action_type="read", chain_callable=True, data_model=DocumentSettings,
    event="pandadoc-connector.get_document_settings",
)
async def get_document_settings(ctx, params: GetDocumentSettingsParams) -> ActionResult:
    """Run the PandaDoc operation: get document settings."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.get_document_settings(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_SETTINGS_FAILED")
    return ActionResult.ok(DocumentSettings(document_id=params.document_id, settings_json=json.dumps(d)[:4000]))


@chat.function(
    "update_document_settings", "Update per-document settings (recipient signing order enforcement, "
    "language, etc). Pass changed fields as raw JSON.", action_type="write", chain_callable=True,
    data_model=DocumentSettings, event="pandadoc-connector.update_document_settings",
    effects=["pandadoc.document.settings_updated"],
)
async def update_document_settings(ctx, params: UpdateDocumentSettingsParams) -> ActionResult:
    """Run the PandaDoc operation: update document settings."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        payload = json.loads(params.settings_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("settings_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    try:
        d = await pd.update_document_settings(ctx, key, params.document_id, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_SETTINGS_UPDATE_FAILED")
    return ActionResult.ok(DocumentSettings(document_id=params.document_id, settings_json=json.dumps(d)[:4000]))


@chat.function(
    "move_document_to_folder", "Move a document into a different documents folder.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.move_document_to_folder", effects=["pandadoc.document.moved"],
)
async def move_document_to_folder(ctx, params: MoveDocumentToFolderParams) -> ActionResult:
    """Run the PandaDoc operation: move document to folder."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.move_document_to_folder(ctx, key, params.document_id, params.folder_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_MOVE_FAILED")
    return ActionResult.ok(DeleteResult(id=params.document_id, deleted=False))


@chat.function(
    "get_document_ownership", "Read which workspace member currently owns a document.",
    action_type="read", chain_callable=True, data_model=DocumentOwnership,
    event="pandadoc-connector.get_document_ownership",
)
async def get_document_ownership(ctx, params: GetDocumentOwnershipParams) -> ActionResult:
    """Run the PandaDoc operation: get document ownership."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.get_document_ownership(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_OWNERSHIP_FAILED")
    return ActionResult.ok(DocumentOwnership(document_id=params.document_id, member_id=d.get("id", "") if isinstance(d, dict) else ""))


@chat.function(
    "update_document_ownership", "Reassign a document to a different workspace member.",
    action_type="write", chain_callable=True, data_model=DocumentOwnership,
    event="pandadoc-connector.update_document_ownership", effects=["pandadoc.document.ownership_changed"],
)
async def update_document_ownership(ctx, params: UpdateDocumentOwnershipParams) -> ActionResult:
    """Run the PandaDoc operation: update document ownership."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        d = await pd.update_document_ownership(ctx, key, params.document_id, params.member_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_OWNERSHIP_UPDATE_FAILED")
    return ActionResult.ok(DocumentOwnership(document_id=params.document_id, member_id=params.member_id))
