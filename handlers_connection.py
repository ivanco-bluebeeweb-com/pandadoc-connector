"""Connection management for PandaDoc Connector: connect/disconnect/list,
storing API Key connections as a JSON array under one secret, same shape
as CircleCI Connector's / GitLab CI/CD Connector's handlers.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import pandadoc_client as pd
from app import ext, chat
from schemas import (
    NoParams,
    ConnectPandadocParams, ProviderConnection, ProviderConnectionList,
    DisconnectPandadocParams, DeleteResult,
)

_SECRET_NAME = "pandadoc_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return None
    return connections[0]


def _connection_to_entity(c: dict) -> ProviderConnection:
    return ProviderConnection(
        id=c.get("id", ""),
        title=c.get("label") or "PandaDoc workspace",
        connected=True,
        detail="API Key connection",
    )


async def resolve_or_error(ctx, connection_id: str = ""):
    """Shared guard: resolve a connection or return the standard 'not
    connected' ActionResult.error. Returns (conn, api_key, error_or_None)."""
    conn = await resolve_connection(ctx, connection_id)
    if conn is None:
        return None, None, ActionResult.error(
            "No PandaDoc workspace is connected yet. Use connect_pandadoc first.",
            code="PANDADOC_ACCOUNT_MISSING",
        )
    return conn, conn.get("api_key", ""), None


@chat.function(
    "connect_pandadoc",
    "Connect your PandaDoc workspace by saving your API Key, after checking it actually "
    "works. Generate one in the Developer Dashboard (Sandbox key is free/self-serve; "
    "Production key requires PandaDoc Sales approval). This manages documents, templates, "
    "forms, contacts, webhooks, and your product catalog in your own PandaDoc workspace.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="pandadoc-connector.connect_pandadoc",
    effects=["pandadoc.provider.connected"],
)
async def connect_pandadoc(ctx, params: ConnectPandadocParams) -> ActionResult:
    """Connect a PandaDoc workspace via API Key."""
    api_key = params.api_key.strip()
    if not api_key:
        return ActionResult.error("Please provide your PandaDoc API Key.", code="PANDADOC_MISSING_FIELD")
    check = await pd.check_connection(ctx, api_key)
    if not check.get("ok"):
        return ActionResult.error(check.get("error", "Could not verify this API Key."), code=check.get("error_code", "PANDADOC_CONNECT_FAILED"))

    connections = await _load_connections(ctx)
    existing = next((c for c in connections if c.get("api_key") == api_key), None)
    if existing:
        existing.update({"label": params.label.strip() or existing.get("label", "")})
        await _save_connections(ctx, connections)
        return ActionResult.success(
            _connection_to_entity(existing),
            refresh_panels=["pandadoc_connect", "pandadoc_settings"],
        ), summary="Pandadoc connected."

    new_conn = {
        "id": str(uuid.uuid4()),
        "api_key": api_key,
        "label": params.label.strip(),
    }
    connections.append(new_conn)
    await _save_connections(ctx, connections)
    return ActionResult.success(
        _connection_to_entity(new_conn),
        refresh_panels=["pandadoc_connect", "pandadoc_settings"],
    ), summary="Pandadoc connected."


@chat.function(
    "disconnect_pandadoc",
    "Disconnect a PandaDoc workspace: deletes the saved API Key. Nothing in your PandaDoc "
    "account itself is changed.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="pandadoc-connector.disconnect_pandadoc",
    effects=["pandadoc.provider.disconnected"],
)
async def disconnect_pandadoc(ctx, params: DisconnectPandadocParams) -> ActionResult:
    """Run the PandaDoc operation: disconnect pandadoc."""
    connections = await _load_connections(ctx)
    if not connections:
        return ActionResult.error("No PandaDoc workspace is connected.", code="PANDADOC_ACCOUNT_MISSING")
    target_id = params.connection_id or connections[0].get("id", "")
    remaining = [c for c in connections if c.get("id") != target_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code="PANDADOC_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.success(
        DeleteResult(id=target_id, deleted=True),
        refresh_panels=["pandadoc_connect", "pandadoc_settings"],
    ), summary="Pandadoc disconnected."


@chat.function(
    "list_connections",
    "List the connected PandaDoc workspaces.",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
    event="pandadoc-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Run the PandaDoc operation: list connections."""
    connections = await _load_connections(ctx)
    return ActionResult.success(ProviderConnectionList(items=[_connection_to_entity(c) for c in connections])), summary="Connections listed."
