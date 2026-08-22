# PandaDoc Connector — Preparation

## 1. Паспорт приложения

- **Название:** PandaDoc Connector
- **Что это:** BYOK-коннектор к PandaDoc (document automation / eSignature) —
  создание, отправка, отслеживание и управление документами, шаблонами,
  формами, каталогом товаров/цен, контактами, папками, вебхуками и
  нотариальным заверением напрямую из Imperal.
- **Владелец продукта:** Imperal Cloud (developer imp_u_NBzuhNN-te).
- **Дата и версия подготовки:** 2026-08-22, v1 (полный объём с первого захода).
- **Почему сейчас:** прямой явный запрос пользователя — "разработай в
  максимальной форме со всеми доступными функциями с их стороны и всеми
  возможными функциями внутри нашего приложения для повышения
  эффективности". Согласно `CONNECTOR_DISCOVERY_STANDARD.md` Шаг 5,
  исключение — вопрос о форме релиза не задаётся повторно, когда форма уже
  явно заявлена Владом с первого сообщения.
- **Связанное событие:** пополнение портфеля document-automation рядом с
  существующими коннекторами (HubSpot, Salesforce, Stripe и др.) —
  document workflow — частый downstream шаг после CRM-сделки.

## 2. Проблема в человеческих словах

Когда **менеджер по продажам или операционный сотрудник** сталкивается с
**необходимостью подготовить/отправить/отследить коммерческое предложение,
договор или форму**, ему приходится **вручную заходить в отдельный
PandaDoc-интерфейс, искать шаблон, вручную выставлять получателей, вручную
проверять статус подписания, вручную отправлять напоминания и вручную
сверять данные с CRM**, из-за чего возникает **потеря времени, забытые
напоминания, документы без owner'а, рассинхронизация с CRM/Sales Strategy
Hub, и отсутствие единой сводки "что происходит со всеми документами
компании прямо сейчас"**.

## 3. Пользователи, роли и права

| Роль | Job to be done | Данные | Права |
|---|---|---|---|
| Sales / Account manager | Быстро создать документ из шаблона, отправить на подпись, отследить статус | Документы, получатели, шаблоны, контакты | Создавать/отправлять/просматривать свои документы |
| Ops / Document admin | Управлять шаблонами, каталогом товаров, папками, вебхуками, доступом workspace | Templates, Product Catalog, Folders, Webhooks, Users/Workspaces | Полный CRUD на конфигурацию workspace |
| Владелец аккаунта (Vlad) | Видеть health/audit всего документооборота, находить застрявшие документы | Все документы всех статусов, member list | Читает всё, может запускать bulk-операции и аудит |

## 4. Сценарии и точки решения человека

**Основной сценарий — "создать и отправить документ из шаблона":**

```
триггер: нужно отправить КП клиенту
→ действие человека: выбрать шаблон + указать получателя (имя/email) в чате/панели
→ действие приложения: create_document (из шаблона, с pre-filled полями) → get_document (проверка статуса draft)
→ review/approval человека: подтверждает содержимое/получателей перед отправкой
→ действие приложения: send_document
→ результат: клиент получает документ на подпись; статус отслеживается через list_documents/get_document, авто-напоминания включены
```

- **Happy path:** шаблон существует → документ создаётся в draft → отправляется → подписывается.
- **Missing/error path:** шаблон не найден / получатель без email → явная ошибка с указанием, что проверить.
- **Blocked state:** документ в статусе `document.error` (PandaDoc не смог сгенерировать) — репортим статус, не пытаемся угадать причину.
- **Recovery path:** `void_document`/пересоздание, или `move_document_to_draft` для правки перед повторной отправкой.
- **Точка человека:** отправка (`send_document`) и любое удаление/аннулирование — только по explicit confirmation; создание workspace-пользователей и смена ролей — тоже explicit.

**Второй сценарий — "аудит документооборота":** `audit_document_pipeline`
(наша value-add функция) — агрегирует статусы всех документов, находит
просроченные без ответа сверх N дней, документы без recipient, черновики
старше N дней — единый отчёт вместо ручного пролистывания списка.

## 5. Ценность и измеримый результат

- Время от "нужно отправить КП" до факта отправки — сокращается за счёт
  отсутствия переключения в отдельный PandaDoc UI.
- Доля документов с известным актуальным статусом (не "забыт в черновиках").
- Число документов, ожидающих подписи больше N дней без напоминания —
  должно снижаться благодаря `audit_document_pipeline` и bulk-reminder.
- Неуспех: если после запуска ни один документ не создаётся через
  коннектор (используют только PandaDoc UI напрямую) — сигнал, что
  discoverability/UX в панели недостаточны.

## 6. Границы: делает / не делает

**Делает (P0 + полный охват):** весь документный workflow (create/send/
status/download/void), recipients, fields, reminders, attachments, linked
objects (CRM linking), sections/bundles, DSV named items, audit trail,
document settings; templates (полный CRUD + sharing + settings);
content library items; forms (list); folders (documents + templates);
contacts; members/workspaces/users (административная сторона); webhooks +
webhook events; product catalog (pricing tables); quotes; notary; API logs;
beta: DOCX export, AI metadata, document summary/content, document search.

