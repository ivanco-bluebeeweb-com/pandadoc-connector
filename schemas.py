"""Pydantic params models + SDL entity contracts for PandaDoc Connector.

All params models are module-scope (V17 federal invariant, same rule as
CircleCI Connector's / GitLab CI/CD Connector's schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectPandadocParams(BaseModel):
    api_key: str = Field(
        "",
        description="Your PandaDoc API Key, generated in the Developer Dashboard (Sandbox or Production).",
    )
    label: str = Field("", description="Optional friendly name for this connection (e.g. 'Sales workspace').")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""


class ProviderConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ProviderConnection] = []


class DisconnectPandadocParams(BaseModel):
    connection_id: str = Field("", description="Id of the connection to disconnect (from list_connections).")


class DeleteResult(sdl.Entity):
    title: str = ""
    id: str = ""
    deleted: bool = False


class _Scoped(BaseModel):
    connection_id: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────────────────


class ListDocumentsParams(_Scoped):
    template_id: str = Field("", description="Filter by parent template id.")
    form_id: str = Field("", description="Filter by parent form id.")
    folder_uuid: str = Field("", description="Filter by folder id.")
    contact_id: str = Field("", description="Filter by recipient/approver contact id.")
    q: str = Field("", description="Search query (document name).")
    status: str = Field("", description="Filter by document status, e.g. document.draft, document.sent, document.completed.")
    count: int = Field(50, description="Max results (default 50, max 100).")
    page: int = Field(1, description="Page number for pagination.")


class Document(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    status: str = ""
    date_created: str = ""
    date_modified: str = ""
    date_sent: str = ""
    date_completed: str = ""
    expiration_date: str = ""
    folder_uuid: str = ""
    tags: list[str] = []


class DocumentList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Document] = []


class CreateDocumentFromTemplateParams(_Scoped):
    name: str = Field("", description="Name for the new document.")
    template_uuid: str = Field(..., description="Id of the template to create the document from (from list_templates).")
    recipients_json: str = Field(
        "[]",
        description='JSON array of recipients, e.g. [{"email":"a@b.com","first_name":"A","last_name":"B","role":"Client"}].',
    )
    fields_json: str = Field("{}", description='JSON object of merge-field values, e.g. {"CustomerName":{"value":"John Doe"}}.')
    tokens_json: str = Field("[]", description='JSON array of token replacements, e.g. [{"name":"Client.Name","value":"Acme"}].')
    pricing_tables_json: str = Field("[]", description="JSON array of pricing table data-merge overrides, if the template has pricing tables.")
    folder_uuid: str = Field("", description="Folder id to store the document in.")
    tags_json: str = Field("[]", description="JSON array of tag strings to attach to the document.")


class CreateDocumentFromUrlParams(_Scoped):
    name: str = Field("", description="Name for the new document.")
    url: str = Field(..., description="Publicly reachable URL of the PDF to create the document from.")
    recipients_json: str = Field("[]", description="JSON array of recipients, same shape as create_document_from_template.")
    tags_json: str = Field("[]", description="JSON array of tag strings.")
    parse_form_fields: bool = Field(False, description="Auto-detect PDF form fields as document fields.")


class BulkDeleteDocumentsParams(_Scoped):
    document_ids_json: str = Field(..., description='JSON array of document ids to delete, e.g. ["id1","id2"].')


class BulkResultItem(sdl.Entity):
    title: str = ""
    id: str = ""
    ok: bool = False
    error: str = ""


class BulkResult(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[BulkResultItem] = []
    succeeded: int = 0
    failed: int = 0


class GetDocumentParams(_Scoped):
    document_id: str = Field(..., description="Document id, from list_documents.")


class DeleteDocumentParams(GetDocumentParams):
    pass


class UpdateDocumentParams(GetDocumentParams):
    name: str = Field("", description="New document name.")
    tags_json: str = Field("", description="JSON array of tags to set (replaces existing tags if provided).")


class DocumentDetails(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    status: str = ""
    date_created: str = ""
    date_modified: str = ""
    date_completed: str = ""
    date_sent: str = ""
    expiration_date: str = ""
    grand_total_amount: str = ""
    grand_total_currency: str = ""
    recipients_json: str = ""
    fields_json: str = ""
    metadata_json: str = ""


class SendDocumentParams(GetDocumentParams):
    message: str = Field("", description="Message included in the send-for-signature email.")
    subject: str = Field("", description="Email subject line.")
    silent: bool = Field(False, description="Send without notifying recipients by email.")


class ChangeDocumentStatusParams(GetDocumentParams):
    status: int = Field(..., description="Numeric target status code per PandaDoc's DocumentStatusRequestEnum (0-14).")


class DownloadDocumentParams(GetDocumentParams):
    watermark_text: str = Field("", description="Optional watermark text to stamp on the downloaded PDF.")


class DownloadResult(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    content_type: str = ""
    base64_content: str = ""


class GetEsignDisclosureParams(GetDocumentParams):
    pass


class EsignDisclosure(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    content: str = ""


class GetAuditTrailParams(GetDocumentParams):
    pass


class AuditTrailEvent(sdl.Entity):
    id: str = ""
    title: str = ""
    event: str = ""
    created_at: str = ""
    actor_email: str = ""
    detail: str = ""


class AuditTrailList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[AuditTrailEvent] = []


class GetDocumentSettingsParams(GetDocumentParams):
    pass


class DocumentSettings(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    settings_json: str = ""


class UpdateDocumentSettingsParams(GetDocumentParams):
    settings_json: str = Field(..., description="JSON object of document settings fields to update.")


class MoveDocumentToFolderParams(GetDocumentParams):
    folder_id: str = Field(..., description="Target document folder id, from list_document_folders.")


class GetDocumentOwnershipParams(GetDocumentParams):
    pass


class DocumentOwnership(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    member_id: str = ""
    member_email: str = ""


class UpdateDocumentOwnershipParams(GetDocumentParams):
    member_id: str = Field(..., description="Workspace member id to assign as the new owner, from list_members.")


# ──────────────────────────────────────────────────────────────────────────
# Document fields / recipients / reminders / attachments / sections / links
# ──────────────────────────────────────────────────────────────────────────


class GetDocumentFieldsParams(GetDocumentParams):
    pass


class DocumentField(sdl.Entity):
    id: str = ""
    title: str = ""
    field_id: str = ""
    name: str = ""
    value: str = ""
    type: str = ""


class DocumentFieldList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DocumentField] = []


class UpdateDocumentFieldsParams(GetDocumentParams):
    fields_json: str = Field(..., description="JSON array of {field_id, value} objects to update.")


class ListDocumentRecipientsParams(GetDocumentParams):
    pass


class DocumentRecipient(sdl.Entity):
    id: str = ""
    title: str = ""
    recipient_id: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    role: str = ""
    signing_order: int = 0
    has_completed: bool = False


class DocumentRecipientList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DocumentRecipient] = []


class AddDocumentRecipientParams(GetDocumentParams):
    contact_id: str = Field(..., description="Contact id to add as recipient/approver/CC, from list_contacts.")
    kind: str = Field("recipient", description="One of: recipient, approver, cc.")


class UpdateDocumentRecipientParams(GetDocumentParams):
    recipient_id: str = Field(..., description="Recipient id to update, from list_document_recipients.")
    fields_json: str = Field("{}", description="JSON object of recipient fields to change.")


class DeleteDocumentRecipientParams(GetDocumentParams):
    recipient_id: str = Field(..., description="Recipient id to remove, from list_document_recipients.")


class ReassignDocumentRecipientParams(GetDocumentParams):
    recipient_id: str = Field(..., description="Recipient id being replaced, from list_document_recipients.")
    new_contact_id: str = Field(..., description="New contact id to sign in their place, from list_contacts.")


class SendManualReminderParams(GetDocumentParams):
    recipient_id: str = Field("", description="Optional -- limit the reminder to one recipient.")
    message: str = Field("", description="Optional custom reminder message.")


class GetAutoReminderSettingsParams(GetDocumentParams):
    pass


class AutoReminderSettings(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    enabled: bool = False
    settings_json: str = ""


class UpdateAutoReminderSettingsParams(GetDocumentParams):
    enabled: bool = Field(True, description="Turn automatic reminders on or off for this document.")
    settings_json: str = Field("{}", description="JSON object of auto-reminder schedule fields.")


class GetAutoReminderStatusParams(GetDocumentParams):
    pass


class AutoReminderStatus(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    status: str = ""


class ListDocumentAttachmentsParams(GetDocumentParams):
    pass


class DocumentAttachment(sdl.Entity):
    id: str = ""
    title: str = ""
    attachment_id: str = ""
    name: str = ""
    size: int = 0


class DocumentAttachmentList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DocumentAttachment] = []


class AddDocumentAttachmentParams(GetDocumentParams):
    file_url: str = Field(..., description="Publicly reachable HTTPS URL of the file to attach.")
    name: str = Field("", description="Optional display name for the attachment.")


class DeleteDocumentAttachmentParams(GetDocumentParams):
    attachment_id: str = Field(..., description="Attachment id to remove, from list_document_attachments.")


class ListDocumentSectionsParams(GetDocumentParams):
    pass


class DocumentSection(sdl.Entity):
    id: str = ""
    title: str = ""
    section_id: str = ""
    name: str = ""
    status: str = ""


class DocumentSectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[DocumentSection] = []


class AddDocumentSectionFromTemplateParams(GetDocumentParams):
    template_uuid: str = Field(..., description="Template id to append as a new section/bundle.")
    name: str = Field("", description="Optional name for the new section.")


class ListLinkedObjectsParams(GetDocumentParams):
    pass


class LinkedObject(sdl.Entity):
    id: str = ""
    title: str = ""
    linked_object_id: str = ""
    provider: str = ""
    external_id: str = ""


class LinkedObjectList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[LinkedObject] = []


class LinkObjectToDocumentParams(GetDocumentParams):
    provider: str = Field(..., description="CRM/provider name the object belongs to (e.g. 'salesforce', 'hubspot').")
    external_id: str = Field(..., description="The external record id being linked to this document.")


class UnlinkObjectFromDocumentParams(GetDocumentParams):
    linked_object_id: str = Field(..., description="Linked-object id to remove, from list_linked_objects.")


class AppendContentLibraryItemParams(GetDocumentParams):
    item_id: str = Field(..., description="Content Library item id to append, from list_content_library_items.")


# ──────────────────────────────────────────────────────────────────────────
# Document reminders
# ──────────────────────────────────────────────────────────────────────────


class SendManualReminderParams(GetDocumentParams):
    message: str = Field("", description="Optional custom reminder message.")


class GetAutoReminderSettingsParams(GetDocumentParams):
    pass


class AutoReminderSettings(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    enabled: bool = False
    settings_json: str = ""


class UpdateAutoReminderSettingsParams(GetDocumentParams):
    enabled: bool = Field(True, description="Turn automatic reminders on or off.")
    settings_json: str = Field("{}", description="JSON object of auto-reminder schedule fields.")


class GetAutoReminderStatusParams(GetDocumentParams):
    pass


class AutoReminderStatus(sdl.Entity):
    id: str = ""
    title: str = ""
    document_id: str = ""
    status: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────


class ListTemplatesParams(_Scoped):
    folder_uuid: str = Field("", description="Filter by folder id.")
    tag: str = Field("", description="Filter by tag.")
    count: int = Field(50, description="Page size, max 100.")
    page: int = Field(1, description="Page number.")


class TemplateSummary(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    date_created: str = ""
    date_modified: str = ""


class TemplateList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[TemplateSummary] = []


class GetTemplateParams(_Scoped):
    template_id: str = Field(..., description="Template id, from list_templates.")


class TemplateDetails(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    tags_csv: str = ""
    date_created: str = ""
    date_modified: str = ""


class UpdateTemplateParams(GetTemplateParams):
    tokens_json: str = Field("", description="Optional JSON array of token overrides.")
    roles_json: str = Field("", description="Optional JSON array of role name overrides.")


class DeleteTemplateParams(GetTemplateParams):
    pass


class DuplicateTemplateParams(GetTemplateParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Forms / Content Library
# ──────────────────────────────────────────────────────────────────────────


class ListFormsParams(_Scoped):
    folder_uuid: str = Field("", description="Filter by folder id.")
    count: int = Field(50, description="Page size, max 100.")
    page: int = Field(1, description="Page number.")


class FormSummary(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    date_created: str = ""


class FormList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[FormSummary] = []


class GetFormParams(_Scoped):
    form_id: str = Field(..., description="Form id, from list_forms.")


class FormDetails(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    fields_json: str = ""


class ListContentLibraryItemsParams(_Scoped):
    folder_uuid: str = Field("", description="Filter by folder id.")
    count: int = Field(50, description="Page size, max 100.")
    page: int = Field(1, description="Page number.")


class ContentLibraryItemSummary(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    date_created: str = ""


class ContentLibraryItemList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ContentLibraryItemSummary] = []


class GetContentLibraryItemParams(_Scoped):
    item_id: str = Field(..., description="Content Library item id, from list_content_library_items.")


class ContentLibraryItemDetails(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    tags_csv: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Folders (documents + templates)
# ──────────────────────────────────────────────────────────────────────────


class ListDocumentFoldersParams(_Scoped):
    parent_uuid: str = Field("", description="Optional parent folder id to list children of.")


class FolderSummary(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    parent_uuid: str = ""


class FolderList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[FolderSummary] = []


class CreateDocumentFolderParams(_Scoped):
    name: str = Field(..., description="Name for the new documents folder.")
    parent_uuid: str = Field("", description="Optional parent folder id to nest this folder under.")


class RenameDocumentFolderParams(_Scoped):
    folder_id: str = Field(..., description="Documents folder id to rename, from list_document_folders.")
    name: str = Field(..., description="New folder name.")


class ListTemplateFoldersParams(_Scoped):
    parent_uuid: str = Field("", description="Optional parent folder id to list children of.")


class CreateTemplateFolderParams(_Scoped):
    name: str = Field(..., description="Name for the new templates folder.")
    parent_uuid: str = Field("", description="Optional parent folder id to nest this folder under.")


class RenameTemplateFolderParams(_Scoped):
    folder_id: str = Field(..., description="Templates folder id to rename, from list_template_folders.")
    name: str = Field(..., description="New folder name.")


# ──────────────────────────────────────────────────────────────────────────
# Contacts
# ──────────────────────────────────────────────────────────────────────────


class ListContactsParams(_Scoped):
    count: int = Field(50, description="Page size, max 100.")
    page: int = Field(1, description="Page number.")


class Contact(sdl.Entity):
    title: str = ""
    id: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    company: str = ""


class ContactList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[Contact] = []


class CreateContactParams(_Scoped):
    email: str = Field("", description="Contact's email address.")
    first_name: str = Field("", description="Contact's first name.")
    last_name: str = Field("", description="Contact's last name.")
    company: str = Field("", description="Contact's company name.")
    job_title: str = Field("", description="Contact's job title.")
    phone: str = Field("", description="Contact's phone number.")


class UpdateContactParams(_Scoped):
    contact_id: str = Field(..., description="Contact id to update, from list_contacts.")
    fields_json: str = Field(..., description="JSON object of contact fields to change.")


class DeleteContactParams(_Scoped):
    contact_id: str = Field(..., description="Contact id to delete, from list_contacts.")


# ──────────────────────────────────────────────────────────────────────────
# Members (workspace users)
# ──────────────────────────────────────────────────────────────────────────


class ListMembersParams(_Scoped):
    pass


class WorkspaceMember(sdl.Entity):
    title: str = ""
    id: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    role: str = ""
    is_active: bool = True


class WorkspaceMemberList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WorkspaceMember] = []


# ──────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────


class ListWebhooksParams(_Scoped):
    pass


class WebhookSubscription(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    url: str = ""
    active: bool = True
    triggers_csv: str = ""


class WebhookSubscriptionList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[WebhookSubscription] = []


class GetWebhookParams(_Scoped):
    webhook_id: str = Field(..., description="Webhook subscription id, from list_webhooks.")


class CreateWebhookParams(_Scoped):
    name: str = Field(..., description="Display name for this webhook subscription.")
    url: str = Field(..., description="HTTPS endpoint PandaDoc will POST events to.")
    triggers_csv: str = Field(..., description="Comma-separated trigger events, e.g. 'document_state_changed,recipient_completed'.")
    active: bool = Field(True, description="Whether the subscription is active immediately.")


class UpdateWebhookParams(GetWebhookParams):
    name: str = Field("", description="New display name, leave blank to keep current.")
    url: str = Field("", description="New HTTPS endpoint, leave blank to keep current.")
    triggers_csv: str = Field("", description="New comma-separated trigger events, leave blank to keep current.")
    active: bool = Field(True, description="Whether the subscription should be active.")


class DeleteWebhookParams(GetWebhookParams):
    pass


class ListWebhookEventsParams(_Scoped):
    pass


class WebhookEventType(sdl.Entity):
    id: str = ""
    title: str = ""
    name: str = ""
    description: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Product/pricing catalog
# ──────────────────────────────────────────────────────────────────────────


class ListCatalogItemsParams(_Scoped):
    count: int = Field(50, description="Page size, max 100.")
    page: int = Field(1, description="Page number.")


class CatalogItem(sdl.Entity):
    id: str = ""
    title: str = ""
    sku: str = ""
    price: str = ""
    category_id: str = ""


class CatalogItemList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[CatalogItem] = []


class CreateCatalogItemParams(_Scoped):
    title: str = Field(..., description="Product/service name.")
    sku: str = Field("", description="Stock-keeping unit code.")
    description: str = Field("", description="Product description.")
    price: str = Field("", description="Unit price (as a decimal string, e.g. '199.00').")
    category_id: str = Field("", description="Optional catalog category id.")


class GetCatalogItemParams(_Scoped):
    item_id: str = Field(..., description="Catalog item id, from list_catalog_items.")


class UpdateCatalogItemParams(GetCatalogItemParams):
    fields_json: str = Field(..., description="JSON object of catalog item fields to change.")


class DeleteCatalogItemParams(GetCatalogItemParams):
    pass


# ──────────────────────────────────────────────────────────────────────────
# API logs
# ──────────────────────────────────────────────────────────────────────────


class ListApiLogsParams(_Scoped):
    count: int = Field(50, description="Page size, max 100.")
    page: int = Field(1, description="Page number.")


class ApiLogEntry(sdl.Entity):
    id: str = ""
    title: str = ""
    time: str = ""
    status: int = 0
    method: str = ""
    endpoint: str = ""


class ApiLogList(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[ApiLogEntry] = []


# ──────────────────────────────────────────────────────────────────────────
# Ярус 3 — value-add: bulk operations + health audit
# ──────────────────────────────────────────────────────────────────────────


class BulkDeleteDocumentsParams(_Scoped):
    document_ids_json: str = Field(..., description="JSON array of explicit document ids to delete, e.g. '[\"id1\",\"id2\"]'.")


class BulkResultItem(sdl.Entity):
    title: str = ""
    id: str = ""
    ok: bool = False
    error: str = ""


class BulkResult(sdl.Entity):
    id: str = ""
    title: str = ""
    items: list[BulkResultItem] = []
    succeeded: int = 0
    failed: int = 0


class BulkSendDocumentsParams(_Scoped):
    document_ids_json: str = Field(..., description="JSON array of explicit draft document ids to send, e.g. '[\"id1\",\"id2\"]'.")
    subject: str = Field("", description="Email subject line applied to every send.")
    message: str = Field("", description="Email message applied to every send.")
    silent: bool = Field(False, description="Send without notifying recipients by email.")


class BulkSendManualRemindersParams(_Scoped):
    document_ids_json: str = Field(..., description="JSON array of explicit document ids to remind, e.g. '[\"id1\",\"id2\"]'.")
    message: str = Field("", description="Reminder message applied to every document.")


class AuditWorkspaceHealthParams(_Scoped):
    sample_size: int = Field(50, description="How many recent documents to sample for the audit (max 100).")


class WorkspaceHealthReport(sdl.Entity):
    id: str = ""
    title: str = ""
    total_sampled: int = 0
    draft_count: int = 0
    sent_count: int = 0
    viewed_count: int = 0
    completed_count: int = 0
    declined_count: int = 0
    expired_count: int = 0
    overdue_unsigned_count: int = 0
    documents_without_owner_count: int = 0
    summary: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Compatibility aliases / additions used by handlers_documents.py --
# keeps one canonical shape per concept without duplicating field lists.
# ──────────────────────────────────────────────────────────────────────────

DocumentSummary = Document


class DocumentStatus(sdl.Entity):
    title: str = ""
    id: str = ""
    name: str = ""
    status: str = ""


class CreateDocumentParams(_Scoped):
    payload_json: str = Field(
        ...,
        description=(
            'Raw PandaDoc Create Document request body as JSON -- either the '
            'template shape ({"template_uuid":..., "recipients":[...], "fields":{...}}) '
            'or the PDF-URL shape ({"url":..., "recipients":[...]}). '
            'See create_document_from_template / create_document_from_url for the '
            'structured alternative.'
        ),
    )


class CreateDocumentFromUploadParams(_Scoped):
    name: str = Field(..., description="Name for the new document.")
    content_b64: str = Field(..., description="Base64-encoded PDF/DOCX file content to upload.")
    recipients_json: str = Field("[]", description="JSON array of recipients, same shape as create_document_from_template.")


GetDocumentDetailsParams = GetDocumentParams

DownloadedDocument = DownloadResult

AuditTrailEntry = AuditTrailEvent
