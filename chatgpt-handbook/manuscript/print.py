import io
import os
from pathlib import Path
import re
import subprocess
import tempfile
from xml.sax.saxutils import escape, quoteattr

from lxml import html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, Image, KeepTogether, ListFlowable, ListItem, PageBreak,
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from build import DATE, DISPLAY_DATE, EDITIONS, ILLUSTRATION, OUT, VERSION

FONT_DIR = Path(os.environ.get("DEJAVU_FONT_DIR", "/usr/share/fonts/truetype/dejavu"))
for name, filename in (("Book", "DejaVuSans.ttf"), ("Book-Bold", "DejaVuSans-Bold.ttf"),
                       ("Book-Italic", "DejaVuSans-Oblique.ttf"), ("Mono", "DejaVuSansMono.ttf")):
    pdfmetrics.registerFont(TTFont(name, FONT_DIR / filename))
pdfmetrics.registerFontFamily("Book", normal="Book", bold="Book-Bold",
                             italic="Book-Italic", boldItalic="Book-Bold")
INK = colors.HexColor("#18251e")
MUTED = colors.HexColor("#48594e")
LINE = colors.HexColor("#d9e2d9")
TINT = colors.HexColor("#f1f5f1")
MARGIN = 52
WIDTH = A4[0] - 2 * MARGIN - 12


class ChapterMark(Flowable):
    def __init__(self, anchor, title):
        super().__init__()
        self.anchor = anchor
        self.title = title

    def draw(self):
        self.canv.bookmarkHorizontal(self.anchor, 0, 0)
        self.canv.addOutlineEntry(self.title, self.anchor, level=0)


def rich(node):
    output = escape(node.text or "")
    for child in node:
        inner = rich(child)
        if child.tag in ("strong", "b"):
            output += f"<b>{inner}</b>"
        elif child.tag in ("em", "i"):
            output += f"<i>{inner}</i>"
        elif child.tag == "a":
            output += f'<a href={quoteattr(child.get("href"))} color="#246644">{inner}</a>'
        elif child.tag == "code":
            output += f'<font name="Mono" size="9">{inner}</font>'
        else:
            output += inner
        output += escape(child.tail or "")
    return output


def cover_art():
    svg = re.search(r"<svg.*?</svg>", ILLUSTRATION, re.S).group()
    svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "cover.svg"
        target = Path(directory) / "cover.png"
        source.write_text(svg)
        subprocess.run(["inkscape", str(source), "--export-width=920",
                        "--export-filename=" + str(target)], check=True, capture_output=True)
        return target.read_bytes()


ART = cover_art()


