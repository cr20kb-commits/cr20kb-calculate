from html import escape
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "release"
VERSION = "1.0.0"
DATE = "2026-11-06"
DISPLAY_DATE = "6 ноября 2026"
GITHUB = "https://github.com/cr20kb-commits/cr20kb-calculate/tree/main/chatgpt-handbook"
PUBLIC = "https://cr20kb.com/utilities/chatgpt-handbook/"
EDITIONS = {
    "easy": ("01", "Млад и стар", "От первого вопроса до своей задачи", "Вопросы, обучение, поиск, голос, фото, файлы, расчёты, проекты и напоминания.", "#317659"),
    "standard": ("02", "Стандарт", "Повседневная работа с ChatGPT", "Исследования, документы, таблицы, медиа, подключённые приложения и приёмка результата.", "#225c83"),
    "pro": ("03", "Профи", "Разработка и эксплуатация рабочих процессов", "Codex, Git, права, Sites, API, MCP, автоматизация и проверка выпуска.", "#81552b"),
}
CSS = """
*{box-sizing:border-box}
:root{color-scheme:light;--paper:#fff;--surface:#eef1ee;--ink:#18251e;--muted:#48594e;--line:#d9e2d9}
body{margin:0;background:var(--surface);color:var(--ink);font:17px/1.6 system-ui,'Segoe UI',sans-serif}
a{color:var(--accent);text-underline-offset:.16em}
a:focus-visible,button:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
main{width:min(100% - 32px,920px);margin:auto;padding:20px 0 48px}
.top,.actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.top{justify-content:space-between;margin-bottom:18px;font-size:.9rem}
.top a{font-weight:650}
.cover,.chapter,.card{background:var(--paper);border:1px solid var(--line);border-radius:17px}
.cover,.chapter{padding:clamp(18px,4vw,42px);margin-bottom:16px}
.cover{border-top:5px solid var(--accent)}
.kicker,.label{font-size:.75rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1,h2,h3,p{margin-top:0}
h1{font-size:clamp(2.2rem,7vw,4.15rem);line-height:1.02;letter-spacing:-.045em;margin:.25em 0}
h2{font-size:clamp(1.45rem,4.5vw,2rem);line-height:1.16;margin:.2em 0 .65em}
h3{font-size:1.1em;line-height:1.2;margin:1.1em 0 .45em}
p,ul,ol{margin-bottom:.9em}
.lead{font-size:1.23em;line-height:1.38;max-width:36rem}
.meta,.muted,footer{color:var(--muted);font-size:.9em}
.cover figure{max-width:660px;margin:20px 0}
.cover svg{display:block;width:100%;height:auto}
figcaption{font-size:.84em;color:var(--muted);margin-top:8px}
.toc{margin-top:20px;border-top:1px solid var(--line);padding-top:12px}
.toc ol{margin-top:6px;padding-left:1.45em}
.toc a{text-decoration:none}
.toc a:hover{text-decoration:underline}
.chapter{scroll-margin-top:12px}
pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--ink);font:inherit}
code{font-family:ui-monospace,Consolas,monospace;overflow-wrap:anywhere;font-size:.92em}
pre code{font:inherit}
.snippet{position:relative;background:#f2f6f2;border-left:3px solid var(--accent);border-radius:0 9px 9px 0;padding:12px 15px;margin:0 0 1em}
.copy{margin-top:9px;background:white;border:1px solid var(--line);border-radius:7px;padding:4px 9px;color:var(--accent);font:inherit;font-size:.79em;font-weight:700;cursor:pointer}
table{border-collapse:collapse;width:100%;table-layout:fixed;margin:.45em 0 1.1em;font-size:.91em}
th,td{padding:7px 9px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
th{background:#edf3ee;color:var(--ink)}
.button{display:inline-block;background:var(--accent);color:white;text-decoration:none;font-weight:700;border-radius:8px;padding:7px 12px}
.secondary{background:white;border:1px solid var(--line);color:var(--accent)}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}
.card{padding:18px;display:flex;flex-direction:column;border-top:4px solid var(--accent)}
.card h2{font-size:1.42rem}
.card .actions{margin-top:auto}
.card .button{font-size:.89em}
footer{border-top:1px solid var(--line);padding:14px 0}
@media(max-width:690px){.cards{grid-template-columns:1fr}.top{justify-content:flex-start}}
@page{size:A4;margin:16mm 17mm 17mm}
@media print{
  body{background:white;font-size:11.5pt;line-height:1.45}
  main{width:auto;margin:0;padding:0}
  .screen-only,button,footer{display:none!important}
  .cover,.chapter{border:0;border-radius:0;padding:0;margin:0}
  .cover{padding-top:7mm;border-top:4pt solid var(--accent)}
  .chapter{break-before:page;padding-top:3mm}
  .chapter h2{margin-top:3mm}
  h1{font-size:36pt}
  h2{font-size:23pt}
  h3{break-after:avoid}
  table,.snippet,figure{break-inside:avoid}
  .cover figure{margin:10mm 0}
  .toc{margin-top:7mm}
  a{text-decoration:none}
}
"""
ILLUSTRATION = """
<figure><svg viewBox="0 0 640 240" role="img" aria-labelledby="graphic-title graphic-desc">
<title id="graphic-title">Три способа работы с ChatGPT</title>
<desc id="graphic-desc">Три карточки изображают диалог, рабочий документ и среду разработки.</desc>
<rect width="640" height="240" rx="18" fill="#183328"/>
<path d="M28 120h584" stroke="#375d4c" stroke-width="2" stroke-dasharray="5 9"/>
<rect x="46" y="46" width="156" height="148" rx="16" fill="#d8e8d4"/>
<rect x="242" y="46" width="156" height="148" rx="16" fill="#d8e6ec"/>
<rect x="438" y="46" width="156" height="148" rx="16" fill="#ecdfcb"/>
<path d="M83 83h82a9 9 0 0 1 9 9v39a9 9 0 0 1-9 9h-48l-24 18v-18H83a9 9 0 0 1-9-9V92a9 9 0 0 1 9-9z" fill="#317659"/>
<circle cx="102" cy="112" r="4" fill="#fff"/><circle cx="124" cy="112" r="4" fill="#fff"/><circle cx="146" cy="112" r="4" fill="#fff"/>
<path d="M287 73h47l19 19v73h-66z" fill="#225c83"/><path d="M334 73v20h19m-51 17h34m-34 15h34m-34 15h23" fill="none" stroke="#edf5f8" stroke-width="4" stroke-linecap="round"/>
<rect x="470" y="83" width="92" height="74" rx="8" fill="#81552b"/>
<path d="M470 100h92m-69 14 11 9-11 9m20 2h22" fill="none" stroke="#fff4e4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<g fill="#fff4e4"><circle cx="482" cy="92" r="2"/><circle cx="491" cy="92" r="2"/><circle cx="500" cy="92" r="2"/></g>
</svg><figcaption>Диалог, готовый результат и разработка. Выбирай способ работы по задаче.</figcaption></figure>
"""
SCRIPT = """
document.querySelectorAll('.snippet pre').forEach(pre => {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'copy screen-only';
  button.textContent = 'Копировать команду';
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(pre.textContent.trim());
      button.textContent = 'Скопировано';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(pre);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = 'Текст выделен';
    }
  });
  pre.after(button);
});
"""

