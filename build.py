from base64 import b64encode
from html import escape
from itertools import groupby
from json import dumps, loads
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
LANGUAGES = {"sk": "Slovenčina", "cs": "Čeština", "la": "Latinčina"}
CONTENTS = {"sk": "Obsah", "cs": "Obsah", "la": "Index"}
TIMESTAMP = "2026-11-19T00:00:00Z"


def valid_id(value):
    if not re.fullmatch(r"[a-z][a-z0-9-]*", value):
        raise ValueError(f"Invalid anchor: {value}")
    return value


def html_document(title, lang, body, *, work="", portable_views=None, portable_index=None):
    standalone = portable_views is not None
    templates = ""
    scripts = ("preferences.js", "reader.js", "search-index.js", "search.js")
    if standalone:
        style = (DOCS / "style.css").read_text(encoding="utf-8")
        assets = f"<style>{style}</style>"
        templates = "\n".join(f'<template data-work-view="{slug}">{view}</template>' for slug, view in portable_views.items())
        scripts_text = "\n".join((DOCS / js).read_text(encoding="utf-8") for js in scripts if js != "search-index.js")
        offline_index = dumps(portable_index, ensure_ascii=False).replace("<", "\\u003c")
        javascript = f"""<script>
        (() => {{
          const work = new URLSearchParams(location.search).get("dielo");
          const view = [...document.querySelectorAll("template[data-work-view]")].find((item) => item.dataset.workView === work);
          if (view) {{
            document.querySelector("main").replaceChildren(view.content.cloneNode(true));
            document.documentElement.dataset.work = work;
          }}
        }})();
        const searchIndex = {offline_index};
        {scripts_text}</script>"""
    else:
        assets = '<link rel="stylesheet" href="style.css">'
        javascript = "\n".join(f'<script src="{js}" defer></script>' for js in scripts)
    brand_target = "#zaciatok" if standalone else "index.html"
    work_actions = """
      <a href="#obsah" class="contents-link">Obsah</a>
      <button type="button" data-open="porovnanie" hidden>Porovnať</button>
    """ if work else ""
    document = f"""<!doctype html>
<html lang="sk" data-work="{work}" data-language="{lang}" data-standalone="{str(standalone).lower()}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · Tomáš Akvinský</title>
  {assets}
</head>
<body>
  <a class="skip" href="#zaciatok">Preskočiť na obsah stránky</a>
  <header class="masthead">
    <div class="topbar">
      <a class="brand" href="{brand_target}" aria-label="Tomáš Akvinský"><span aria-hidden="true" class="brand-mark">T</span><span>Tomáš Akvinský</span></a>
      <nav aria-label="Nástroje knižnice">
        {work_actions}
        <button type="button" id="show-search" hidden>Hľadať</button>
        <button type="button" data-open="nastavenia" hidden>Nastavenia</button>
      </nav>
    </div>
  </header>
  <main id="zaciatok">{body}</main>
  <dialog id="nastavenia" aria-labelledby="settings-title">
    <div class="dialog-heading"><h2 id="settings-title">Nastavenia čítania</h2>
      <form method="dialog"><button>Zavrieť</button></form></div>
    <label for="theme">Motív</label>
    <select id="theme" name="theme">
      <option value="system">Podľa systému</option><option value="light">Svetlý</option><option value="dark">Tmavý</option>
    </select>
    <label for="accent">Farebný odtieň</label>
    <select id="accent" name="accent">
      <option value="green">Zelený</option><option value="blue">Jemne modrý</option>
      <option value="violet">Levanduľový</option><option value="amber">Teplý jantárový</option>
    </select>
    <label for="font">Písmo čítania</label>
    <select id="font" name="font">
      <option value="serif">Pätkové</option><option value="sans">Bezpätkové</option>
    </select>
    <label for="page-axis">Listovanie ťuknutím</label>
    <select id="page-axis" name="pageAxis" aria-describedby="tap-tip">
      <option value="horizontal">Ľavý a pravý okraj</option>
      <option value="vertical">Horný a dolný okraj</option>
      <option value="off">Vypnuté</option>
    </select>
    <p id="tap-tip" class="muted">Krajných 30 % obrazovky. Ľavá alebo horná zóna listuje späť, pravá alebo dolná dopredu.</p>
  </dialog>
  {templates}
  {javascript}
</body>
</html>
"""
    return "\n".join(line.rstrip() for line in document.split("\n"))


