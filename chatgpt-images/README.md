# Картинки с ChatGPT

Самостоятельное руководство CR20KB. Текст и примеры подготовил ChatGPT. Версия **1.0.0**, источники сверены **6 ноября 2026**.

| Редакция | Исходник | Скачать |
|---|---|---|
| Млад и стар | [Markdown](manuscript/easy.md) | [PDF](release/CR20KB_ChatGPT_Images_easy.pdf) |
| Стандарт | [Markdown](manuscript/standard.md) | [PDF](release/CR20KB_ChatGPT_Images_standard.pdf) |
| Профи | [Markdown](manuscript/pro.md) | [PDF](release/CR20KB_ChatGPT_Images_pro.pdf) |

[Читать онлайн на CR20KB](https://cr20kb.com/utilities/chatgpt-images/).

## Сборка и обновление

Отредактируйте нужные главы в `manuscript/*.md`. Если сверили источники, обновите дату в `manuscript/build.py`. При изменении текста обновите номер версии и добавьте запись в журнал ниже. Соберите HTML командой `python manuscript/build.py` с Python 3 и Pandoc. Сгенерируйте три PDF командой `python manuscript/print.py` с ReportLab, lxml, DejaVu Sans и Inkscape. Результат в `release/`.

Проверьте оглавление, команды для копирования, экран телефона и все страницы PDF. Опубликуйте те же файлы в `utilities/chatgpt-images/` на CR20KB. Сверьте дату и версию в GitHub и на сайте.

### Журнал

- **1.0.0 · 2026-11-06** — три самостоятельные редакции. Работа в ChatGPT, оригинальные примеры, приёмка, приложение по API.
