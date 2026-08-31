"""Webhooks / Product-Pricing Catalog / API Logs chat functions for
PandaDoc Connector. Built on pandadoc_client.py / schemas.py.
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from handlers_connection import resolve_or_error
from schemas import (
    ListWebhooksParams, WebhookSubscription, WebhookSubscriptionList,
    GetWebhookParams, CreateWebhookParams, UpdateWebhookParams,
    DeleteWebhookParams, DeleteResult,
    ListWebhookEventsParams, WebhookEventType,
    ListCatalogItemsParams, CatalogItem, CatalogItemList,
    CreateCatalogItemParams, GetCatalogItemParams, UpdateCatalogItemParams,
    DeleteCatalogItemParams,
    ListApiLogsParams, ApiLogEntry, ApiLogList,
)


def _webhook_entity(w: dict) -> WebhookSubscription:
    triggers = w.get("triggers", [])
    return WebhookSubscription(
        id=w.get("uuid", w.get("id", "")), name=w.get("name", "") or "",
        url=w.get("url", "") or "", active=bool(w.get("active", True)),
        triggers_csv=",".join(triggers) if isinstance(triggers, list) else str(triggers or ""),
    )


@chat.function(
    "list_webhooks", "List webhook subscriptions configured on this PandaDoc workspace.",
    action_type="read", chain_callable=True, data_model=WebhookSubscriptionList,
    event="pandadoc-connector.list_webhooks",
)
async def list_webhooks(ctx, params: ListWebhooksParams) -> ActionResult:
    """Run the PandaDoc operation: list webhooks."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_webhook_subscriptions(ctx, key)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_WEBHOOKS_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    return ActionResult.success(WebhookSubscriptionList(items=[_webhook_entity(w) for w in items])), summary="Webhooks listed."


@chat.function(
    "get_webhook", "Read one webhook subscription's full configuration by id.",
    action_type="read", chain_callable=True, data_model=WebhookSubscription,
    event="pandadoc-connector.get_webhook",
)
async def get_webhook(ctx, params: GetWebhookParams) -> ActionResult:
    """Run the PandaDoc operation: get webhook."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_webhook_subscription(ctx, key, params.webhook_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_GET_WEBHOOK_FAILED")
    return ActionResult.success(_webhook_entity(resp if isinstance(resp, dict) else {})), summary="Webhook retrieved."


@chat.function(
    "create_webhook", "Subscribe to a PandaDoc event (e.g. document_state_changed, recipient_completed) "
    "-- PandaDoc will POST to your URL whenever it happens.",
    action_type="write", chain_callable=True, data_model=WebhookSubscription,
    event="pandadoc-connector.create_webhook", effects=["pandadoc.webhook.created"],
)
async def create_webhook(ctx, params: CreateWebhookParams) -> ActionResult:
    """Run the PandaDoc operation: create webhook."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    triggers = [t.strip() for t in params.triggers_csv.split(",") if t.strip()]
    payload = {"name": params.name, "url": params.url, "active": params.active, "triggers": triggers}
    try:
        resp = await pd.create_webhook_subscription(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_CREATE_WEBHOOK_FAILED")
    return ActionResult.success(_webhook_entity(resp if isinstance(resp, dict) else payload), refresh_panels=["pandadoc_dashboard"]), summary="Webhook created."


@chat.function(
    "update_webhook", "Update an existing webhook subscription's name, URL, triggers, and/or active state. "
    "Only given fields change.",
    action_type="write", chain_callable=True, data_model=WebhookSubscription,
    event="pandadoc-connector.update_webhook", effects=["pandadoc.webhook.updated"],
)
async def update_webhook(ctx, params: UpdateWebhookParams) -> ActionResult:
    """Run the PandaDoc operation: update webhook."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {}
    if params.name:
        payload["name"] = params.name
    if params.url:
        payload["url"] = params.url
    if params.triggers_csv:
        payload["triggers"] = [t.strip() for t in params.triggers_csv.split(",") if t.strip()]
    payload["active"] = params.active
    try:
        resp = await pd.update_webhook_subscription(ctx, key, params.webhook_id, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_WEBHOOK_FAILED")
    return ActionResult.success(_webhook_entity(resp if isinstance(resp, dict) else {"uuid": params.webhook_id, **payload}), refresh_panels=["pandadoc_dashboard"]), summary="Webhook updated."


@chat.function(
    "delete_webhook", "Permanently remove a webhook subscription. Cannot be undone.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_webhook", effects=["pandadoc.webhook.deleted"],
)
async def delete_webhook(ctx, params: DeleteWebhookParams) -> ActionResult:
    """Run the PandaDoc operation: delete webhook."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.delete_webhook_subscription(ctx, key, params.webhook_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DELETE_WEBHOOK_FAILED")
    return ActionResult.success(DeleteResult(id=params.webhook_id, deleted=True), refresh_panels=["pandadoc_dashboard"]), summary="Webhook deleted."


