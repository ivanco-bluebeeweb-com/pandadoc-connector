"""Document Fields / Recipients / Reminders / Attachments / Sections /
Linked Objects chat functions for PandaDoc Connector. Built on
pandadoc_client.py / schemas.py.
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from handlers_connection import resolve_or_error
from schemas import (
    GetDocumentFieldsParams, DocumentField, DocumentFieldList,
    UpdateDocumentFieldsParams,
    ListDocumentRecipientsParams, DocumentRecipient, DocumentRecipientList,
    AddDocumentRecipientParams, UpdateDocumentRecipientParams,
    DeleteDocumentRecipientParams, ReassignDocumentRecipientParams,
    SendManualReminderParams,
    GetAutoReminderSettingsParams, AutoReminderSettings,
    UpdateAutoReminderSettingsParams,
    GetAutoReminderStatusParams, AutoReminderStatus,
    ListDocumentAttachmentsParams, DocumentAttachment, DocumentAttachmentList,
    AddDocumentAttachmentParams, DeleteDocumentAttachmentParams,
    ListDocumentSectionsParams, DocumentSection, DocumentSectionList,
    AddDocumentSectionFromTemplateParams,
    ListLinkedObjectsParams, LinkedObject, LinkedObjectList,
    LinkObjectToDocumentParams, UnlinkObjectFromDocumentParams,
    DeleteResult,
)


@chat.function(
    "get_document_fields", "Read the merge/form field values currently set on a document.",
    action_type="read", chain_callable=True, data_model=DocumentFieldList,
    event="pandadoc-connector.get_document_fields",
)
async def get_document_fields(ctx, params: GetDocumentFieldsParams) -> ActionResult:
    """Run the PandaDoc operation: get document fields."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_document_details(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_GET_FIELDS_FAILED")
    fields = resp.get("fields", {}) if isinstance(resp, dict) else {}
    items = [DocumentField(field_id=k, name=k, value=str(v.get("value", "")) if isinstance(v, dict) else str(v), type=v.get("type", "") if isinstance(v, dict) else "") for k, v in fields.items()]
    return ActionResult.success(DocumentFieldList(items=items), summary="Document fields retrieved.")


@chat.function(
    "update_document_fields", "Update merge/form field values on a document that is still in draft.",
    action_type="write", chain_callable=True, data_model=DocumentField,
    event="pandadoc-connector.update_document_fields",
    effects=["pandadoc.document.fields_updated"],
)
async def update_document_fields(ctx, params: UpdateDocumentFieldsParams) -> ActionResult:
    """Run the PandaDoc operation: update document fields."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        fields = json.loads(params.fields_json or "[]")
    except (TypeError, ValueError):
        return ActionResult.error("fields_json must be a valid JSON array.", code="PANDADOC_INVALID_JSON")
    try:
        resp = await pd.update_document(ctx, key, params.document_id, {"fields": fields})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_FIELDS_FAILED")
    return ActionResult.success(DocumentField(field_id=params.document_id, name="updated", value="ok"), summary="Document fields updated.")


@chat.function(
    "list_document_recipients", "List the recipients, approvers, and CC'd contacts on a document.",
    action_type="read", chain_callable=True, data_model=DocumentRecipientList,
    event="pandadoc-connector.list_document_recipients",
)
async def list_document_recipients(ctx, params: ListDocumentRecipientsParams) -> ActionResult:
    """Run the PandaDoc operation: list document recipients."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_document_details(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_RECIPIENTS_FAILED")
    recips = resp.get("recipients", []) if isinstance(resp, dict) else []
    items = [DocumentRecipient(
        recipient_id=r.get("id", ""), email=r.get("email", ""),
        first_name=r.get("first_name", ""), last_name=r.get("last_name", ""),
        role=r.get("role", ""), signing_order=r.get("signing_order", 0) or 0,
        has_completed=r.get("has_completed", False),
    ) for r in recips]
    return ActionResult.success(DocumentRecipientList(items=items), summary="Document recipients listed.")


@chat.function(
    "add_document_recipient", "Add a contact as a recipient, approver, or CC on a document, by contact id.",
    action_type="write", chain_callable=True, data_model=DocumentRecipient,
    event="pandadoc-connector.add_document_recipient",
    effects=["pandadoc.document.recipient_added"],
)
async def add_document_recipient(ctx, params: AddDocumentRecipientParams) -> ActionResult:
    """Run the PandaDoc operation: add document recipient."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.update_document(ctx, key, params.document_id, {"recipients": [{"id": params.contact_id, "kind": params.kind}]})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_ADD_RECIPIENT_FAILED")
    return ActionResult.success(DocumentRecipient(recipient_id=params.contact_id, role=params.kind), summary="Document recipient created.")


@chat.function(
    "update_document_recipient", "Update a recipient's details on a document still in draft (e.g. fix a mistyped email).",
    action_type="write", chain_callable=True, data_model=DocumentRecipient,
    event="pandadoc-connector.update_document_recipient",
    effects=["pandadoc.document.recipient_updated"],
)
async def update_document_recipient(ctx, params: UpdateDocumentRecipientParams) -> ActionResult:
    """Run the PandaDoc operation: update document recipient."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        fields = json.loads(params.fields_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("fields_json must be a valid JSON object.", code="PANDADOC_INVALID_JSON")
    fields["id"] = params.recipient_id
    try:
        resp = await pd.update_document(ctx, key, params.document_id, {"recipients": [fields]})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_RECIPIENT_FAILED")
    return ActionResult.success(DocumentRecipient(recipient_id=params.recipient_id), summary="Document recipient updated.")


