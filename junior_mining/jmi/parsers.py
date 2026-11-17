"""Document parsers: bytes in, pages/tables with exact locations out.

Each parser is an adapter around a library that may be absent. If it is, the
parser reports the gap ("dependency unavailable") — it never returns invented
text. Coordinates come only from the PDF text layer (pdfplumber word boxes);
none are estimated. Pages without a text layer are reported as unreadable:
no OCR engine is installed in this environment.

Document content is untrusted data. Nothing here interprets instructions in a
document; text is stored and searched, never executed or obeyed.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

PARSER_VERSION = "2026-11-17.1"
MIN_TEXT_CHARS = 20


@dataclass
class ParsedPage:
    page_no: int
    text: str
    readable: bool
    label: str = ""


@dataclass
class ParsedTable:
    page_no: int
    table_index: int
    rows: list
    title: str = ""
    footnotes: list = field(default_factory=list)
    cell_refs: list | None = None   # spreadsheet A1 refs parallel to rows


@dataclass
class ParsedDoc:
    parser: str
    pages: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def unreadable_pages(self) -> list[int]:
        return [p.page_no for p in self.pages if not p.readable]

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)


class ParseError(Exception):
    pass


_FOOTNOTE_LINE = re.compile(r"^\s*(?:\d{1,2}[.)]\s|[¹²³⁴⁵⁶⁷⁸⁹]\s?|notes?:|source:)", re.I)


def _clean(cell) -> str:
    if cell is None:
        return ""
    return re.sub(r"[ \t]+", " ", str(cell)).strip()


def detect_kind(filename: str, data: bytes) -> str:
    name = filename.lower()
    if data[:5] == b"%PDF-" or name.endswith(".pdf"):
        return "pdf"
    if data[:2] == b"PK" and name.endswith((".xlsx", ".xlsm")):
        return "xlsx"
    if name.endswith(".csv"):
        return "csv"
    if name.endswith((".txt", ".md")):
        return "text"
    raise ParseError(f"unsupported file type: {filename}")


def parse(filename: str, data: bytes) -> ParsedDoc:
    kind = detect_kind(filename, data)
    return {"pdf": parse_pdf, "xlsx": parse_xlsx, "csv": parse_csv, "text": parse_text}[kind](data)


# ------------------------------------------------------------------ PDF
def parse_pdf(data: bytes) -> ParsedDoc:
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover - environment dependent
        raise ParseError("PDF parsing unavailable: pdfplumber is not installed")
    doc = ParsedDoc(parser=f"pdfplumber-{pdfplumber.__version__}")
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:
        raise ParseError(f"unreadable PDF: {type(exc).__name__}") from exc
    with pdf:
        tcount = 0
        for i, page in enumerate(pdf.pages, start=1):
            text = _page_text(page)
            readable = len(text.strip()) >= MIN_TEXT_CHARS
            doc.pages.append(ParsedPage(i, text, readable))
            if not readable:
                doc.warnings.append(f"page {i}: no usable text layer (scanned image?) — "
                                    "not OCR'd; requires human reading")
                continue
            found = sorted(page.find_tables(), key=lambda t: t.bbox[1])
            for k, t in enumerate(found):
                rows = [[_clean(c) for c in r] for r in t.extract()]
                if not rows or not any(any(c for c in r) for r in rows):
                    continue
                x0, top, x1, bottom = t.bbox
                title = ""
                if top > 2:
                    above = page.crop((0, max(0, top - 44), page.width, top)).extract_text_lines(strip=True) or []
                    # the caption is the run of lines directly above the table (wrapped captions included)
                    run = []
                    for ln in reversed(above):
                        if run and run[-1]["top"] - ln["bottom"] > max(4.0, 0.6 * (ln["bottom"] - ln["top"])):
                            break
                        run.append(ln)
                    title = " ".join(ln["text"] for ln in reversed(run)).strip()
                # footnotes: only the region between this table and the next one
                limit = found[k + 1].bbox[1] - 28 if k + 1 < len(found) else page.height
                below_text = page.crop((0, bottom, page.width, max(bottom + 1, limit))).extract_text() or ""
                notes = [ln.strip() for ln in below_text.splitlines() if _FOOTNOTE_LINE.match(ln)]
                doc.tables.append(ParsedTable(i, tcount, rows, title, notes))
                tcount += 1
    return doc


def _page_text(page) -> str:
    """Page text with paragraph breaks restored from vertical gaps.

    pdfplumber joins lines with single newlines; a blank line is inserted where
    the gap between consecutive lines is clearly larger than the page's usual
    line spacing. Offsets into this text are the offsets stored in locations.
    """
    try:
        lines = page.extract_text_lines(strip=True, return_chars=False)
    except Exception:
        return page.extract_text() or ""
    if not lines:
        return ""
    heights = sorted(ln["bottom"] - ln["top"] for ln in lines)
    h = heights[len(heights) // 2] if heights else 10.0
    out = [lines[0]["text"]]
    for a, b in zip(lines, lines[1:]):
        gap = b["top"] - a["bottom"]
        out.append(("\n\n" if gap > max(3.0, 0.5 * h) else "\n") + b["text"])
    return "".join(out)


def pdf_bbox(data: bytes, page_no: int, quote: str) -> tuple[list | None, str]:
    """Word-box coordinates of `quote` on a page, from the text layer only.

    Returns (bbox, note). bbox is None when the quote is absent, ambiguous
    (several matches) or the library is unavailable — never a guess.
    """
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover
        return None, "coordinates unavailable: pdfplumber not installed"
    q = re.sub(r"\s+", " ", quote).strip()
    if len(q) < 3:
        return None, "quote too short to locate"
    pattern = r"\s+".join(re.escape(w) for w in q.split(" "))
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if page_no < 1 or page_no > len(pdf.pages):
            return None, "page out of range"
        page = pdf.pages[page_no - 1]
        try:
            hits = page.search(pattern, regex=True, case=True)
        except Exception:
            return None, "text-layer search failed"
    if len(hits) == 1:
        h = hits[0]
        return [round(h["x0"], 2), round(h["top"], 2), round(h["x1"], 2), round(h["bottom"], 2)], \
            "from PDF text layer"
    if not hits:
        return None, "quote not found as contiguous text in the PDF text layer"
    return None, f"quote occurs {len(hits)} times on the page; no single highlight"


def render_page_png(data: bytes, page_no: int, scale: float = 1.5) -> bytes:
    """Page image for human checking (pypdfium2). Raises ParseError if unavailable."""
    try:
        import pypdfium2 as pdfium
    except ImportError:  # pragma: no cover
        raise ParseError("page images unavailable: pypdfium2 not installed")
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as exc:
        raise ParseError(f"page image unavailable: the stored file is not a readable PDF ({type(exc).__name__})")
    try:
        if page_no < 1 or page_no > len(pdf):
            raise ParseError("page out of range")
        img = pdf[page_no - 1].render(scale=scale).to_pil()
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    finally:
        pdf.close()


# ------------------------------------------------------------------ XLSX
def _a1(row: int, col: int) -> str:
    s, c = "", col
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return f"{s}{row}"


def parse_xlsx(data: bytes) -> ParsedDoc:
    try:
        import openpyxl
    except ImportError:  # pragma: no cover
        raise ParseError("spreadsheet parsing unavailable: openpyxl is not installed")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=False)
    except Exception as exc:
        raise ParseError(f"unreadable workbook: {type(exc).__name__}") from exc
    doc = ParsedDoc(parser=f"openpyxl-{openpyxl.__version__}")
    for i, ws in enumerate(wb.worksheets, start=1):
        merged = {}
        for rng in ws.merged_cells.ranges:
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    if (r, c) != (rng.min_row, rng.min_col):
                        merged[(r, c)] = _a1(rng.min_row, rng.min_col)
        rows, refs, text_lines = [], [], []
        for r in range(1, (ws.max_row or 0) + 1):
            row, ref = [], []
            for c in range(1, (ws.max_column or 0) + 1):
                v = ws.cell(row=r, column=c).value
                row.append(_clean(v))
                ref.append(_a1(r, c))
            if any(row):
                rows.append(row)
                refs.append(ref)
                text_lines.append(" | ".join(x for x in row if x))
        if merged:
            doc.warnings.append(f"sheet '{ws.title}': {len(merged)} merged cell(s); "
                                "values are read from the top-left cell only")
        text = "\n".join(text_lines)
        doc.pages.append(ParsedPage(i, text, bool(text.strip()), label=ws.title))
        if rows:
            notes = [ln for ln in text_lines if _FOOTNOTE_LINE.match(ln)]
            # a single filled cell in the first row (often merged) is the table title
            first = [c for c in rows[0] if c]
            title = first[0] if len(first) == 1 else ws.title
            doc.tables.append(ParsedTable(i, len(doc.tables), rows, title, notes, refs))
    return doc


# ------------------------------------------------------------------ CSV / text
def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ParseError("text is not valid UTF-8")


def parse_csv(data: bytes) -> ParsedDoc:
    text = _decode(data)
    rows = [[_clean(c) for c in r] for r in csv.reader(io.StringIO(text))]
    rows = [r for r in rows if any(r)]
    doc = ParsedDoc(parser="csv-stdlib")
    doc.pages.append(ParsedPage(1, text, bool(text.strip())))
    refs = [[_a1(ri + 1, ci + 1) for ci in range(len(r))] for ri, r in enumerate(rows)]
    doc.tables.append(ParsedTable(1, 0, rows, "", [], refs))
    return doc


def parse_text(data: bytes) -> ParsedDoc:
    text = _decode(data)
    doc = ParsedDoc(parser="text-stdlib")
    doc.pages.append(ParsedPage(1, text, bool(text.strip())))
    return doc