def document(title, description, accent, canonical, body, script=""):
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{escape(description, quote=True)}">
<meta name="theme-color" content="#eef1ee">
<meta name="cr20kb-edition" content="{VERSION}">
<meta name="cr20kb-verified" content="{DATE}">
<link rel="canonical" href="{canonical}">
<title>{escape(title)}</title>
<style>:root{{--accent:{accent}}}{CSS}</style>
</head><body><main>
{body}
</main>{f'<script>{script}</script>' if script else ''}</body></html>
'''

def book(edition, item):
    number, name, subtitle, summary, accent = item
    source = (HERE / f"{edition}.md").read_text()
    html = subprocess.run(["pandoc", "-f", "markdown", "-t", "html5", "--section-divs", "--no-highlight"],
                          input=source, text=True, capture_output=True, check=True).stdout
    chapters = re.findall(r'<section id="([^"]+)" class="level2">\s*<h2>(.*?)</h2>', html)
    if len(chapters) != source.count("\n## ") + 1:
        raise ValueError(f"Chapter mismatch in {edition}")
    html = re.sub(r'<section id="([^"]+)" class="level2">', r'<section class="chapter" id="\1">', html)
    html = re.sub(r'(<pre\b.*?</pre>)', r'<div class="snippet">\1</div>', html, flags=re.S)
    toc = "".join(f'<li><a href="#{anchor}">{title}</a></li>' for anchor, title in chapters)
    return document(f"ChatGPT в деле · {name} | CR20KB", summary, accent, PUBLIC + f"{edition}.html", f'''