@chat.function(
    "delete_document_recipient", "Remove a recipient from a document still in draft. Cannot be undone.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_document_recipient",
    effects=["pandadoc.document.recipient_deleted"],
)
async def delete_document_recipient(ctx, params: DeleteDocumentRecipientParams) -> ActionResult:
    """Run the PandaDoc operation: delete document recipient."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.update_document(ctx, key, params.document_id, {"recipients": [{"id": params.recipient_id, "delete": True}]})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DELETE_RECIPIENT_FAILED")
    return ActionResult.success(DeleteResult(id=params.recipient_id, deleted=True), summary="Document recipient deleted.")


@chat.function(
    "send_manual_reminder", "Send an immediate one-off reminder email to a document's pending recipients.",
    action_type="write", chain_callable=True, data_model=AutoReminderStatus,
    event="pandadoc-connector.send_manual_reminder",
    effects=["pandadoc.document.reminder_sent"],
)
async def send_manual_reminder(ctx, params: SendManualReminderParams) -> ActionResult:
    """Run the PandaDoc operation: send manual reminder."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.send_manual_reminder(ctx, key, params.document_id, {"message": params.message} if params.message else {})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_SEND_REMINDER_FAILED")
    return ActionResult.success(AutoReminderStatus(document_id=params.document_id, status="reminder_sent"), summary="Manual reminder send requested.")


@chat.function(
    "get_document_auto_reminder_settings", "Read a document's automatic reminder schedule settings.",
    action_type="read", chain_callable=True, data_model=AutoReminderSettings,
    event="pandadoc-connector.get_document_auto_reminder_settings",
)
async def get_document_auto_reminder_settings(ctx, params: GetAutoReminderSettingsParams) -> ActionResult:
    """Run the PandaDoc operation: get document auto reminder settings."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_document_auto_reminders(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_GET_AUTO_REMINDERS_FAILED")
    return ActionResult.success(AutoReminderSettings(document_id=params.document_id, enabled=bool(resp.get("enabled")) if isinstance(resp, dict) else False, settings_json=json.dumps(resp)), summary="Document auto reminder settings retrieved.")


@chat.function(
    "update_document_auto_reminder_settings", "Update a document's automatic reminder schedule (turn on/off, change cadence).",
    action_type="write", chain_callable=True, data_model=AutoReminderSettings,
    event="pandadoc-connector.update_document_auto_reminder_settings",
    effects=["pandadoc.document.auto_reminders_updated"],
)
async def update_document_auto_reminder_settings(ctx, params: UpdateAutoReminderSettingsParams) -> ActionResult:
    """Run the PandaDoc operation: update document auto reminder settings."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        extra = json.loads(params.settings_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("settings_json must be a valid JSON object.", code="PANDADOC_INVALID_JSON")
    payload = {"enabled": params.enabled, **extra}
    try:
        resp = await pd.update_document_auto_reminders(ctx, key, params.document_id, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_AUTO_REMINDERS_FAILED")
    return ActionResult.success(AutoReminderSettings(document_id=params.document_id, enabled=params.enabled, settings_json=json.dumps(resp)), summary="Document auto reminder settings updated.")


@chat.function(
    "get_document_auto_reminder_status", "Read whether a document's automatic reminders are currently active.",
    action_type="read", chain_callable=True, data_model=AutoReminderStatus,
    event="pandadoc-connector.get_document_auto_reminder_status",
)
async def get_document_auto_reminder_status(ctx, params: GetAutoReminderStatusParams) -> ActionResult:
    """Run the PandaDoc operation: get document auto reminder status."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_document_auto_reminder_status(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_GET_REMINDER_STATUS_FAILED")
    status = resp.get("status", "") if isinstance(resp, dict) else ""
    return ActionResult.success(AutoReminderStatus(document_id=params.document_id, status=status), summary="Document auto reminder status retrieved.")


@chat.function(
    "list_document_attachments", "List files attached to a document (separate from the document's own content).",
    action_type="read", chain_callable=True, data_model=DocumentAttachmentList,
    event="pandadoc-connector.list_document_attachments",
)
async def list_document_attachments(ctx, params: ListDocumentAttachmentsParams) -> ActionResult:
    """Run the PandaDoc operation: list document attachments."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_document_attachments(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_ATTACHMENTS_FAILED")
    items = resp if isinstance(resp, list) else resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.success(DocumentAttachmentList(items=[
        DocumentAttachment(id=a.get("uuid", a.get("id", "")), name=a.get("name", ""), url=a.get("url", "")) for a in items
    ]), summary="Document attachments listed.")


