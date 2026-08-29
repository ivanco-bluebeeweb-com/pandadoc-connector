# PandaDoc Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: sales-менеджер/
руководитель отдела продаж на PandaDoc.

## 1. Credential type
API key (Sandbox или Production, одно поле + опциональный label).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой на Developer Dashboard + явное объяснение
   разницы Sandbox/Production ключей (Sandbox для теста интеграции, Production для
   реальной отправки документов клиентам).
2. **Форма** — api_key (password-type) + friendly label.
3. **После успеха** — `audit_workspace_health` сразу: отправлено/просмотрено/не
   подписано — прямой ответ на "где застряли сделки" для sales-менеджера.
4. **Viewed-but-not-signed emphasis** — документы, просмотренные, но не подписанные N+
   дней — сильный сигнал "нужно позвонить клиенту" — визуально выделить.
5. **Ошибка "sandbox key in production call"** — если использован явно Sandbox-ключ
   для реальной отправки — конкретное предупреждение, не тихий сбой.

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
