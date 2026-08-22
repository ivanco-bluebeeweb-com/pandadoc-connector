# PandaDoc Connector — Connector Discovery

## 1. Целевой сервис и источники

PandaDoc — SaaS-платформа document automation / eSignature: proposals,
quotes, contracts, forms, продуктовый каталог с ценами, нотариальное
заверение (Notary), библиотека переиспользуемого контента.

Официальные источники, использованные для discovery (все прочитаны
2026-08-22):

- `developers.pandadoc.com/reference/about` — обзор API.
- `developers.pandadoc.com/reference/api-key-authentication-process` — API Key auth (заголовок `Authorization: API-Key {{api_key}}`).
- `developers.pandadoc.com/reference/authentication-process` — OAuth2 flow (`/oauth2/access_token`).
- `developers.pandadoc.com/reference/limits` — rate limits (per-user, sliding window 60s; sandbox = 10 RPM на любой эндпоинт; production — от 50 до 2000 RPM в зависимости от операции).
- `developers.pandadoc.com/reference/features` — feature overview (12 разделов).
- `raw.githubusercontent.com/PandaDoc/pandadoc-openapi-specification/main/openapi.yaml`, версия **8.11.1** — полная, официальная, машиночитаемая OpenAPI-схема. Использована как основной источник полного списка эндпоинтов (135+ операций).

## 2. Авторизация — выбор способа

Два способа, оба официально документированы:

| Способ | Механика | Когда уместен |
|---|---|---|
| **API Key** (выбран) | Заголовок `Authorization: API-Key {{api_key}}`. Sandbox-ключ — свободный (self-serve, Dev Center). Production-ключ требует approval от PandaDoc Sales. Ключ привязан к создавшему его пользователю (его роль/лицензия ограничивает возможности ключа); удаление пользователя из workspace деактивирует его ключи. | BYOK-коннектор для одного workspace/пользователя — тот же паттерн, что CircleCI/GitLab CI/CD/n8n/MuleSoft Connector. |
| OAuth2 (`/oauth2/access_token`) | Классический authorization code + refresh flow, для приложений, действующих от имени СТОРОННЕГО пользователя (multi-tenant SaaS-интеграция). | Избыточно для модели "подключи свой собственный аккаунт" — не выбран, оставлен вне текущего охвата (эквивалент решения по CircleCI: нет публичного OAuth-приложения для third-party "connect your account", здесь технически есть, но она не нужна для BYOK-модели). |

**Решение:** API Key, заголовок `Authorization: API-Key {{api_key}}`, форма
подключения — один секрет (ключ) + опциональный дружелюбный label + поле
sandbox/production переключатель (т.к. rate-limit и уровень доступа
разные, и это влияет на UX-подсказки об ошибках 429).

Rate limits (важно для UX ошибок 429): sandbox = 10 RPM на любой эндпоинт;
production — по операциям (List/Status/Delete = 2000 RPM, Create from
Template = 500 RPM, Send Document = 400 RPM, Create from PDF = 300 RPM,
Document Details = 600 RPM, Download = 100-300 RPM, Create Notarization
Request = 100 RPM). Max request body = 2MB, max PDF upload = 50MB.

## 3. Карта возможностей (направление на каждую)

