#!/usr/bin/env python3
"""Authenticate and seal the complete rendered-page QA for NOETHER-ISV-v020."""

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
RELEASE = ROOT / "release_v020"
EVIDENCE = RELEASE / "evidence"
READER = RELEASE / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
METHODS = EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf"
LINKED_ASSETS = EVIDENCE / "linked-reader-visual-assets.json"
METHODS_ASSETS = EVIDENCE / "methods-visual-assets.json"
DELTA = EVIDENCE / "cyrillic-rendered-page-delta-v019-to-v020.json"

PINS = {
    READER: (6_885_841, "7DCB4C852BF3CCE5928921E13F73FA34E80EA4FEB2A82F967FEE29657150AE20"),
    METHODS: (178_720, "DA45E0B1C4D40B6582C312C578812E709C5E42C6FCEE663FF0599DCAFC39AED7"),
    LINKED_ASSETS: (13_421, "4ACA2ACFF2B843212A0A411C8DA8D131CBF9EC4B1776D6A2EC91EED9B495DE92"),
    METHODS_ASSETS: (2_033, "D0A2D35630BAA81098C81B6A308602A5E0A256617FAEFF365D189D9BCBE54258"),
    DELTA: (65_031, "51858018D2BF796F0620B216BF6C932C9E1D839402A6031EC12334E57B477A55"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def authenticate(path: Path) -> None:
    require(path.is_file(), f"missing input: {path}")
    actual = (path.stat().st_size, sha256(path))
    require(actual == PINS[path], f"input pin drift for {path}: {actual}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def image_record(path: Path, declared: dict[str, Any]) -> dict[str, Any]:
    require(path.is_file(), f"missing rendered asset: {path}")
    actual = record(path)
    require(actual["bytes"] == declared["bytes"], f"image byte drift: {path}")
    require(actual["sha256"] == declared["sha256"], f"image hash drift: {path}")
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        dimensions = [image.width, image.height]
        mode = image.mode
    require(dimensions == declared["dimensions"], f"image dimension drift: {path}")
    return {
        **actual,
        "dimensions": dimensions,
        "mode": mode,
        "represented_pages": declared["represented_pages"],
    }


def raster_census(path: Path, expected_pages: int) -> dict[str, Any]:
    document = fitz.open(path)
    require(len(document) == expected_pages, f"page-count drift for {path}: {len(document)}")
    rows: list[dict[str, Any]] = []
    for page_number, page in enumerate(document, 1):
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(0.5, 0.5), colorspace=fitz.csGRAY, alpha=False
        )
        width, height = pixmap.width, pixmap.height
        ink_pixels = 0
        min_x, min_y = width, height
        max_x = max_y = -1
        for index, value in enumerate(pixmap.samples):
            if value >= 245:
                continue
            ink_pixels += 1
            x, y = index % width, index // width
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x), max(max_y, y)
        bbox = None if ink_pixels == 0 else [min_x, min_y, max_x, max_y]
        rows.append(
            {
                "page": page_number,
                "width": width,
                "height": height,
                "ink_pixels": ink_pixels,
                "ink_fraction": ink_pixels / (width * height),
                "ink_bbox": bbox,
            }
        )
    document.close()
    blank = [row["page"] for row in rows if row["ink_pixels"] < 20]
    high_coverage = [row["page"] for row in rows if row["ink_fraction"] > 0.50]
    require(not blank and not high_coverage, f"raster anomaly: blank={blank}, high={high_coverage}")
    canonical = (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return {
        "pages": len(rows),
        "render_scale": 0.5,
        "colorspace": "grayscale",
        "ink_threshold": "pixel value < 245",
        "blank_page_threshold": "< 20 ink pixels",
        "blank_pages": blank,
        "high_coverage_pages": high_coverage,
        "minimum_ink_page": min(rows, key=lambda row: row["ink_pixels"]),
        "maximum_coverage_page": max(rows, key=lambda row: row["ink_fraction"]),
        "page_census_bytes": len(canonical),
        "page_census_sha256": hashlib.sha256(canonical).hexdigest().upper(),
    }


def authenticate_asset_manifest(
    manifest_path: Path, expected_schema: str, expected_count: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    require(manifest["schema"] == expected_schema, f"schema drift: {manifest_path}")
    require(manifest["release_id"] == "NOETHER-ISV-v020", f"release drift: {manifest_path}")
    require(manifest["status"] == "ASSETS_RENDERED_AWAITING_MANUAL_REVIEW", f"asset state drift: {manifest_path}")
    declarations = manifest["contact_sheets"]
    require(len(declarations) == expected_count, f"contact-sheet count drift: {manifest_path}")
    rows = []
    for declaration in declarations:
        path = ROOT / declaration["path"]
        rows.append(image_record(path, declaration))
    return manifest, rows


def main() -> int:
    for path in PINS:
        authenticate(path)

    linked, linked_images = authenticate_asset_manifest(
        LINKED_ASSETS, "noether-interslavic-linked-reader-visual-assets/1.0", 25
    )
    methods, methods_images = authenticate_asset_manifest(
        METHODS_ASSETS, "noether-interslavic-methods-visual-assets/1.0", 4
    )
    delta = load_json(DELTA)
    require(delta["status"] == "PASS", "rendered delta did not pass")
    result = delta["result"]
    changed = result["changed_linked_reader_pages"]
    controls = result["adjacent_unchanged_control_linked_reader_pages"]
    coverage = linked["coverage"]
    require(result["compared_pages"] == 588, "delta page-count drift")
    require(result["changed_pages"] == 86 and len(changed) == 86, "changed-page count drift")
    require(len(controls) == 103, "control-page count drift")
    require(changed == coverage["changed_pages"], "changed-page asset coverage drift")
    require(controls == coverage["adjacent_unchanged_control_pages"], "control asset coverage drift")
    require(methods["coverage"]["all_pages"] == list(range(1, 14)), "methods coverage drift")

    linked_changed_rendered = sorted(
        page
        for row in linked_images
        if Path(row["path"]).name.startswith("changed-pages-")
        for page in row["represented_pages"]
    )
    linked_controls_rendered = sorted(
        page
        for row in linked_images
        if Path(row["path"]).name.startswith("adjacent-controls-")
        for page in row["represented_pages"]
    )
    require(linked_changed_rendered == changed, "not every changed page is rendered exactly once")
    require(linked_controls_rendered == controls, "not every control page is rendered exactly once")
    require(
        sorted(page for row in methods_images for page in row["represented_pages"]) == list(range(1, 14)),
        "not every methods page is rendered exactly once",
    )

    receipt = {
        "schema": "noether-interslavic-v020-visual-qa/1.0",
        "release_id": "NOETHER-ISV-v020",
        "generated_at": "2026-08-22T00:00:00Z",
        "inputs": {
            "linked_reader": {**record(READER), "pages": 1159},
            "methods_paper": {**record(METHODS), "pages": 13},
            "linked_reader_visual_assets": record(LINKED_ASSETS),
            "methods_visual_assets": record(METHODS_ASSETS),
            "rendered_delta": record(DELTA),
        },
        "all_page_raster_census": {
            "linked_reader": raster_census(READER, 1159),
            "methods_paper": raster_census(METHODS, 13),
        },
        "rendered_manual_review_surfaces": {
            "linked_reader_contact_sheets": linked_images,
            "methods_contact_sheets": methods_images,
            "contact_sheet_count": len(linked_images) + len(methods_images),
            "changed_pages": changed,
            "changed_page_count": len(changed),
            "adjacent_unchanged_control_pages": controls,
            "adjacent_unchanged_control_page_count": len(controls),
            "front_and_boundaries": coverage["front_and_boundaries"],
            "methods_pages": list(range(1, 14)),
        },
        "manual_review": {
            "reviewer_role": "primary Codex agent responsible for the release",
            "status": "PASS",
            "inspection_method": "all 29 contact sheets opened and inspected at original detail",
            "coverage": [
                "all 86 visibly changed Cyrillic linked-reader pages",
                "all 103 adjacent visibly unchanged control pages",
                "new linked-reader front matter and both script boundaries",
                "all 13 Interslavic-first bilingual methods-paper pages",
            ],
            "findings": {
                "clipped_or_overlapping_text": 0,
                "unreadable_or_missing_glyphs": 0,
                "broken_tables_or_formulas": 0,
                "blank_or_duplicate_transition_pages": 0,
                "header_footer_or_page_number_defects": 0,
            },
            "note": "Page 13 of the methods paper is intentionally short citation/reuse material; it is not a blank-page defect.",
        },
        "status": "PASS",
    }

    output = EVIDENCE / "visual-qa-receipt.json"
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    require(load_json(output) == receipt, "visual receipt readback mismatch")
    print(
        json.dumps(
            {
                "status": "PASS",
                "receipt": record(output),
                "linked_reader_pages": 1159,
                "methods_pages": 13,
                "changed_pages": len(changed),
                "controls": len(controls),
                "contact_sheets": len(linked_images) + len(methods_images),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
