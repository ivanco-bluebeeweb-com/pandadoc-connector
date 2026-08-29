# PandaDoc Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `pandadoc-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(workspace) + `ui.Divider` + navigation `ui.ListItem`(Documents/Templates/Catalog) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Document List (center, `center_overlay=True`) | `ui.Stats`(Sent/Viewed/Completed this month) + `ui.Select`(status_filter) + `ui.DataTable`(name, recipient, status Badge draft/sent/viewed/completed, date; sortable) | `DataTable` — стандартный способ работы с потоком документов на подпись. |
| Document Detail | Back-button + `ui.KeyValue`(recipient/pricing total/created) + `ui.Timeline`(document_state_changed events) + `ui.Row`(Button "Send", "Send Reminder", "Delete") | `Timeline` отражает жизненный цикл документа (draft→sent→viewed→completed). |
| Pricing Table Viewer | `ui.DataTable`(item, qty, price, subtotal; sortable) | Таблица позиций коммерческого предложения — прямое использование DataTable. |
| Template List | `ui.List`(templates: name, roles count) + `ui.Button`("Создать документ из шаблона") | Список шаблонов для запуска нового документа. |
| Create Document Form | `ui.Form`(action="create_document") + `ui.Select`(template_id) + N×`ui.Input`(type="email", recipient_email по числу ролей) | Форма подстраивается под шаблон аналогично DocuSign. |
| Catalog (products) | `ui.DataTable`(sku, name, price) | Каталог товаров/услуг для построения pricing table в документе. |
| Content Library | `ui.List`(reusable blocks/clauses) | Библиотека переиспользуемых блоков контента. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Webhooks CRUD, API Logs]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__pandadoc_sidebar` рендерит workspace + разделы;
   `auto_action` открывает Document List, если `not active_view`.
2. Document List: Select статуса → DataTable → клик на строку →
   `ui.Call("__panel__pandadoc_center", document_id=...)` → Document Detail.
3. Document Detail: Button "Send" → `send_document` → `refresh_panels=["pandadoc_center"]`;
   Button "Send Reminder" → `send_manual_reminder` без Dialog (не деструктивно).
   Button "Delete" → `ui.Dialog`(confirm_label="Удалить") → `delete_document` →
   возврат к Document List.
4. Раздел "Templates" → List → клик "Создать из шаблона" → Create Document Form →
   Button "Создать" → `create_document` → открывает новый Document Detail.
5. "App settings" → отдельный center overlay с Accordion-секциями.

## 3. Конкретные экраны (screens)

### Screen: Document List (`pandadoc_center`, default)
- Stats row: Sent / Viewed / Completed this month.
- Select (статус) сверху таблицы.
- DataTable: name, recipient, status Badge, date — row-click → Document Detail.

### Screen: Document Detail (`pandadoc_center` + `document_id`)
- Back-button "← К документам".
- KeyValue: recipient, pricing total, created date.
- DataTable: строки pricing table (если есть).
- Timeline: смена статусов документа.
- Row кнопок: Send, Send Reminder, Delete (Dialog-подтверждение).

### Screen: Create Document (`pandadoc_create` + `template_id`)
- Select шаблона.
- N×Input(email) по числу ролей шаблона.
- Button "Создать документ".

### Screen: App settings (`pandadoc_settings`)
- Accordion "Подключение": workspace, Disconnect (Dialog-подтверждение).
- Accordion "Webhooks": List + Button "Добавить".
- Accordion "API Logs": DataTable последних запросов.