@chat.function(
    "list_webhook_event_types", "List the event types PandaDoc can notify a webhook subscription about "
    "(e.g. document_state_changed, recipient_completed, template_created).",
    action_type="read", chain_callable=True, data_model=WebhookEventType,
    event="pandadoc-connector.list_webhook_event_types",
)
async def list_webhook_event_types(ctx, params: ListWebhookEventsParams) -> ActionResult:
    """Run the PandaDoc operation: list webhook event types."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_webhook_events(ctx, key)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_WEBHOOK_EVENTS_FAILED")
    return ActionResult.success(resp if resp is not None else {}), summary="Webhook event types listed."


def _catalog_entity(c: dict) -> CatalogItem:
    return CatalogItem(
        id=c.get("id", ""), title=c.get("title", "") or "", sku=c.get("sku", "") or "",
        price=str(c.get("price", "") or ""), category_id=c.get("category_id", "") or "",
    )


@chat.function(
    "list_catalog_items", "List products/services in the connected PandaDoc pricing catalog.",
    action_type="read", chain_callable=True, data_model=CatalogItemList,
    event="pandadoc-connector.list_catalog_items",
)
async def list_catalog_items(ctx, params: ListCatalogItemsParams) -> ActionResult:
    """Run the PandaDoc operation: list catalog items."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_catalog_items(ctx, key, count=params.count, page=params.page)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_CATALOG_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    return ActionResult.success(CatalogItemList(items=[_catalog_entity(c) for c in items])), summary="Catalog items listed."


@chat.function(
    "create_catalog_item", "Create a new product/service in the connected PandaDoc pricing catalog, "
    "so it can be added to documents/quotes as a priced line item.",
    action_type="write", chain_callable=True, data_model=CatalogItem,
    event="pandadoc-connector.create_catalog_item", effects=["pandadoc.catalog_item.created"],
)
async def create_catalog_item(ctx, params: CreateCatalogItemParams) -> ActionResult:
    """Run the PandaDoc operation: create catalog item."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {
        "title": params.title, "sku": params.sku, "description": params.description,
        "price": params.price, "category_id": params.category_id,
    }
    payload = {k: v for k, v in payload.items() if v}
    try:
        resp = await pd.create_catalog_item(ctx, key, payload)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_CREATE_CATALOG_FAILED")
    return ActionResult.success(_catalog_entity(resp if isinstance(resp, dict) else payload), refresh_panels=["pandadoc_dashboard"]), summary="Catalog item created."


@chat.function(
    "get_catalog_item", "Read one product/service catalog item in full.",
    action_type="read", chain_callable=True, data_model=CatalogItem,
    event="pandadoc-connector.get_catalog_item",
)
async def get_catalog_item(ctx, params: GetCatalogItemParams) -> ActionResult:
    """Run the PandaDoc operation: get catalog item."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.get_catalog_item(ctx, key, params.item_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_GET_CATALOG_FAILED")
    return ActionResult.success(_catalog_entity(resp if isinstance(resp, dict) else {})), summary="Catalog item retrieved."


@chat.function(
    "update_catalog_item", "Update selected fields of an existing catalog item (price, title, SKU, etc). "
    "Only given fields change.",
    action_type="write", chain_callable=True, data_model=CatalogItem,
    event="pandadoc-connector.update_catalog_item", effects=["pandadoc.catalog_item.updated"],
)
async def update_catalog_item(ctx, params: UpdateCatalogItemParams) -> ActionResult:
    """Run the PandaDoc operation: update catalog item."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        fields = json.loads(params.fields_json or "{}")
    except (TypeError, ValueError):
        return ActionResult.error("fields_json must be valid JSON.", code="PANDADOC_INVALID_JSON")
    try:
        resp = await pd.update_catalog_item(ctx, key, params.item_id, fields)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_UPDATE_CATALOG_FAILED")
    return ActionResult.success(_catalog_entity(resp if isinstance(resp, dict) else {"id": params.item_id, **fields}), refresh_panels=["pandadoc_dashboard"]), summary="Catalog item updated."


@chat.function(
    "delete_catalog_item", "Permanently delete a product/service from the pricing catalog. Cannot be undone.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="pandadoc-connector.delete_catalog_item", effects=["pandadoc.catalog_item.deleted"],
)
async def delete_catalog_item(ctx, params: DeleteCatalogItemParams) -> ActionResult:
    """Run the PandaDoc operation: delete catalog item."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await pd.delete_catalog_item(ctx, key, params.item_id)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_DELETE_CATALOG_FAILED")
    return ActionResult.success(DeleteResult(id=params.item_id, deleted=True), refresh_panels=["pandadoc_dashboard"]), summary="Catalog item deleted."


@chat.function(
    "list_api_logs", "List recent API request logs for the connected PandaDoc workspace -- useful for "
    "debugging integration issues.",
    action_type="read", chain_callable=True, data_model=ApiLogList,
    event="pandadoc-connector.list_api_logs",
)
async def list_api_logs(ctx, params: ListApiLogsParams) -> ActionResult:
    """Run the PandaDoc operation: list api logs."""
    conn, key, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        resp = await pd.list_api_logs(ctx, key, count=params.count, page=params.page)
    except pd.ClientFail as e:
        return ActionResult.error(e.message, code="PANDADOC_LIST_API_LOGS_FAILED")
    items = resp.get("results", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
    return ActionResult.success(ApiLogList(items=[
        ApiLogEntry(
            time=str(e.get("time", "") or ""), status=int(e.get("status", 0) or 0),
            method=str(e.get("method", "") or ""), endpoint=str(e.get("endpoint", "") or ""),
        ) for e in items
    ])), summary="Api logs listed."