| Возможность сервиса | Ingress / Egress / Both | Комментарий |
|---|---|---|
| List/Get/Search Documents | Ingress | list, get status, get details, beta search |
| Create Document (from template / PDF upload / Markdown upload) | Egress | 3 разных пути создания |
| Update Document / Update Document Status (draft↔sent) | Both | статус-машина документа |
| Delete Document (single + bulk) | Egress (destructive) | нативный bulk delete существует в API |
| Send Document | Egress | переводит в отправленный статус |
| Download Document / Download Protected | Ingress | получение готового PDF |
| Document Fields (list/create/update assignment) | Both | |
| Document Recipients (add/update/delete/reassign) | Both | reassign = "change signer" |
| Document Reminders (auto settings + status + manual send) | Both | |
| Document Attachments (list/create/create-from-upload/get/delete/download) | Both | |
| Document Sections/Bundles (list/create/create-from-upload/get/delete) | Both | составные документы |
| Document Link to CRM (linked objects) | Both | привязка к внешним CRM-объектам |
| Document Audit Trail (v2) | Ingress | журнал действий по документу |
| Document Settings (v2, get/update) | Both | |
| Document ownership (transfer single / bulk) | Egress | |
| Move document to folder | Egress | |
| Append Content Library Item to document | Egress | |
| Document Structure View — add named items (v2) | Egress | продвинутая работа со структурой |
| Quotes (update) | Egress | |
| Templates (list/create/create-from-upload/duplicate/update/delete/details/status) | Both | |
| Template Settings (v2, get/update) + Sharing (get/update) | Both | |
| Content Library Items (list/create/create-from-upload/get/details) | Both | нет delete в API |
| Forms (list) | Ingress | только list, PandaDoc не даёт CRUD форм через API |
| Folders — documents + templates (list/create/rename) | Both | нет delete в API |
| API Logs (v1 + v2, list + details) | Ingress | аудит вызовов самого API |
| Contacts (list/create/get/update/delete) | Both | |
| Members (list/get/current/create token) | Both | нет create/delete member через API |
| Webhook Subscriptions (list/create/get/update/delete/rotate shared key) | Both | |
| Webhook Events (list/get) | Ingress | справочник событий, на которые можно подписаться |
| Notary — Notaries (list) + Notarization Requests (list/create/get/delete) | Both | |
| Product Catalog Items (search/create/get/update/delete) | Both | line items с ценами |
| Workspaces (list/create/deactivate) + Members (add/remove/change role) | Both | |
| Users (list/create/get) | Both | |
| API Keys (create, per workspace) | Egress | |
| SMS Opt-outs (list) | Ingress | Communication Preferences |
| [Beta] DOCX Export Task (create/get) | Both | асинхронная задача экспорта |
| [Beta] Document Summary / Content / AI-metadata (single + bulk) | Ingress | AI-обогащённые данные о документе |
| [Beta] Document Search | Ingress | продвинутый поиск |

## 4. Ярус 1 — Ключевые функции (P0-кандидаты)

Полный документный жизненный цикл — то, ради чего в первую очередь ставят
PandaDoc: connect/disconnect, list/get/create (from template)/send/
download/delete documents, list/get templates, list contacts, list/create/
delete webhook subscriptions, get document status, add recipient.

## 5. Ярус 2 — Полное покрытие

Всё из карты §3, которое реализуемо через REST API — то есть **весь**
список эндпоинтов из OpenAPI-схемы 8.11.1, включая Notary, Product
Catalog, Content Library, Sections/Bundles, Audit Trail, Document
Settings/DSV, User & Workspace management, API Logs, Beta-эндпоинты
(DOCX export, Summary/Content/AI-metadata, Search). Ничего не отложено —
пользователь заявил максимум с первого сообщения.

Не покрыто (`not applicable`): OAuth2-flow как способ авторизации (см.
§2 — сознательно не выбран для BYOK-модели, не ограничение API); Forms —
только list, PandaDoc не предоставляет create/update/delete форм через
публичный API; Content Library Items и Folders — нет delete-эндпоинта в
API (сервис не предоставляет).

## 6. Ярус 3 — Функции на нашей стороне (value-add)

- `audit_workspace_health` — агрегированный отчёт по workspace: документы
  по статусам (draft/sent/viewed/completed/expired/declined), количество
  просроченных auto-reminder'ов, необработанные webhook-события,
  документы без назначенных получателей.
- `get_pending_signatures_report` — аналог `get_dunning_report` у Stripe
  Connector: документы в статусе "sent"/"viewed", ожидающие подписи дольше
  N дней — с последним статусом и получателями.
- Bulk-обёртки над одиночными операциями, которых у API нет "из коробки"
  за пределами уже нативного bulk-delete документов: `bulk_send_documents`,
  `bulk_add_recipients` (по списку document_id + один и тот же recipient),
  `bulk_delete_templates`, `bulk_create_documents_from_template`.
- `document_lifecycle_snapshot` — cross-check по одному документу:
  сводка статуса + получателей + полей + вложений + аудит-трейла в одном
  вызове (одна сущность, много под-эндпоинтов PandaDoc, собранных в одну
  читаемую карточку).

## 7. Решение по объёму этого захода

**Выбранная форма релиза: Ярус 1 + Ярус 2 + Ярус 3 — полное покрытие плюс
value-add (максимум).**

**Подтверждено исключением из `CONNECTOR_DISCOVERY_STANDARD.md`, Шаг 5:**
пользователь с первого сообщения по этой задаче написал буквально
"разработай это приложение в максимальной форме со всеми доступными
функциями с их стороны и всеми возможными функциями внутри нашего
приложения для повышения эффективности" — прямое указание на полный
объём. Повторный вопрос о форме релиза не задаётся; решение
зафиксировано этой записью и решение принято 2026-08-22.
