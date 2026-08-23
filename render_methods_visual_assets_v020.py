#!/usr/bin/env python3
"""Render every v020 methods-paper page into reviewable contact sheets."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PDF = ROOT / "release_v020" / "evidence" / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf"
OUTPUT_ROOT = ROOT / "tmp" / "pdfs" / "isv_release_v020" / "visual" / "methods"
MANIFEST = ROOT / "release_v020" / "evidence" / "methods-visual-assets.json"
PDF_PIN = (178_720, "DA45E0B1C4D40B6582C312C578812E709C5E42C6FCEE663FF0599DCAFC39AED7")
EXPECTED_PAGES = 13


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, object]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def render_page(document: fitz.Document, page_number: int, width: int) -> Image.Image:
    pixmap = document[page_number - 1].get_pixmap(
        matrix=fitz.Matrix(1.5, 1.5), colorspace=fitz.csRGB, alpha=False, annots=False
    )
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_contact(document: fitz.Document, pages: list[int], path: Path) -> dict[str, object]:
    columns = 2
    cell_width = 700
    label_height = 38
    title_height = 46
    margin = 14
    images = [render_page(document, page, cell_width) for page in pages]
    cell_height = max(image.height for image in images) + label_height
    rows = math.ceil(len(pages) / columns)
    canvas = Image.new(
        "RGB",
        (
            margin + columns * (cell_width + margin),
            title_height + margin + rows * (cell_height + margin),
        ),
        "#D7DCE1",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=20)
    draw.text((margin, 10), "NOETHER-ISV-v020 methods paper - every page", fill="#111111", font=font)
    for index, (page_number, image) in enumerate(zip(pages, images)):
        row, column = divmod(index, columns)
        x = margin + column * (cell_width + margin)
        y = title_height + margin + row * (cell_height + margin)
        draw.text((x, y + 5), f"methods page {page_number}", fill="#111111", font=font)
        canvas.paste(image, (x, y + label_height))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", optimize=True)
    with Image.open(path) as check:
        check.verify()
    return {**record(path), "represented_pages": pages, "dimensions": [canvas.width, canvas.height]}


def main() -> int:
    actual = (PDF.stat().st_size, sha256(PDF))
    if actual != PDF_PIN:
        raise RuntimeError(f"methods PDF pin drift: {actual}")
    document = fitz.open(PDF)
    if len(document) != EXPECTED_PAGES:
        raise RuntimeError(f"methods page count drift: {len(document)}")
    contacts = []
    all_pages = list(range(1, EXPECTED_PAGES + 1))
    for index, offset in enumerate(range(0, EXPECTED_PAGES, 4), 1):
        pages = all_pages[offset : offset + 4]
        contacts.append(make_contact(document, pages, OUTPUT_ROOT / f"methods-pages-{index:02d}.png"))
    manifest = {
        "schema": "noether-interslavic-methods-visual-assets/1.0",
        "release_id": "NOETHER-ISV-v020",
        "input": {**record(PDF), "pages": len(document)},
        "coverage": {"all_pages": all_pages, "page_count": EXPECTED_PAGES},
        "render": {"engine": f"PyMuPDF {fitz.VersionBind}", "matrix": [1.5, 1.5], "colorspace": "RGB"},
        "contact_sheets": contacts,
        "status": "ASSETS_RENDERED_AWAITING_MANUAL_REVIEW",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if json.loads(MANIFEST.read_text(encoding="utf-8")) != manifest:
        raise RuntimeError("methods visual manifest readback mismatch")
    print(json.dumps({
        "status": "PASS",
        "pages": EXPECTED_PAGES,
        "contact_sheets": len(contacts),
        "manifest": record(MANIFEST),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
