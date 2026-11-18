"""The current season's rules: article references in a ruling, and the rulebooks they point to.

A 2026 ruling cites two books by article:
  - the FIA 2026 F1 Regulations, Section B [Sporting]: "Article B1.8.5", "Articles B8.2.2a read with B8.2.3";
  - Appendix L of the International Sporting Code: "Appendix L, Chapter IV, Article 2 d)".
Earlier seasons used other rulebooks with other numbering, so only 2026 rulings are linked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEASON = 2026
BOOKS = {
    "sporting": {
        "title": "FIA 2026 F1 Regulations – Section B [Sporting]",
        "short": "Sporting Regulations",
        "issue": "Issue 9, 1 October 2026",
        "url": "https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_09_-_2026-10-01.pdf",
        "file": "fia_2026_f1_regulations_-_section_b_sporting_-_iss_09_-_2026-10-01.pdf",
    },
    "appendix_l": {
        "title": "International Sporting Code, Appendix L – 2026",
        "short": "Appendix L",
        "issue": "Published 23 June 2026",
        "url": "https://www.fia.com/system/files/documents/appendix_l_2026_publie_le_24_juin_2026.pdf",
        "file": "appendix_l_2026_publie_le_24_juin_2026.pdf",
    },
}


@dataclass(frozen=True)
class Ref:
    start: int  # span in the text that was searched
    end: int
    book: str  # key of BOOKS
    article: str  # "B1.8.5" (letter suffix dropped: "B8.2.2a" cites B8.2.2), or "IV.2" for Appendix L
    point: str = ""  # the sub-point the ruling names, "a" or "d", for display only


# A Section B article number; the B prefix keeps it apart from the Sporting Code's own "Article 12.2.1.i".
_SPORTING = re.compile(r"\bB(\d+(?:\.\d+)+)([a-z])?(?!\w)")
_APPENDIX_L = re.compile(
    r"Appendix\s+L\s*,?\s*Chapter\s+([IVX]+)\s*,?\s*Articles?\s+(\d+)(?:\s*\.?\s*([a-z])\)?)?(?![\w])", re.I)


def references(text: str) -> list[Ref]:
    """Every Section B and Appendix L article cited in the text, in order."""
    refs = [Ref(m.start(), m.end(), "sporting", f"B{m.group(1)}", m.group(2) or "") for m in _SPORTING.finditer(text)]
    refs += [Ref(m.start(), m.end(), "appendix_l", f"{m.group(1).upper()}.{m.group(2)}", (m.group(3) or "").lower())
             for m in _APPENDIX_L.finditer(text)]
    return sorted(refs, key=lambda r: r.start)


# ---------------------------------------------------------------- splitting the rulebooks into articles
#
# Both PDFs have a text layer. PyMuPDF's text blocks are paragraphs, and a numbered article starts a
# block of its own, so the books are split block by block. Positions are PDF points (A4: 595 x 842).

Block = tuple[float, float, str]  # x0, y0, text


@dataclass
class Article:
    number: str  # "B1", "B1.6", "B1.6.3"; "IV.2" for Appendix L
    title: str
    page: int  # 1-based page in the PDF, for a #page= link
    paragraphs: list[tuple[int, str]]  # (indent level, text)


def _flat(text: str) -> str:
    return " ".join(text.split())


_TOP = re.compile(r"^ARTICLE (B\d+)\s*:\s*(.+)$")
_NUMBER = re.compile(r"^(B\d+(?:\.\d+)+)$")
_MARKER = re.compile(r"^(?:[a-z]|[ivx]+)\.$")
_SKIP = re.compile(r"^(?:Advisory Committee|Governance)\s*:")


def _add(article: Article, level: int, text: str) -> None:
    """A paragraph, or the rest of the last one when a page break split it (it starts in lower case)."""
    if article.paragraphs and text[:1].islower() and not _MARKER.match(text.split(" ", 1)[0]) and not _L_POINT.match(text):
        last_level, last = article.paragraphs[-1]
        article.paragraphs[-1] = (last_level, f"{last} {text}")
    else:
        article.paragraphs.append((level, text))


def _key(number: str) -> list[int]:
    return [int(x) for x in number.lstrip("B").split(".")]


def split_sporting(pages: list[list[Block]]) -> list[Article]:
    """Section B, from each page's blocks. Running headers and footers sit above y=60 and below y=770."""
    articles: list[Article] = []
    for page_no, blocks in enumerate(pages, 1):
        for x0, y0, raw in blocks:
            if not 60 < y0 < 770:
                continue
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if not lines:
                continue
            if articles and re.match(r"^APPENDIX B\d+\s*:", _flat(raw)):
                return articles  # definitions and forms follow the last article
            top = _TOP.match(_flat(raw))
            if top:
                if re.search(r"\s\d+$", top.group(2)):  # in the contents, the title ends in a page number
                    continue
                tops = [a for a in articles if "." not in a.number]
                if tops and _key(top.group(1)) <= _key(tops[-1].number):
                    return articles  # the extracts repeated at the end of the issue ("…/…")
                articles.append(Article(top.group(1), top.group(2).strip().title(), page_no, []))
                continue
            if not articles or _SKIP.match(lines[0]):
                continue  # the contents pages come before ARTICLE B1
            number = _NUMBER.match(lines[0])
            if number:
                rest = lines[1:]
                title = rest[0] if len(rest) == 1 and len(rest[0]) < 90 and not rest[0].endswith((".", ",", ";", ":")) else ""
                body = [] if title or not rest else [(0, _flat(" ".join(rest)))]
                if any(a.number == number.group(1) for a in articles):
                    # the issue numbers two articles alike (B1.5.11); keep one anchor, fold the second in
                    articles[-1].paragraphs.append((0, f"{number.group(1)} {title}".strip()))
                    articles[-1].paragraphs.extend(body)
                    continue
                articles.append(Article(number.group(1), title, page_no, body))
                continue
            level = 0 if x0 < 70 else 1 if x0 < 110 else 2
            if _MARKER.match(lines[0]) and len(lines) > 1:
                text = f"{lines[0]} {_flat(' '.join(lines[1:]))}"
            else:
                text = _flat(" ".join(lines))
            _add(articles[-1], level, text)
    return articles


