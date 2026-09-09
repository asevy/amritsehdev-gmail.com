"""Source Archive - content-addressed document store. Nothing disappears.

Every primary document (annual report, registry extract, court judgment,
land record, filing) is stored by its sha256 under graph/archive/objects/
with extracted text alongside for search, and an append-only index. When
a document is attached to a Source, that source's record is updated with
preserved=True and the archive ref - which is what lets the claims built
on it pass the evidence-path invariant and become approvable.

Usage:
    from archive import Archive
    from store import Ledger
    led = Ledger("data"); arc = Archive(".")
    ref = arc.add("~/Downloads/wisynco-ar-2025.pdf",
                  source_id="S-2026-0005", ledger=led)
    arc.search("Mahfood")

Self-test: python3 archive.py
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import shutil
import subprocess
from typing import Optional

TEXT_EXTS = {".txt", ".md", ".html", ".htm", ".csv", ".json"}


class Archive:
    def __init__(self, graph_dir: str = "."):
        root = pathlib.Path(graph_dir) / "archive"
        self.objects = root / "objects"
        self.texts = root / "text"
        self.index_file = root / "index.jsonl"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.texts.mkdir(parents=True, exist_ok=True)
        self.index: list[dict] = []
        if self.index_file.exists():
            self.index = [json.loads(l) for l in
                          self.index_file.read_text().splitlines()
                          if l.strip()]

    def add(self, file_path: str, source_id: Optional[str] = None,
            ledger=None, description: str = "",
            added: str = "") -> str:
        src = pathlib.Path(file_path).expanduser()
        data = src.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        ref = f"sha256:{sha}"
        ext = src.suffix.lower()
        obj = self.objects / f"{sha}{ext}"
        if not obj.exists():
            shutil.copyfile(src, obj)
        self._extract_text(obj, sha, ext)
        rec = {"ref": ref, "filename": src.name, "bytes": len(data),
               "ext": ext, "source_id": source_id,
               "description": description, "added": added}
        self.index.append(rec)
        with self.index_file.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if ledger is not None and source_id is not None:
            s = ledger.sources.get(source_id)
            if s is None:
                raise ValueError(f"unknown source {source_id}")
            ledger.add_source(dataclasses.replace(
                s, preserved=True, archive_ref=ref))
        return ref

    def _extract_text(self, obj: pathlib.Path, sha: str, ext: str) -> None:
        out = self.texts / f"{sha}.txt"
        if out.exists():
            return
        if ext in TEXT_EXTS:
            out.write_text(obj.read_text(errors="replace"))
        elif ext == ".pdf":
            try:
                subprocess.run(["pdftotext", str(obj), str(out)],
                               check=True, capture_output=True)
            except (OSError, subprocess.CalledProcessError):
                out.write_text("")  # OCR/extraction pending
        else:
            out.write_text("")

    def search(self, term: str) -> list[dict]:
        term_l = term.lower()
        hits = []
        for rec in self.index:
            sha = rec["ref"].split(":", 1)[1]
            txt = self.texts / f"{sha}.txt"
            in_text = txt.exists() and term_l in txt.read_text(
                errors="replace").lower()
            in_meta = term_l in json.dumps(rec).lower()
            if in_text or in_meta:
                hits.append(rec)
        return hits

    def get_path(self, ref: str) -> Optional[pathlib.Path]:
        sha = ref.split(":", 1)[1]
        for p in self.objects.glob(f"{sha}*"):
            return p
        return None


if __name__ == "__main__":
    import tempfile
    from schema import Source
    from store import Ledger

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        led = Ledger(str(td / "data"))
        led.add_source(Source(id="S1", description="test filing", tier=1,
                              retrieval_date="2026-09-09",
                              passage="p.4", analyst="test"))
        doc = td / "filing.txt"
        doc.write_text("Register of members: Family Y Holdings 62,000")
        arc = Archive(str(td))
        ref = arc.add(str(doc), source_id="S1", ledger=led,
                      added="2026-09-09")
        assert ref.startswith("sha256:")
        assert led.sources["S1"].preserved
        assert led.sources["S1"].archive_ref == ref
        assert arc.search("Family Y")[0]["filename"] == "filing.txt"
        assert arc.get_path(ref).exists()
        # Same content added twice: same object, second index entry only.
        arc.add(str(doc), added="2026-09-09")
        assert len(list(arc.objects.iterdir())) == 1
        print("archive self-test: OK (content-addressed, indexed, "
              "searchable, ledger-linked)")