def make_pdf(edition, item):
    number, name, subtitle, _, accent_hex = item
    accent = colors.HexColor(accent_hex)
    title = f"ChatGPT в деле / {name}"
    body = ParagraphStyle("body", fontName="Book", fontSize=11.25, leading=16.5, textColor=INK, spaceAfter=8)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=12, textColor=MUTED)
    eyebrow = ParagraphStyle("eyebrow", parent=small, fontName="Book-Bold", textColor=accent, spaceAfter=14)
    big = ParagraphStyle("big", parent=body, fontName="Book-Bold", fontSize=42, leading=45, spaceAfter=18)
    sub = ParagraphStyle("sub", parent=body, fontSize=16, leading=22, spaceAfter=18)
    h2 = ParagraphStyle("h2", parent=body, fontName="Book-Bold", fontSize=25, leading=30,
                        spaceAfter=18, keepWithNext=True)
    h3 = ParagraphStyle("h3", parent=body, fontName="Book-Bold", fontSize=12, leading=16,
                        spaceBefore=7, spaceAfter=5, keepWithNext=True)
    cell = ParagraphStyle("cell", parent=body, fontSize=10.1, leading=14)
    cell_head = ParagraphStyle("cell_head", parent=cell, fontName="Book-Bold")
    prompt = ParagraphStyle("prompt", parent=body, fontSize=10.6, leading=15)
    mono = ParagraphStyle("mono", parent=prompt, fontName="Mono", fontSize=8.7, leading=13)

    def table(node):
        rows = []
        for row in node.xpath("./thead/tr | ./tbody/tr | ./tr"):
            rows.append([Paragraph(rich(entry), cell_head if entry.tag == "th" else cell) for entry in row])
        result = Table(rows, colWidths=[WIDTH / len(rows[0])] * len(rows[0]), repeatRows=1)
        result.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TINT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), .4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return KeepTogether([result, Spacer(1, 10)])

    def block(node):
        if node.tag == "p":
            return Paragraph(rich(node), body)
        if node.tag == "section":
            return [block(child) for child in node]
        if node.tag == "h3":
            return Paragraph(rich(node), h3)
        if node.tag in ("ol", "ul"):
            entries = [ListItem(Paragraph(rich(child), body)) for child in node]
            return ListFlowable(entries, bulletType="1" if node.tag == "ol" else "bullet",
                                bulletFontName="Book", bulletFontSize=9, leftIndent=22, spaceAfter=8)
        if node.tag == "table":
            return table(node)
        if node.tag == "div" and "snippet" in node.get("class", ""):
            pre = node.find("pre")
            style = mono if set(pre.get("class", "").split()) & {"json", "python"} else prompt
            lines = pre.text_content().strip("\n").splitlines()
            markup = "<br/>".join(re.sub(r"^ +", lambda m: "&#160;" * len(m[0]), escape(line)) for line in lines)
            result = Table([[Paragraph(markup, style)]], colWidths=[WIDTH])
            result.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), TINT),
                ("LINEBEFORE", (0, 0), (0, 0), 2.5, accent),
                ("LEFTPADDING", (0, 0), (0, 0), 12),
                ("RIGHTPADDING", (0, 0), (0, 0), 12),
                ("TOPPADDING", (0, 0), (0, 0), 9),
                ("BOTTOMPADDING", (0, 0), (0, 0), 9),
            ]))
            return KeepTogether([result, Spacer(1, 10)])
        raise ValueError(f"Unexpected document node: {node.tag}")

    def append(story, node):
        if node.tag == "section":
            for child in node:
                append(story, child)
        else:
            story.append(block(node))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN, 38, A4[0] - MARGIN, 38)
        canvas.setFont("Book", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 26, f"CR20KB  /  {name}  /  {VERSION}")
        canvas.drawRightString(A4[0] - MARGIN, 26, str(document.page))
        canvas.restoreState()

    tree = html.fromstring((OUT / f"{edition}.html").read_text())
    chapters = tree.xpath("//section[@class='chapter']")
    story = [
        Spacer(1, 8), Paragraph(f"CR20KB  /  РУКОВОДСТВО ПО ЭКСПЛУАТАЦИИ  /  {number}", eyebrow),
        Paragraph("ChatGPT<br/>в деле", big),
        Paragraph(f"<b>{name}</b><br/>{subtitle}", sub),
        Image(io.BytesIO(ART), width=340, height=340 * 240 / 640, hAlign="LEFT"),
        Spacer(1, 8),
        Paragraph("Диалог, готовый результат и разработка. Выбирай способ работы по задаче.", small),
        Spacer(1, 10),
        Paragraph(f"Текст и примеры — ChatGPT для CR20KB<br/>Версия {VERSION} · Источники сверены {DISPLAY_DATE}", body),
        Spacer(1, 7), Paragraph("Оглавление", h3),
    ]
    toc = ParagraphStyle("toc", parent=body, fontSize=9.8, leading=13.5, spaceAfter=4)
    for i, chapter in enumerate(chapters, 1):
        anchor = chapter.get("id")
        heading = chapter.findtext("h2")
        story.append(Paragraph(f'<a href="#{anchor}" color="{accent_hex}">{i:02d}  {escape(heading)}</a>', toc))
    for i, chapter in enumerate(chapters, 1):
        heading = chapter.findtext("h2")
        story += [PageBreak(), ChapterMark(chapter.get("id"), heading),
                  Paragraph(f"CR20KB  /  {name.upper()}  /  {i:02d}", eyebrow),
                  Paragraph(escape(heading), h2)]
        for node in list(chapter)[1:]:
            append(story, node)

    path = OUT / f"CR20KB_ChatGPT_Handbook_{edition}.pdf"
    document = SimpleDocTemplate(
        str(path), pagesize=A4, topMargin=52, bottomMargin=54, leftMargin=MARGIN, rightMargin=MARGIN,
        title=title, author="ChatGPT для CR20KB", subject=f"Руководство по эксплуатации · {DATE}",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    for edition, item in EDITIONS.items():
        make_pdf(edition, item)
