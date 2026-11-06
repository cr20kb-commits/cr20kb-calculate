# ChatGPT в деле

Три самостоятельные книги CR20KB. Текст и упражнения подготовил ChatGPT. Версия **1.0.0**, документация сверена **6 ноября 2026**.

| Книга | Рукопись | PDF |
|---|---|---|
| Млад и стар | [Markdown](manuscript/easy.md) | [PDF](release/CR20KB_ChatGPT_Handbook_easy.pdf) |
| Стандарт | [Markdown](manuscript/standard.md) | [PDF](release/CR20KB_ChatGPT_Handbook_standard.pdf) |
| Профи | [Markdown](manuscript/pro.md) | [PDF](release/CR20KB_ChatGPT_Handbook_pro.pdf) |

[Читать на CR20KB](https://cr20kb.com/utilities/chatgpt-handbook/) · [Отдельное руководство по картинкам](https://cr20kb.com/utilities/chatgpt-images/).

## Сборка и сопровождение

1. Редактируй Markdown в `manuscript/`. Ссылки на первичные источники стоят в главах.
2. При содержательном изменении обнови версию, дату сверки в `manuscript/build.py` и журнал. Дату храни в ISO-формате и в человекочитаемом виде.
3. Из этой папки собери HTML командой `python manuscript/build.py` с Python 3 и Pandoc.
4. Собери PDF командой `python manuscript/print.py` с ReportLab, lxml, DejaVu Sans и Inkscape. Выходные файлы в `release/`.
5. Проверь все страницы PDF, оглавления, внутренние ссылки и кнопки копирования. Комплект из `release/` публикуется на CR20KB в `utilities/chatgpt-handbook/`.
6. Открой рабочий URL после деплоя. Сверь версию, карточку раздела «Полезности», все три веб-редакции и скачивание PDF.

### Журнал

- **1.0.0 · 2026-11-06** — первый выпуск. От базовых запросов до Work, Codex, Sites, API, интеграций и автоматизации.