def search_markup(work=""):
    title = "Hľadať v tomto diele" if work else "Hľadať v textoch"
    return f"""
    <div class="search" data-search="{work}" hidden>
      <form role="search" id="search">
        <label for="query">{title}</label>
        <div class="search-line">
          <input id="query" type="search" name="q" placeholder="Zadajte slovo alebo frázu" required>
          <button class="primary" type="submit">Vyhľadať</button>
        </div>
      </form>
      <p id="search-status" role="status"></p>
      <ul id="search-results"></ul>
    </div>"""


def text_html(paragraphs, prose):
    escaped = [escape(text) for text in paragraphs]
    if prose:
        return "".join(f"<p>{paragraph}</p>" for paragraph in escaped)
    return "<p>" + "<br />\n".join(escaped) + "</p>"


def section_html(section, lang, prose):
    anchor = section["id"]
    title = escape(section["title"][lang])
    body = text_html(section["text"][lang], prose)
    return f'<div id="{anchor}"><h2>{title}</h2>{body}</div>'


def web_work(work, lang, *, portable_titles=None):
    standalone = portable_titles is not None
    slug = work["id"]
    filename = f"{slug}-{lang}"
    title = escape(work["title"][lang])
    prose = work.get("layout") == "prose"
    codes = [code for code in LANGUAGES if any(section["text"].get(code) for section in work["sections"])]
    language_links = []
    for code in codes:
        targets = " ".join(s["id"] for s in work["sections"] if s["text"].get(code))
        destination = f"?dielo={slug}&amp;jazyk={code}" if standalone else f"{slug}-{code}.html"
        language_links.append(
            f'<a data-passages="{targets}" data-code="{code}" href="{destination}"'
            f' data-title="{escape(work["title"][code])}" data-author="{escape(work["author"][code])}"'
            f' data-edition="{escape(work["edition"][code])}"'
            f'{" aria-current=page" if code == lang else ""}>{LANGUAGES[code]}</a>'
        )
    entries = []
    for group, chunk in groupby(work["sections"], key=lambda s: s.get("group")):
        chunk = list(chunk)
        links = "".join(
            f'<li data-entry="{s["id"]}"{"" if s["text"].get(lang) else " hidden"}>'
            f'<a href="#{s["id"]}">{escape(s["title"].get(lang) or next(iter(s["title"].values())))}</a></li>'
            for s in chunk
        )
        if group:
            labels = chunk[0]["group_title"]
            group_title = escape(labels.get(lang) or next(iter(labels.values())))
            hidden = "" if any(s["text"].get(lang) for s in chunk) else " hidden"
            links = f'<li data-toc-group{hidden}><details><summary>{group_title}</summary><ol>{links}</ol></details></li>'
        entries.append(links)
    content = []
    for s in work["sections"]:
        visible = bool(s["text"].get(lang))
        heading = s["title"].get(lang) or next(iter(s["title"].values()))
        translations = []
        for code in codes:
            translation_title = escape(s["title"].get(code) or heading)
            paragraphs = s["text"].get(code, [])
            body_html = text_html(paragraphs, prose) if paragraphs else '<p class="muted" lang="sk">Text v tomto jazyku chýba.</p>'
            translations.append(
                f'<div class="translation" lang="{code}" data-code="{code}" data-heading="{translation_title}"'
                f' data-available="{str(bool(paragraphs)).lower()}"{"" if code == lang else " hidden"}>'
                f'<h3 class="translation-label" lang="sk">{LANGUAGES[code]}</h3>{body_html}</div>'
            )
        content.append(
            f'<section id="{s["id"]}"{"" if visible else " hidden"}><h2 lang="{lang}">{escape(heading)}</h2>'
            f'<div class="translations">{"".join(translations)}</div></section>'
        )
    downloads = []
    for code in codes if standalone else [lang]:
        for fmt, mime in (("pdf", "application/pdf"), ("epub", "application/epub+zip")):
            name = f"{slug}-{code}.{fmt}"
            path = f"output/{fmt}/{name}"
            if standalone:
                payload = b64encode((DOCS / path).read_bytes()).decode("ascii")
                path = f"data:{mime};base64,{payload}"
            downloads.append(
                f'<a href="{path}" data-download-lang="{code}" download="{name}"'
                f'{"" if code == lang else " hidden"}>{fmt.upper()}</a>'
            )
    comparison_options = "\n".join(
        f'<label><input type="checkbox" name="language" value="{code}"> {LANGUAGES[code]}</label>' for code in codes
    )
    number_of_sections = sum(bool(s["text"].get(lang)) for s in work["sections"])
    related = ""
    reference_edition = ""
    if work.get("related"):
        related_label = escape(work.get("related_label", "Úryvok na Cormier OP"))
        related = f'<a href="{escape(work["related"])}">{related_label}</a>'
        if work.get("related_label"):
            reference_edition, related = f'<p class="reference-edition">{related}</p>', ""
    offline_navigation = ""
    if standalone:
        items = "".join(
            f'<a href="?dielo={work_id}"{(" aria-current=page" if work_id == slug else "")}>{escape(label)}</a>'
            for work_id, label in portable_titles.items()
        )
        offline_navigation = f'<nav class="offline-works" aria-label="Diela v offline knižnici">{items}</nav>'
    body = f"""
    {offline_navigation}
    {search_markup(slug)}
    <header class="work-header">
      <h1 lang="{lang}">{title}</h1>
      <p class="author" lang="{lang}">{escape(work["author"][lang])}</p>
      <p class="edition" lang="{lang}">{escape(work["edition"][lang])}</p>
      <div class="actions">
        <nav class="languages" aria-label="Jazyk textu">{"".join(language_links)}</nav>
        <div class="downloads" aria-label="Stiahnuť text">{"".join(downloads)}</div>
      </div>
      {reference_edition}
    </header>
    <div class="layout">
      <details id="obsah" class="contents" open>
        <summary>Obsah</summary>
        <nav aria-label="Obsah diela"><ol>{"".join(entries)}</ol></nav>
      </details>
      <article id="reading" class="{"prose" if prose else "verse"}">{"".join(content)}</article>
    </div>
    <footer class="sources"><a href="{escape(work["source"])}">Latinský prameň</a>
      {related}</footer>
    <nav class="pager" aria-label="Listovanie" hidden>
      <button type="button" data-page="-1">Späť</button>
      <a id="reading-position" href="#obsah" aria-label="Otvoriť obsah">1 / {number_of_sections}</a>
      <button type="button" data-page="1">Ďalej</button>
    </nav>
    <button type="button" class="back-to-top" hidden>Na začiatok</button>
    <dialog id="porovnanie" aria-labelledby="compare-title">
      <div class="dialog-heading"><h2 id="compare-title">Porovnať jazyky</h2>
      <form method="dialog"><button>Zavrieť</button></form></div>
      <form id="compare-form">
        <fieldset><legend>Vyberte dva alebo tri jazyky</legend>{comparison_options}</fieldset>
        <p id="compare-status" role="status" class="muted"></p>
        <div class="dialog-actions">
          <button class="primary" type="submit">Zobraziť porovnanie</button>
          <button id="single-language" type="button" hidden>Jeden jazyk</button>
        </div>
      </form>
    </dialog>
    """
    if standalone:
        return body
    (DOCS / f"{filename}.html").write_text(
        html_document(work["title"][lang], lang, body, work=slug), encoding="utf-8"
    )


