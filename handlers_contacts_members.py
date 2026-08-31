"""Contacts / Members (workspace users) chat functions for PandaDoc
Connector. Built on pandadoc_client.py / schemas.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from handlers_connection import resolve_or_error
from schemas import (
    ListContactsParams, Contact, ContactList,
    CreateContactParams, UpdateContactParams, DeleteContactParams, DeleteResult,
    ListMembersParams, WorkspaceMember, WorkspaceMemberList,
)


@chat.function(
    "list_contacts", "List contacts (external people you send documents to) saved in the "
    "connected PandaDoc workspace.", action_type="read", chain_callable=True,
    data_model=ContactList, event="pandadoc-connector.list_contacts",
)
async def list_contacts(ctx, params: ListContactsParams) -> ActionResult:
    """Run the PandaDoc operation: list contacts."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_contacts(ctx, key, count=params.count, page=params.page)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_CONTACTS_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    return ActionResult.success(ContactList(items=[
        Contact(
            id=c.get("id", ""), email=c.get("email", "") or "",
            first_name=c.get("first_name", "") or "", last_name=c.get("last_name", "") or "",
            company=c.get("company", "") or "",
        ) for c in items
    ])), summary="Contacts listed."


@chat.function(
    "create_contact", "Create a new contact (a person you can add as a document recipient/approver) "
    "in the connected PandaDoc workspace.", action_type="write", chain_callable=True,
    data_model=Contact, event="pandadoc-connector.create_contact",
    effects=["pandadoc.contact.created"],
)
async def create_contact(ctx, params: CreateContactParams) -> ActionResult:
    """Run the PandaDoc operation: create contact."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {
        "email": params.email, "first_name": params.first_name, "last_name": params.last_name,
        "company": params.company, "job_title": params.job_title, "phone": params.phone,
    }
    payload = {k: v for k, v in payload.items() if v}
    try:
        resp = await pd.create_contact(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_CREATE_CONTACT_FAILED")
    return ActionResult.success(Contact(
        id=resp.get("id", "") if isinstance(resp, dict) else "",
        email=params.email, first_name=params.first_name, last_name=params.last_name,
        company=params.company,
    ), refresh_panels=["pandadoc_dashboard"]), summary="Contact created."


@chat.function(
    "update_contact", "Update selected fields of an existing PandaDoc contact.",
    action_type="write", chain_callable=True, data_model=Contact,
    event="pandadoc-connector.update_contact", effects=["pandadoc.contact.updated"],
)
async def update_contact(ctx, params: UpdateContactParams) -> ActionResult:
    """Run the PandaDoc operation: update contact."""
    import json
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        fields = json.loads(params.fields_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("fields_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    try:
        resp = await pd.update_contact(ctx, key, params.contact_id, fields)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_CONTACT_FAILED")
    return ActionResult.success(Contact(
        id=params.contact_id, email=(resp or {}).get("email", ""),
        first_name=(resp or {}).get("first_name", ""), last_name=(resp or {}).get("last_name", ""),
        company=(resp or {}).get("company", ""),
    ), refresh_panels=["pandadoc_dashboard"]), summary="Contact updated."


@chat.function(
    "delete_contact", "Permanently delete a contact from the connected PandaDoc workspace. "
    "Documents already sent to them are not affected.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_contact", effects=["pandadoc.contact.deleted"],
)
async def delete_contact(ctx, params: DeleteContactParams) -> ActionResult:
    """Run the PandaDoc operation: delete contact."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.delete_contact(ctx, key, params.contact_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DELETE_CONTACT_FAILED")
    return ActionResult.success(DeleteResult(id=params.contact_id, deleted=True), refresh_panels=["pandadoc_dashboard"]), summary="Contact deleted."


@chat.function(
    "list_members", "List the members (users) of the connected PandaDoc workspace.",
    action_type="read", chain_callable=True, data_model=WorkspaceMemberList,
    event="pandadoc-connector.list_members",
)
async def list_members(ctx, params: ListMembersParams) -> ActionResult:
    """Run the PandaDoc operation: list members."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_members(ctx, key)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_MEMBERS_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    return ActionResult.success(WorkspaceMemberList(items=[
        WorkspaceMember(
            id=str(m.get("membership_id", m.get("id", ""))), email=m.get("email", "") or "",
            first_name=m.get("first_name", "") or "", last_name=m.get("last_name", "") or "",
            role=m.get("role", "") or "", is_active=bool(m.get("is_active", True)),
        ) for m in items
    ])), summary="Members listed."