@chat.function(
    "add_document_attachment", "Attach a file (fetched from a publicly reachable URL) to a document.",
    action_type="write", chain_callable=True, data_model=DocumentAttachment,
    event="pandadoc-connector.add_document_attachment",
    effects=["pandadoc.document.attachment_added"],
)
async def add_document_attachment(ctx, params: AddDocumentAttachmentParams) -> ActionResult:
    """Run the PandaDoc operation: add document attachment."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.add_document_attachment(ctx, key, params.document_id, {"url": params.file_url, "name": params.name})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_ADD_ATTACHMENT_FAILED")
    return ActionResult.success(DocumentAttachment(id=resp.get("uuid", "") if isinstance(resp, dict) else "", name=params.name), summary="Document attachment created.")


@chat.function(
    "delete_document_attachment", "Permanently remove an attachment from a document. Cannot be undone.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_document_attachment",
    effects=["pandadoc.document.attachment_deleted"],
)
async def delete_document_attachment(ctx, params: DeleteDocumentAttachmentParams) -> ActionResult:
    """Run the PandaDoc operation: delete document attachment."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.delete_document_attachment(ctx, key, params.document_id, params.attachment_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DELETE_ATTACHMENT_FAILED")
    return ActionResult.success(DeleteResult(id=params.attachment_id, deleted=True), summary="Document attachment deleted.")


@chat.function(
    "list_document_sections", "List the content sections/bundles that make up a multi-section document.",
    action_type="read", chain_callable=True, data_model=DocumentSectionList,
    event="pandadoc-connector.list_document_sections",
)
async def list_document_sections(ctx, params: ListDocumentSectionsParams) -> ActionResult:
    """Run the PandaDoc operation: list document sections."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_document_sections(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_SECTIONS_FAILED")
    items = resp if isinstance(resp, list) else resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.success(DocumentSectionList(items=[
        DocumentSection(id=s.get("uuid", s.get("id", "")), title=s.get("title", ""), status=s.get("status", "")) for s in items
    ]), summary="Document sections listed.")


@chat.function(
    "add_document_section_from_template", "Add a new content section to a document, built from an existing template.",
    action_type="write", chain_callable=True, data_model=DocumentSection,
    event="pandadoc-connector.add_document_section_from_template",
    effects=["pandadoc.document.section_added"],
)
async def add_document_section_from_template(ctx, params: AddDocumentSectionFromTemplateParams) -> ActionResult:
    """Run the PandaDoc operation: add document section from template."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.add_document_section_from_template(ctx, key, params.document_id, {"template_uuid": params.template_uuid, "name": params.name})
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_ADD_SECTION_FAILED")
    return ActionResult.success(DocumentSection(id=resp.get("uuid", "") if isinstance(resp, dict) else ""), summary="Document section from template created.")


@chat.function(
    "list_linked_objects", "List CRM/external objects (e.g. a HubSpot deal or Salesforce opportunity) linked to a document.",
    action_type="read", chain_callable=True, data_model=LinkedObjectList,
    event="pandadoc-connector.list_linked_objects",
)
async def list_linked_objects(ctx, params: ListLinkedObjectsParams) -> ActionResult:
    """Run the PandaDoc operation: list linked objects."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_linked_objects(ctx, key, params.document_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_LINKED_OBJECTS_FAILED")
    items = resp if isinstance(resp, list) else resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.success(LinkedObjectList(items=[
        LinkedObject(id=o.get("id", ""), provider=o.get("provider", ""), object_type=o.get("entity_type", "")) for o in items
    ]), summary="Linked objects listed.")


@chat.function(
    "link_object_to_document", "Link an external CRM object (provider + entity type + id) to a document.",
    action_type="write", chain_callable=True, data_model=LinkedObject,
    event="pandadoc-connector.link_object_to_document",
    effects=["pandadoc.document.object_linked"],
)
async def link_object_to_document(ctx, params: LinkObjectToDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: link object to document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.link_object_to_document(ctx, key, params.document_id, {
            "provider": params.provider,
            "external_id": params.external_id,
        })
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LINK_OBJECT_FAILED")
    return ActionResult.success(LinkedObject(id=resp.get("id", "") if isinstance(resp, dict) else ""), summary="Link object to document done.")


@chat.function(
    "unlink_object_from_document", "Remove a previously linked external CRM object from a document.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.unlink_object_from_document",
    effects=["pandadoc.document.object_unlinked"],
)
async def unlink_object_from_document(ctx, params: UnlinkObjectFromDocumentParams) -> ActionResult:
    """Run the PandaDoc operation: unlink object from document."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.unlink_object_from_document(ctx, key, params.document_id, params.linked_object_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UNLINK_OBJECT_FAILED")
    return ActionResult.success(DeleteResult(id=params.linked_object_id, deleted=True), summary="Unlink object from document done.")
