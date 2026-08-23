#!/usr/bin/env python3
"""Render reviewable contact sheets for every changed page and adjacent control."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import fitz
from PIL import Image, ImageDraw, ImageFont


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
READER = ROOT / "release_v020" / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
DELTA = ROOT / "release_v020" / "evidence" / "cyrillic-rendered-page-delta-v019-to-v020.json"
OUTPUT_ROOT = ROOT / "tmp" / "pdfs" / "isv_release_v020" / "visual" / "linked-reader"
MANIFEST = ROOT / "release_v020" / "evidence" / "linked-reader-visual-assets.json"
READER_PIN = (6_885_841, "7DCB4C852BF3CCE5928921E13F73FA34E80EA4FEB2A82F967FEE29657150AE20")
DELTA_PIN = (65_031, "51858018D2BF796F0620B216BF6C932C9E1D839402A6031EC12334E57B477A55")
FRONT_AND_BOUNDARIES = (1, 2, 3, 4, 5, 6, 570, 571, 572, 1159)


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


def authenticate(path: Path, pin: tuple[int, str], label: str) -> None:
    actual = (path.stat().st_size, sha256(path))
    if actual != pin:
        raise RuntimeError(f"{label} pin drift: {actual}")


def batches(values: list[int], size: int) -> Iterable[list[int]]:
    for offset in range(0, len(values), size):
        yield values[offset : offset + size]


def render_page(document: fitz.Document, page_number: int, cell_width: int) -> Image.Image:
    page = document[page_number - 1]
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25), colorspace=fitz.csRGB, alpha=False, annots=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    cell_height = round(image.height * cell_width / image.width)
    return image.resize((cell_width, cell_height), Image.Resampling.LANCZOS)


def make_contact(
    document: fitz.Document,
    pages: list[int],
    output: Path,
    *,
    columns: int,
    cell_width: int,
    title: str,
) -> dict[str, object]:
    if not pages:
        raise ValueError("empty contact-sheet page set")
    label_height = 34
    title_height = 44
    margin = 12
    rendered = [render_page(document, page, cell_width) for page in pages]
    cell_height = max(image.height for image in rendered) + label_height
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
    font = ImageFont.load_default(size=18)
    draw.text((margin, 10), title, fill="#111111", font=font)
    for index, (page, image) in enumerate(zip(pages, rendered)):
        row, column = divmod(index, columns)
        x = margin + column * (cell_width + margin)
        y = title_height + margin + row * (cell_height + margin)
        canvas.paste(image, (x, y + label_height))
        draw.text((x, y + 5), f"linked-reader page {page}", fill="#111111", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    with Image.open(output) as check:
        check.verify()
    return {
        **record(output),
        "represented_pages": pages,
        "dimensions": [canvas.width, canvas.height],
    }


def main() -> int:
    authenticate(READER, READER_PIN, "linked reader")
    authenticate(DELTA, DELTA_PIN, "rendered-page delta receipt")
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    result = delta["result"]
    changed = [int(page) for page in result["changed_linked_reader_pages"]]
    controls = [int(page) for page in result["adjacent_unchanged_control_linked_reader_pages"]]
    if len(changed) != 86 or len(controls) != 103:
        raise RuntimeError(f"review-set cardinality drift: {len(changed)}, {len(controls)}")
    document = fitz.open(READER)
    if len(document) != 1_159:
        raise RuntimeError(f"linked-reader page count drift: {len(document)}")

    rows: list[dict[str, object]] = []
    rows.append(
        make_contact(
            document,
            list(FRONT_AND_BOUNDARIES),
            OUTPUT_ROOT / "front-and-boundaries.png",
            columns=2,
            cell_width=560,
            title="NOETHER-ISV-v020: new front matter and reader boundaries",
        )
    )
    for index, page_batch in enumerate(batches(changed, 6), 1):
        rows.append(
            make_contact(
                document,
                page_batch,
                OUTPUT_ROOT / f"changed-pages-{index:02d}.png",
                columns=3,
                cell_width=500,
                title=f"NOETHER-ISV-v020: changed Cyrillic pages {index:02d}",
            )
        )
    for index, page_batch in enumerate(batches(controls, 12), 1):
        rows.append(
            make_contact(
                document,
                page_batch,
                OUTPUT_ROOT / f"adjacent-controls-{index:02d}.png",
                columns=4,
                cell_width=350,
                title=f"NOETHER-ISV-v020: adjacent unchanged controls {index:02d}",
            )
        )

    manifest = {
        "schema": "noether-interslavic-linked-reader-visual-assets/1.0",
        "release_id": "NOETHER-ISV-v020",
        "inputs": {
            "linked_reader": {**record(READER), "pages": len(document)},
            "rendered_delta": record(DELTA),
        },
        "coverage": {
            "changed_pages": changed,
            "changed_page_count": len(changed),
            "adjacent_unchanged_control_pages": controls,
            "adjacent_unchanged_control_page_count": len(controls),
            "front_and_boundaries": list(FRONT_AND_BOUNDARIES),
        },
        "render": {
            "engine": f"PyMuPDF {fitz.VersionBind}",
            "matrix": [1.25, 1.25],
            "colorspace": "RGB",
            "contact_sheet_format": "PNG",
        },
        "contact_sheets": rows,
        "status": "ASSETS_RENDERED_AWAITING_MANUAL_REVIEW",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if json.loads(MANIFEST.read_text(encoding="utf-8")) != manifest:
        raise RuntimeError("visual asset manifest readback mismatch")
    print(json.dumps({
        "status": "PASS",
        "contact_sheets": len(rows),
        "changed_pages": len(changed),
        "controls": len(controls),
        "manifest": record(MANIFEST),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
