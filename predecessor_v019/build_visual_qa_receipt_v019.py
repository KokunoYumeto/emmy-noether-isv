#!/usr/bin/env python3
"""Seal the final rendered-page and all-page raster QA receipt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import fitz
from PIL import Image


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v019"
READER = RELEASE / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
METHODS = RELEASE / "evidence" / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v019.pdf"
READER_PIN = (
    6_885_443,
    "E14B2C9336E94878370332913360ECC52935AE93A89701BC7A5AE22C0552C401",
)
METHODS_PIN = (
    148_036,
    "9F202AC7A94DFE0CD09633AB5CFFD0DD349608E9ABD89CE887EE1A24F0ABDA2F",
)
READER_RENDER_ROOT = ROOT / "tmp" / "pdfs" / "isv_release_v019" / "visual" / "linked-reader"
METHODS_RENDER_ROOT = ROOT / "tmp" / "pdfs" / "isv_release_v019" / "visual" / "methods"
READER_PAGES = (
    1, 2, 3, 4, 5, 6, 7, 25, 50, 100, 150, 200, 250, 300, 350, 400,
    450, 500, 550, 568, 569, 570, 571, 572, 573, 600, 650, 700, 750, 800,
    850, 900, 950, 1000, 1050, 1100, 1150, 1159,
)
CONTACTS = (
    (READER_RENDER_ROOT / "contact-front-boundaries.png", (1, 2, 3, 4, 5, 6, 7, 568, 569, 570, 571, 572, 573, 1159)),
    (READER_RENDER_ROOT / "contact-latin-samples.png", (25, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550)),
    (READER_RENDER_ROOT / "contact-cyrillic-samples.png", (600, 650, 700, 750, 800, 850, 900, 950, 1000, 1050, 1100, 1150)),
    (METHODS_RENDER_ROOT / "contact-methods.png", (1, 2, 3, 4, 5, 6)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    return {"path": path.resolve().relative_to(ROOT.resolve()).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}


def authenticate(path: Path, pin: tuple[int, str], label: str) -> None:
    actual = (path.stat().st_size, sha256(path))
    if actual != pin:
        raise RuntimeError(f"{label} pin drift: {actual}")


def raster_census(path: Path, expected_pages: int) -> dict[str, Any]:
    document = fitz.open(path)
    if len(document) != expected_pages:
        raise RuntimeError(f"page-count drift for {path}: {len(document)}")
    rows = []
    for page_number, page in enumerate(document, 1):
        pixmap = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5), colorspace=fitz.csGRAY, alpha=False)
        width, height = pixmap.width, pixmap.height
        samples = pixmap.samples
        dark = [index for index, value in enumerate(samples) if value < 245]
        if not dark:
            bbox = None
        else:
            xs = [index % width for index in dark]
            ys = [index // width for index in dark]
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        rows.append(
            {
                "page": page_number,
                "width": width,
                "height": height,
                "ink_pixels": len(dark),
                "ink_fraction": len(dark) / (width * height),
                "ink_bbox": bbox,
            }
        )
    blank = [row["page"] for row in rows if row["ink_pixels"] < 20]
    high_coverage = [row["page"] for row in rows if row["ink_fraction"] > 0.50]
    if blank or high_coverage:
        raise RuntimeError(f"raster anomaly {path}: blank={blank}, high_coverage={high_coverage}")
    canonical = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    minimum = min(rows, key=lambda row: row["ink_pixels"])
    maximum = max(rows, key=lambda row: row["ink_fraction"])
    return {
        "pages": len(rows),
        "render_scale": 0.5,
        "colorspace": "grayscale",
        "ink_threshold": "pixel value < 245",
        "blank_page_threshold": "< 20 ink pixels",
        "blank_pages": blank,
        "high_coverage_pages": high_coverage,
        "minimum_ink_page": minimum,
        "maximum_coverage_page": maximum,
        "page_census_bytes": len(canonical),
        "page_census_sha256": hashlib.sha256(canonical).hexdigest().upper(),
    }


def image_record(path: Path, represented_pages: tuple[int, ...]) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
        mode = image.mode
    return {**record(path), "dimensions": dimensions, "mode": mode, "represented_pages": list(represented_pages)}


def main() -> int:
    authenticate(READER, READER_PIN, "linked reader")
    authenticate(METHODS, METHODS_PIN, "methods paper")
    reader_renders = []
    for page in READER_PAGES:
        path = READER_RENDER_ROOT / f"page-{page:04d}.png"
        reader_renders.append(image_record(path, (page,)))
    method_renders = [image_record(METHODS_RENDER_ROOT / f"page-{page}.png", (page,)) for page in range(1, 7)]
    contact_rows = [image_record(path, pages) for path, pages in CONTACTS]

    receipt = {
        "schema": "noether-interslavic-v019-visual-qa/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-22T00:00:00Z",
        "inputs": {"linked_reader": {**record(READER), "pages": 1159}, "methods_paper": {**record(METHODS), "pages": 6}},
        "all_page_raster_census": {
            "linked_reader": raster_census(READER, 1159),
            "methods_paper": raster_census(METHODS, 6),
        },
        "rendered_samples": {
            "linked_reader_count": len(reader_renders),
            "linked_reader_pages": list(READER_PAGES),
            "linked_reader": reader_renders,
            "methods_count": len(method_renders),
            "methods_pages": list(range(1, 7)),
            "methods": method_renders,
        },
        "contact_sheets": contact_rows,
        "manual_review": {
            "reviewer_role": "primary Codex agent responsible for the release",
            "status": "PASS",
            "inspected": [
                "all four contact sheets",
                "linked-reader front matter pages 1-5 at full size",
                "Cyrillic divider page 571 at full size",
                "methods page 4 at full size after final metric update",
            ],
            "findings": {
                "clipped_or_overlapping_text": 0,
                "unreadable_or_missing_glyphs": 0,
                "broken_tables_or_formulas": 0,
                "blank_or_duplicate_transition_pages": 0,
                "header_footer_or_page_number_defects": 0,
            },
            "note": "Distributed controls span the complete Latin and Cyrillic readers; all newly authored front matter, boundaries, and methods pages were rendered, with every methods page visually represented.",
        },
        "status": "PASS",
    }
    output = RELEASE / "evidence" / "visual-qa-receipt.json"
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if json.loads(output.read_text(encoding="utf-8")) != receipt:
        raise RuntimeError("visual receipt readback mismatch")
    print(json.dumps({"status": "PASS", "receipt": record(output), "reader_pages": 1159, "sample_pages": len(reader_renders)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