def epub_work(work, lang, sections, path):
    title = escape(work["title"][lang])
    edition = escape(work["edition"][lang])
    author = escape(work["author"][lang])
    identifier = str(uuid5(NAMESPACE_URL, f"https://mstaskovan.github.io/StThomasAquinas/{work['id']}/{lang}/epub2"))
    documents = []
    entries = []
    ncx_points = []
    point_number = 0
    has_nested_contents = False

    def toc_entry(target, label):
        return f'<a href="{target}">{escape(label)}</a>'

    def ncx_entry(target, label, children=()):
        nonlocal point_number
        point_number += 1
        number = point_number
        nested_points = "".join(ncx_entry(child_target, child_label) for child_target, child_label in children)
        return (f'<navPoint id="point-{number}" playOrder="{number}"><navLabel><text>{escape(label)}</text></navLabel>'
                f'<content src="{target}"/>{nested_points}</navPoint>')

    for index, (group, chunk) in enumerate(groupby(sections, key=lambda s: s.get("group")), 1):
        chunk = list(chunk)
        filename = "text.xhtml" if index == 1 else f"text-{index:03}.xhtml"
        documents.append((filename, chunk))
        links = [(f'{filename}#{s["id"]}', s["title"][lang]) for s in chunk]
        if group:
            first = chunk[0]
            target, _ = links[0]
            label = first["group_title"].get(lang, first["title"][lang]) if first["id"] == group else first["title"][lang]
            children = links[1:]
            entry = toc_entry(target, label)
            if children:
                has_nested_contents = True
                entry += '<ol>' + "".join(f'<li>{toc_entry(*child)}</li>' for child in children) + '</ol>'
            entries.append(f'<li>{entry}</li>')
            ncx_points.append(ncx_entry(target, label, children))
        else:
            entries.extend(f'<li>{toc_entry(target, label)}</li>' for target, label in links)
            ncx_points.extend(ncx_entry(target, label) for target, label in links)
    manifest = "\n".join(f'<item id="text-{i}" href="{name}" media-type="application/xhtml+xml"/>'
                         for i, (name, _) in enumerate(documents, 1))
    spine = "\n".join(f'<itemref idref="text-{i}"/>' for i in range(1, len(documents) + 1))
    prefix = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
              '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
              f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">')
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as book:
        book.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        book.writestr("META-INF/container.xml", """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")
        book.writestr("content.opf", f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="publication">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="publication" opf:scheme="UUID">{identifier}</dc:identifier>
    <dc:title>{title}</dc:title><dc:language>{lang}</dc:language><dc:creator opf:role="aut">{author}</dc:creator>
    <dc:source>{escape(work["source"])}</dc:source>
    <dc:date>{TIMESTAMP[:10]}</dc:date>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {manifest}
  </manifest>
  <spine toc="ncx"><itemref idref="nav"/>{spine}</spine>
  <guide><reference type="toc" title="{CONTENTS[lang]}" href="nav.xhtml#toc"/></guide>
</package>""")
        book.writestr("toc.ncx", f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="{lang}">
  <head><meta name="dtb:uid" content="{identifier}"/><meta name="dtb:depth" content="{2 if has_nested_contents else 1}"/>
    <meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>
  <docTitle><text>{title}</text></docTitle>
  <navMap>{"".join(ncx_points)}</navMap>
</ncx>""")
        book.writestr("nav.xhtml", f"""<?xml version="1.0" encoding="UTF-8"?>
{prefix}<head><title>{CONTENTS[lang]}</title></head>
<body><div id="toc"><h1>{CONTENTS[lang]}</h1><ol>{"".join(entries)}</ol></div></body></html>""")
        for index, (filename, chunk) in enumerate(documents):
            body = "\n".join(section_html(s, lang, work.get("layout") == "prose") for s in chunk)
            heading = f"<h1>{title}</h1><p>{edition}</p>" if index == 0 else ""
            book.writestr(filename, f"""<?xml version="1.0" encoding="UTF-8"?>
{prefix}<head><title>{title}</title></head><body>
{heading}{body}
<p><a href="nav.xhtml#toc">{CONTENTS[lang]}</a></p>
</body></html>""")


def pdf_work(work, lang, sections, path):
    ink = HexColor("#231e18")
    rust = HexColor("#903f2d")
    title = work["title"][lang]
    pdf = SimpleDocTemplate(
        str(path), pagesize=(148 * mm, 210 * mm), title=title,
        author=work["author"][lang], lang=lang,
        leftMargin=19 * mm, rightMargin=17 * mm, topMargin=15 * mm, bottomMargin=15 * mm
    )
    book_title = ParagraphStyle("Title", fontName="BookBold", fontSize=23, leading=28, spaceAfter=12, textColor=ink)
    heading = ParagraphStyle("Heading", fontName="BookBold", fontSize=12, leading=14, spaceAfter=4, textColor=ink)
    body = ParagraphStyle("Body", fontName="Book", fontSize=11, leading=13, spaceAfter=7, textColor=ink)
    link = ParagraphStyle("Link", parent=body, spaceAfter=8, textColor=rust)
    story = [
        Paragraph(escape(title), book_title),
        Paragraph(escape(work["author"][lang]), body),
        Paragraph(escape(work["edition"][lang]), body),
        Paragraph(f'<a name="obsah"/>{CONTENTS[lang]}', heading),
    ]
    question_bookmarks = {}
    for group, chunk in groupby(sections, key=lambda s: s.get("group")):
        first = next(chunk)
        if group:
            label = first["group_title"].get(lang, first["title"][lang])
            question_bookmarks[first["id"]] = label
            story.append(Paragraph(f'<link href="#{first["id"]}">{escape(label)}</link>', link))
        else:
            for s in [first, *chunk]:
                story.append(Paragraph(f'<link href="#{s["id"]}">{escape(s["title"][lang])}</link>', link))
    source_label = escape(work.get("source_label", "Corpus Thomisticum"))
    story.append(Paragraph(f'<link href="{escape(work["source"])}">{source_label}</link>', link))
    story.append(PageBreak())
    for s in sections:
        name = s["id"]
        section_title = s["title"][lang]
        question_anchor = f'<a name="outline-{name}"/>' if name in question_bookmarks and name != s.get("group") else ""
        first = Paragraph(f'{question_anchor}<a name="{name}"/>{escape(section_title)}', heading)
        first.bookmark = (name, section_title, s.get("group"))
        texts = [escape(text) for text in s["text"][lang]]
        if work.get("layout") == "prose":
            first.keepWithNext = True
            story.append(first)
            story.extend(Paragraph(text, body) for text in texts)
        else:
            story.append(KeepTogether([first, Paragraph("<br/>".join(texts), body)]))
    story.append(Paragraph(f'<link href="#obsah">{CONTENTS[lang]}</link>', link))

    def page_number(canvas, document):
        canvas.setFont("Book", 9)
        canvas.setFillColor(rust)
        canvas.drawRightString(131 * mm, 11 * mm, str(document.page))

    def after_flowable(flowable):
        if hasattr(flowable, "bookmark"):
            name, label, group = flowable.bookmark
            if name in question_bookmarks:
                question_destination = name if name == group else f"outline-{name}"
                pdf.canv.addOutlineEntry(question_bookmarks[name], question_destination, closed=True)
            if name != group:
                pdf.canv.addOutlineEntry(label, name, level=1 if group else 0)

    pdf.afterFlowable = after_flowable
    pdf.build(story, onFirstPage=page_number, onLaterPages=page_number)


def build():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--font-dir", type=Path, default=Path("C:/Windows/Fonts"))
    parser.add_argument("--web-only", action="store_true", help="Keep the existing PDF and EPUB files.")
    args = parser.parse_args()
    if not args.web_only:
        pdfmetrics.registerFont(TTFont("Book", str(args.font_dir / "georgia.ttf")))
        pdfmetrics.registerFont(TTFont("BookBold", str(args.font_dir / "georgiab.ttf")))
    for fmt in ("pdf", "epub"):
        (DOCS / "output" / fmt).mkdir(parents=True, exist_ok=True)
    catalog_items = []
    search_index = []
    portable_books = {}
    for work_file in sorted((ROOT / "texty").glob("*.json")):
        work = loads(work_file.read_text(encoding="utf-8"))
        slug = valid_id(work["id"])
        ids = [valid_id(s["id"]) for s in work["sections"]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate anchors in {slug}")
        available_languages = []
        for lang in LANGUAGES:
            sections = [s for s in work["sections"] if s["text"].get(lang)]
            if not sections:
                continue
            available_languages.append(lang)
            name = f"{slug}-{lang}"
            web_work(work, lang)
            if not args.web_only:
                pdf_work(work, lang, sections, DOCS / "output" / "pdf" / f"{name}.pdf")
                epub_work(work, lang, sections, DOCS / "output" / "epub" / f"{name}.epub")
            search_index.extend({
                "title": work["title"][lang],
                "section": section["title"][lang],
                "text": " ".join(section["text"][lang]),
                "language": LANGUAGES[lang],
                "work": slug,
                "code": lang,
                "href": f"{name}.html#{section['id']}",
            } for section in sections)
        if not available_languages:
            continue
        first_lang = work.get("default_language", available_languages[0])
        if work.get("portable", True):
            portable_books[slug] = (work, first_lang)
        latin = work["title"].get("la")
        catalog_language = "sk" if work["title"].get("sk") else first_lang
        subtitle = f'<span lang="la">{escape(latin)}</span>' if latin and catalog_language != "la" else ""
        catalog_items.append(
            f'<li><a href="{slug}-{first_lang}.html" lang="{catalog_language}">'
            f'{escape(work["title"][catalog_language])}</a>{subtitle}</li>'
        )
    index_json = dumps(search_index, ensure_ascii=False).replace("<", "\\u003c")
    (DOCS / "search-index.js").write_text(
        f"const searchIndex = {index_json};\n",
        encoding="utf-8",
    )
    works = "\n".join(catalog_items)
    (DOCS / "index.html").write_text(
        html_document("Knižnica", "sk", f"""
        <header class="work-header">
          <div class="edition">Pracovné vydanie</div>
          <h1>Knižnica Tomáša Akvinského</h1>
          <p>Latinské pramene, české a slovenské preklady.</p>
        </header>
        {search_markup()}
        <section class="catalog" aria-labelledby="catalog-title">
          <h2 id="catalog-title">Dostupné texty</h2>
          <ul>{works}</ul>
        </section>"""),
        encoding="utf-8",
    )
    if portable_books:
        main_slug = "verbum-supernum" if "verbum-supernum" in portable_books else next(iter(portable_books))
        portable_titles = {slug: work["title"][lang] for slug, (work, lang) in portable_books.items()}
        views = {slug: web_work(work, lang, portable_titles=portable_titles) for slug, (work, lang) in portable_books.items()}
        body = views.pop(main_slug)
        contents = html_document(portable_titles[main_slug], "sk", body, work=main_slug, portable_views=views,
                                 portable_index=[item for item in search_index if item["work"] in portable_books])
        (ROOT / "citacka.html").write_text(contents, encoding="utf-8")


if __name__ == "__main__":
    build()
