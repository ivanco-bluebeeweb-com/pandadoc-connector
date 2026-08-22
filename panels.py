"""Panel UI -- connections list/connect form.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as CircleCI
Connector's / GitLab CI/CD Connector's panels.py).

Every section (connections, connect form) is a plain ui.Stack, content
stacked vertically and left-aligned, sections separated by ui.Divider() --
no Card border/background/shadow anywhere in this slot. Disconnect lives
only in the "App settings" screen (panels_settings.py). The one secondary
"App settings" button is always the LAST element at the bottom of the
sidebar.

WHY A SINGLE API-KEY FORM, NOT A MULTI-FIELD CONNECTED-APP FORM (unlike
MuleSoft/Power Automate) -- see app.py's module docstring for the full
architectural reasoning: PandaDoc's own documented BYOK auth mechanism is
one API Key, no OAuth application, no org/environment ids to collect.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label (never placeholder-only), the placeholder text is
always contextually specific to what's being entered (never a generic
"Enter value"), the form's own container is stretched to the full width
of the left sidebar, and the form's inner content is stretched to fill
that container. The "How do I set this up?" instruction lives ONLY in
the help modal (pandadoc_connect_help below) -- it is not duplicated as
static sidebar text.
"""
from __future__ import annotations

from imperal_sdk import ui

import handlers_connection as h
from app import ext


def _settings_button() -> ui.UINode:
    """The single secondary 'App settings' button -- per UI_INTERFACE_STANDARD.md,
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__pandadoc_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or "PandaDoc workspace"
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text("API Key connection", variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No PandaDoc workspaces connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Form container stretched to the FULL WIDTH of the left sidebar, its
    inner content stretched to fill it (align="stretch" on both the outer
    Stack and the Form's own children Stack). No intro heading/description
    text here -- the API Key walkthrough lives ONLY in pandadoc_connect_help's
    modal (button below opens it); repeating it here would duplicate that
    instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__pandadoc_connect_help")),
        ui.Form(
            action="connect_pandadoc",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("API Key", variant="caption"),
                    ui.Password(param_name="api_key",
                                placeholder="Paste your PandaDoc API Key"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Sales workspace or Sandbox"),
                ]),
            ],
        ),
    ])


@ext.panel("pandadoc_connect", slot="left", title="PandaDoc", icon="📄",
           default_width=320, min_width=260, max_width=420)
async def pandadoc_connect_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="PandaDoc", level=2,
                        subtitle="Manage your documents, templates, forms and eSignature workflow from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected workspaces", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("pandadoc_connect_help", slot="center",
           title="How to connect PandaDoc", center_overlay=True)
async def pandadoc_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. Log into your PandaDoc account and open the Developer Dashboard (Settings > Integrations > API)."),
        ui.Text("2. Copy your Sandbox API Key for testing, or request Production API access from PandaDoc Sales for live use."),
        ui.Text("3. Paste it into the form here and connect."),
        ui.Divider(),
        ui.Alert(
            title="API Key is tied to your PandaDoc user",
            message=(
                "The key inherits the role/license of the user who created it. "
                "If that user is removed from the workspace, their keys stop "
                "working. This manages Documents, Templates, Forms, Content "
                "Library, Folders, Contacts, Workspace Members, Webhooks, "
                "Product/Pricing Catalog, and API request logs. Notary and "
                "Quotes-specific endpoints not covered by the general "
                "Documents API are out of scope."
            ),
            type="warning",
        ),
        ui.Divider(),
        ui.Link(
            label="Open PandaDoc's official API Key authentication guide",
            href="https://developers.pandadoc.com/reference/api-key-authentication-process",
        ),
    ])
    return ui.Dialog(
        title="How to connect PandaDoc",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("pandadoc_center", slot="center", title="PandaDoc", icon="📄", center_overlay=True)
async def pandadoc_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    return ui.Empty(
        message="Nothing to show here -- this app is managed entirely from the sidebar.",
        icon="👈",
    )