<nav class="top screen-only" aria-label="Навигация по книге"><a href="./index.html">← Все редакции</a>
<a href="./CR20KB_ChatGPT_Handbook_{edition}.pdf">Скачать PDF</a></nav>
<header class="cover">
<p class="kicker">CR20KB · Руководство по эксплуатации · {number}</p>
<h1>ChatGPT<br>в деле</h1>
<p class="lead"><strong>{name}</strong><br>{subtitle}</p>
{ILLUSTRATION}
<p class="meta">Текст и примеры — ChatGPT для CR20KB<br>Версия {VERSION} · Источники сверены {DISPLAY_DATE}</p>
<nav class="toc" aria-label="Оглавление"><strong>Оглавление</strong><ol>{toc}</ol></nav>
</header>
{html}
<footer class="screen-only">Самостоятельное руководство CR20KB. <a href="{GITHUB}">Исходники на GitHub</a>.</footer>''', SCRIPT)

def landing():
    cards = []
    for key, (number, name, subtitle, summary, accent) in EDITIONS.items():
        cards.append(f'''<section class="card" style="--accent:{accent}">
<p class="label">Редакция {number}</p><h2>{name}</h2><p>{summary}</p>
<div class="actions"><a class="button" href="./{key}.html" aria-label="Читать редакцию {name}">Читать</a>
<a class="button secondary" href="./CR20KB_ChatGPT_Handbook_{key}.pdf" aria-label="Скачать PDF редакции {name}">PDF</a></div>
</section>''')
    return document("ChatGPT в деле | CR20KB", "Три самостоятельные книги о работе с ChatGPT, Work и Codex.", "#317659", PUBLIC, f'''
<nav class="top" aria-label="Навигация CR20KB"><a href="https://cr20kb.com/utilities/">← Полезности CR20KB</a><a href="{GITHUB}">Исходники на GitHub ↗</a></nav>
<header class="cover">
<p class="kicker">CR20KB · Руководство по эксплуатации</p>
<h1>ChatGPT<br>в деле</h1>
<p class="lead">Моя инструкция по работе со мной. От обычного вопроса и обучения до документов, исследований, разработки и автоматизации.</p>
{ILLUSTRATION}
<p class="meta">Версия {VERSION} · Источники сверены {DISPLAY_DATE} · Три редакции на русском</p>
</header>
<div class="cards">{''.join(cards)}</div>
<footer>Текст и примеры — ChatGPT для CR20KB. <a href="https://learn.chatgpt.com/docs/features">Документация OpenAI</a> · <a href="https://cr20kb.com/utilities/chatgpt-images/">Отдельная книга по картинкам</a></footer>''')

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for edition, item in EDITIONS.items():
        (OUT / f"{edition}.html").write_text(book(edition, item))
    (OUT / "index.html").write_text(landing())