**Не делает:** платежи/обработка карт (PandaDoc сам не обрабатывает
платежи через этот API); не создаёт юридическую оценку содержимого
документа; не принимает решение "подписывать или нет" за человека;
embedded-sign iframe рендерится PandaDoc'ом — коннектор только выдаёт
сессионный URL/токен, не встраивает свой собственный signing UI.

**Рискованные действия, требующие explicit confirmation:** `send_document`
(необратимо запускает подписание у получателя), `delete_document`/
`bulk_delete_documents` (необратимо), `void`-подобные операции статуса,
`delete_template`, `delete_contact`, `deactivate_workspace`,
`remove_member`, `delete_webhook_subscription`, `delete_notarization_request`,
`delete_catalog_item`.

## 7. Данные, конфиденциальность и интеграции

- Минимально необходимые данные: API Key (secret), опционально несколько
  подключений (мульти-workspace, как у CircleCI/GitLab Connector).
- Источник данных: PandaDoc REST API напрямую (`api.pandadoc.com`), без
  промежуточного хранения содержимого документов на стороне Imperal —
  коннектор только проксирует вызовы и кэширует ничего сверх обычного
  ответа запроса.
- Retention: сам API-ключ хранится в `ctx.secrets` (тот же паттерн, что и
  у остальных BYOK-коннекторов); документы/шаблоны/контакты остаются
  исключительно в PandaDoc, Imperal их не реплицирует.
- Tenant isolation: один список подключений на пользователя, каждое
  подключение — самостоятельный API Key одного workspace.
- Интеграции: **available** — прямой REST API (подтверждено официальной
  OpenAPI-схемой и рабочими примерами в докстроке `panels.py`, `pandadoc_client.py`
  в момент реализации). См. `CONNECTOR_DISCOVERY.md` для полной карты по
  трём ярусам.

## 8. P0 — минимальный законченный полезный путь

Главный use case: создать документ из шаблона → отправить → отследить
статус до подписания. Сущности: connection (API key), template, document,
recipient. Safety gate: send/delete/void — explicit confirmation.
Сознательно исключено из чистого P0 (но включено в этот заход по прямому
указанию Влада на максимальный объём): Notary, DOCX export beta,
AI-metadata beta — низкочастотные продвинутые сценарии, но реализуются
всё равно, т.к. заявлен полный охват.

## 9. UX-карта Imperal panel

- **Точка входа:** сайдбар PandaDoc Connector → форма подключения (API Key
  + label) либо список активных подключений.
- **Первый экран:** список последних документов (`list_documents`,
  топ-10, с статусом) + быстрые действия (создать из шаблона).
- **Primary next action:** "Создать документ из шаблона" / "Отправить
  документ" / открыть "App settings" для управления подключениями,
  вебхуками, papkami по умолчанию.
- **Empty state:** "Нет подключённых аккаунтов PandaDoc — подключите API
  Key, чтобы видеть документы."
- **In-progress:** документ в статусе draft/sent — явный бейдж статуса.
- **Blocked:** `document.error` — текст ошибки от PandaDoc как есть.
- **Ready-for-review / approved:** completed — ссылка на скачивание.
- **Ошибки:** неверный API Key → явное сообщение с указанием куда идти
  (Dev Center) без выдумывания причины сверх ответа API.
- **App settings:** единая кнопка в сайдбаре, весь центр-слот настроек —
  подключения (добавить/отключить), вебхуки, папки по умолчанию — по
  `UI_INTERFACE_STANDARD.md`.

## 10. Safety, approvals и audit trail

- Webbee может сама: все `list_*`/`get_*` чтения, создание документов в
  draft, создание/обновление шаблонов, контактов, папок, вебхуков.
- Webbee может только предложить и должна получить explicit confirmation:
  `send_document`, любые `delete_*`/`bulk_delete_*`, `deactivate_workspace`,
  `remove_member_from_workspace`, `delete_notarization_request`.
- Audit trail: PandaDoc сам ведёт `List Document Audit Trail` — коннектор
  читает его (`list_document_audit_trail`), не дублирует свой лог.
- Fail closed: если API Key не проходит проверку при `connect_pandadoc` —
  подключение не сохраняется.

## 11. Discovery и проверка гипотезы

Полный официальный API-reference уже полностью прочитан (135+ операций,
опубликованная OpenAPI-схема v8.11.1) — гипотеза не требует внешнего
интервью для этого технического коннектора; форма релиза (максимальный
охват) явно задана пользователем.

## 12. План воплощения

1. `CONNECTOR_DISCOVERY.md` — готово.
2. `PREPARATION.md` — этот файл.
3. Реализация: `app.py`, `pandadoc_client.py`, `schemas.py`, набор
   `handlers_*.py` по доменам (connection, documents, recipients/fields/
   reminders/attachments, templates, content-library, forms, folders,
   contacts, members/workspaces, webhooks, product-catalog/quotes, notary,
   logs, beta/AI, bulk/audit value-add), `panels.py` + `panels_settings.py`,
   `main.py`, `icon.svg`, `requirements.txt`.
4. `imperal validate` до зелёного результата.
5. `deploy_app` → `update_pricing` (см. `PRICING_HISTORY.md`) →
   `submit_for_review` — строго в этом порядке, без исключений
   (`PRICING_POLICY.md` §1).
