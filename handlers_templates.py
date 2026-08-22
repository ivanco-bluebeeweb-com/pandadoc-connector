"""Templates / Forms / Content Library / Folders chat functions for
PandaDoc Connector. Built on pandadoc_client.py / schemas.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from handlers_connection import resolve_or_error
from schemas import (
    ListTemplatesParams, TemplateSummary, TemplateList,
    GetTemplateParams, TemplateDetails,
    UpdateTemplateParams, DeleteTemplateParams, DeleteResult,
    DuplicateTemplateParams,
    ListFormsParams, FormSummary, FormList,
    GetFormParams, FormDetails,
    ListContentLibraryItemsParams, ContentLibraryItemSummary, ContentLibraryItemList,
    GetContentLibraryItemParams, ContentLibraryItemDetails,
    ListDocumentFoldersParams, FolderSummary, FolderList,
    CreateDocumentFolderParams, RenameDocumentFolderParams,
    ListTemplateFoldersParams, CreateTemplateFolderParams, RenameTemplateFolderParams,
)


@chat.function(
    "list_templates", "List templates available in the connected PandaDoc workspace, optionally "
    "filtered by folder or tag.", action_type="read", chain_callable=True,
    data_model=TemplateList, event="pandadoc-connector.list_templates",
)
async def list_templates(ctx, params: ListTemplatesParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_templates(ctx, key, folder_uuid=params.folder_uuid, tag=params.tag, count=params.count, page=params.page)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_TEMPLATES_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.ok(TemplateList(items=[
        TemplateSummary(id=t.get("id", ""), name=t.get("name", ""), date_created=t.get("date_created", ""), date_modified=t.get("date_modified", ""))
        for t in items
    ]))


@chat.function(
    "get_template", "Read one PandaDoc template in full -- its tags, roles, and content.",
    action_type="read", chain_callable=True, data_model=TemplateDetails,
    event="pandadoc-connector.get_template",
)
async def get_template(ctx, params: GetTemplateParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        t = await pd.get_template_details(ctx, key, params.template_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_TEMPLATE_NOT_FOUND")
    return ActionResult.ok(TemplateDetails(
        id=t.get("id", ""), name=t.get("name", ""),
        tags_csv=",".join(t.get("tags", []) or []),
        date_created=t.get("date_created", ""),
    ))


@chat.function(
    "update_template", "Update a template's tokens and/or role assignments.",
    action_type="write", chain_callable=True, data_model=TemplateDetails,
    event="pandadoc-connector.update_template", effects=["pandadoc.template.updated"],
)
async def update_template(ctx, params: UpdateTemplateParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    import json
    try:
        payload = json.loads(params.fields_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("fields_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    try:
        t = await pd.update_template(ctx, key, params.template_id, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_TEMPLATE_UPDATE_FAILED")
    return ActionResult.ok(TemplateDetails(id=t.get("id", params.template_id), name=t.get("name", "")))


@chat.function(
    "delete_template", "Permanently delete a PandaDoc template. Cannot be undone.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_template", effects=["pandadoc.template.deleted"],
)
async def delete_template(ctx, params: DeleteTemplateParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.delete_template(ctx, key, params.template_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_TEMPLATE_DELETE_FAILED")
    return ActionResult.ok(DeleteResult(id=params.template_id, deleted=True))


@chat.function(
    "duplicate_template", "Duplicate an existing PandaDoc template -- same content/roles, a new id.",
    action_type="write", chain_callable=True, data_model=TemplateDetails,
    event="pandadoc-connector.duplicate_template", effects=["pandadoc.template.duplicated"],
)
async def duplicate_template(ctx, params: DuplicateTemplateParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        t = await pd.duplicate_template(ctx, key, params.template_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_TEMPLATE_DUPLICATE_FAILED")
    return ActionResult.ok(TemplateDetails(id=t.get("id", ""), name=t.get("name", "")))


@chat.function(
    "list_forms", "List forms available in the connected PandaDoc workspace.",
    action_type="read", chain_callable=True, data_model=FormList,
    event="pandadoc-connector.list_forms",
)
async def list_forms(ctx, params: ListFormsParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_forms(ctx, key, folder_uuid=params.folder_uuid, count=params.count, page=params.page)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_FORMS_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.ok(FormList(items=[
        FormSummary(id=f.get("id", ""), name=f.get("name", ""), date_created=f.get("date_created", "")) for f in items
    ]))


@chat.function(
    "get_form", "Read one PandaDoc form's field schema in full.",
    action_type="read", chain_callable=True, data_model=FormDetails,
    event="pandadoc-connector.get_form",
)
async def get_form(ctx, params: GetFormParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        f = await pd.get_form_details(ctx, key, params.form_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_FORM_NOT_FOUND")
    import json as _json
    return ActionResult.ok(FormDetails(id=f.get("id", ""), name=f.get("name", ""), fields_json=_json.dumps(f.get("fields", []) if isinstance(f, dict) else [])))


@chat.function(
    "list_content_library_items", "List Content Library items (reusable blocks/clauses) in the "
    "connected PandaDoc workspace.", action_type="read", chain_callable=True,
    data_model=ContentLibraryItemList, event="pandadoc-connector.list_content_library_items",
)
async def list_content_library_items(ctx, params: ListContentLibraryItemsParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_content_library_items(ctx, key, folder_uuid=params.folder_uuid, count=params.count, page=params.page)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_CONTENT_LIBRARY_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else []
    return ActionResult.ok(ContentLibraryItemList(items=[
        ContentLibraryItemSummary(id=c.get("id", ""), name=c.get("name", ""), date_created=c.get("date_created", "")) for c in items
    ]))


@chat.function(
    "get_content_library_item", "Read one Content Library item in full.",
    action_type="read", chain_callable=True, data_model=ContentLibraryItemDetails,
    event="pandadoc-connector.get_content_library_item",
)
async def get_content_library_item(ctx, params: GetContentLibraryItemParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        c = await pd.get_content_library_item(ctx, key, params.item_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_CONTENT_LIBRARY_ITEM_NOT_FOUND")
    return ActionResult.ok(ContentLibraryItemDetails(id=c.get("id", ""), name=c.get("name", ""), tags_csv=",".join(c.get("tags", []) or [])))


@chat.function(
    "list_document_folders", "List folders used to organize documents in the connected PandaDoc "
    "workspace.", action_type="read", chain_callable=True, data_model=FolderList,
    event="pandadoc-connector.list_document_folders",
)
async def list_document_folders(ctx, params: ListDocumentFoldersParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_document_folders(ctx, key)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_FOLDERS_FAILED")
    items = resp if isinstance(resp, list) else (resp.get("results", []) if isinstance(resp, dict) else [])
    return ActionResult.ok(FolderList(items=[FolderSummary(uuid=f.get("uuid", f.get("id", "")), name=f.get("name", "")) for f in items]))


@chat.function(
    "create_document_folder", "Create a new folder to organize documents.",
    action_type="write", chain_callable=True, data_model=FolderSummary,
    event="pandadoc-connector.create_document_folder", effects=["pandadoc.folder.created"],
)
async def create_document_folder(ctx, params: CreateDocumentFolderParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {"name": params.name}
    if params.parent_uuid:
        payload["parent_uuid"] = params.parent_uuid
    try:
        f = await pd.create_document_folder(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_FOLDER_CREATE_FAILED")
    return ActionResult.ok(FolderSummary(uuid=f.get("uuid", f.get("id", "")), name=f.get("name", params.name)))


@chat.function(
    "rename_document_folder", "Rename an existing document folder.",
    action_type="write", chain_callable=True, data_model=FolderSummary,
    event="pandadoc-connector.rename_document_folder", effects=["pandadoc.folder.renamed"],
)
async def rename_document_folder(ctx, params: RenameDocumentFolderParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        f = await pd.rename_document_folder(ctx, key, params.folder_uuid, params.name)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_FOLDER_RENAME_FAILED")
    return ActionResult.ok(FolderSummary(uuid=params.folder_uuid, name=params.name))


@chat.function(
    "list_template_folders", "List folders used to organize templates in the connected PandaDoc "
    "workspace.", action_type="read", chain_callable=True, data_model=FolderList,
    event="pandadoc-connector.list_template_folders",
)
async def list_template_folders(ctx, params: ListTemplateFoldersParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_template_folders(ctx, key)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_TEMPLATE_FOLDERS_FAILED")
    items = resp if isinstance(resp, list) else (resp.get("results", []) if isinstance(resp, dict) else [])
    return ActionResult.ok(FolderList(items=[FolderSummary(uuid=f.get("uuid", f.get("id", "")), name=f.get("name", "")) for f in items]))


@chat.function(
    "create_template_folder", "Create a new folder to organize templates.",
    action_type="write", chain_callable=True, data_model=FolderSummary,
    event="pandadoc-connector.create_template_folder", effects=["pandadoc.folder.created"],
)
async def create_template_folder(ctx, params: CreateTemplateFolderParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {"name": params.name}
    if params.parent_uuid:
        payload["parent_uuid"] = params.parent_uuid
    try:
        f = await pd.create_template_folder(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_TEMPLATE_FOLDER_CREATE_FAILED")
    return ActionResult.ok(FolderSummary(uuid=f.get("uuid", f.get("id", "")), name=f.get("name", params.name)))


@chat.function(
    "rename_template_folder", "Rename an existing template folder.",
    action_type="write", chain_callable=True, data_model=FolderSummary,
    event="pandadoc-connector.rename_template_folder", effects=["pandadoc.folder.renamed"],
)
async def rename_template_folder(ctx, params: RenameTemplateFolderParams) -> ActionResult:
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        f = await pd.rename_template_folder(ctx, key, params.folder_uuid, params.name)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_TEMPLATE_FOLDER_RENAME_FAILED")
    return ActionResult.ok(FolderSummary(uuid=params.folder_uuid, name=params.name))