_L_ARTICLE = re.compile(r"^(\d+)\.\s*(.+)$")
_L_POINT = re.compile(r"(?:(?<=\s)|^)([a-z])\)\s")


def split_appendix_l_chapter_iv(pages: list[tuple[int, list[Block]]], midline: float) -> list[Article]:
    """Chapter IV of Appendix L, English column only (x0 at or right of the midline), from
    'CHAPTER IV' to 'CHAPTER V'. pages: (1-based page number, blocks)."""
    articles: list[Article] = []
    inside = False
    for page_no, blocks in pages:
        for x0, y0, raw in sorted((b for b in blocks if b[0] >= midline - 5 and b[1] > 45), key=lambda b: b[1]):
            text = _flat(raw)
            if text.startswith("CHAPTER IV"):
                inside = True
                continue
            if text.startswith("CHAPTER V") or not inside or not text or text.startswith("Page "):
                if inside and text.startswith("CHAPTER V"):
                    return articles
                continue
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            alone = re.match(r"^(\d+)\.$", lines[0])
            head = _L_ARTICLE.match(lines[0])
            if alone and len(lines) > 1:  # "1." and its title on separate lines
                articles.append(Article(f"IV.{alone.group(1)}", _flat(lines[1]), page_no, []))
                text = _flat(" ".join(lines[2:]))
            elif head and len(head.group(2)) < 70:
                articles.append(Article(f"IV.{head.group(1)}", _flat(head.group(2)), page_no, []))
                text = _flat(" ".join(lines[1:]))
            if not text:
                continue
            if not articles:
                continue
            # points run together in one block: "a) ... b) ..."; give each its own paragraph
            starts = [m.start() for m in _L_POINT.finditer(text)]
            pieces = [text[a:b].strip() for a, b in zip([0, *starts], [*starts, len(text)]) if text[a:b].strip()]
            for piece in pieces:
                _add(articles[-1], 1 if _L_POINT.match(piece) else 0, piece)
    return articles


def read_pdf(path) -> list[list[Block]]:
    import pymupdf

    with pymupdf.open(path) as doc:
        return [[(b[0], b[1], b[4]) for b in page.get_text("blocks") if b[6] == 0] for page in doc]


def chapter_iv_pages(pages: list[list[Block]]) -> list[tuple[int, list[Block]]]:
    """The pages of Appendix L from the one where Chapter IV starts to the one where Chapter V starts."""
    marks = [i for i, blocks in enumerate(pages) for b in blocks if re.match(r"CHAPTER\s+IV\b", _flat(b[2]))]
    first = next((i for i in marks if i > 5), None)  # page 1 is the contents
    if first is None:
        return []
    return [(i + 1, pages[i]) for i in range(first, min(first + 8, len(pages)))]


def split(book: str, pages: list[list[Block]], width: float) -> list[Article]:
    if book == "sporting":
        return split_sporting(pages)
    return split_appendix_l_chapter_iv(chapter_iv_pages(pages), width / 2)


def store(con, book: str, articles: list[Article]) -> None:
    import json

    con.execute("DELETE FROM articles WHERE book = ?", (book,))
    con.executemany(
        "INSERT INTO articles (book, number, title, page, paragraphs) VALUES (?, ?, ?, ?, ?)",
        [(book, a.number, a.title, a.page, json.dumps(a.paragraphs, ensure_ascii=False)) for a in articles],
    )
    con.commit()


def load_articles(con) -> dict[str, list[Article]]:
    import json

    out: dict[str, list[Article]] = {}
    for r in con.execute("SELECT book, number, title, page, paragraphs FROM articles ORDER BY rowid"):
        out.setdefault(r["book"], []).append(Article(r["number"], r["title"], r["page"],
                                                     [tuple(p) for p in json.loads(r["paragraphs"])]))
    return out
