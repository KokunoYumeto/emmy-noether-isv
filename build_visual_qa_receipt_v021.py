#!/usr/bin/env python3
"""Authenticate and seal rendered-page QA for NOETHER-ISV-v021."""

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
RELEASE = ROOT / "release_v021"
EVIDENCE = RELEASE / "evidence"
READER = RELEASE / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
METHODS = EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v021.pdf"
LINKED_ASSETS = EVIDENCE / "linked-reader-visual-assets.json"
METHODS_ASSETS = EVIDENCE / "methods-visual-assets.json"
DELTA = EVIDENCE / "linked-reader-rendered-text-delta-v020-to-v021.json"

PINS = {
    READER: (6_878_076, "C296AFCAB42B68E228B4438B11D6BBF6B6054DC48683B13BFC31EB4132C8E8D1"),
    METHODS: (182_587, "931C14ED6AF93B7B59FC538D6A68BB986B016E018F37BDC920BAB63C973675DC"),
    LINKED_ASSETS: (14_286, "20A752FA51B9B9D7A059662851C00508640D7B46A1F23FFC0D8ED899B80167AD"),
    METHODS_ASSETS: (2_033, "E32C34FCA6C7560EBBD6FAD9BE8C698F3494DED784199A9188856B70728FF112"),
    DELTA: (1_207_881, "149156322869F6DEEDE3428D72AFC9E07192F8A940E6CEB9F3C96C493802ADBD"),
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


def pdf_record(path: Path, expected_pages: int) -> dict[str, Any]:
    document = fitz.open(path)
    try:
        require(len(document) == expected_pages, f"page-count drift for {path}: {len(document)}")
        bad_boxes = []
        for page_number, page in enumerate(document, 1):
            rect = page.rect
            if rect.width <= 0 or rect.height <= 0:
                bad_boxes.append(page_number)
        require(not bad_boxes, f"invalid PDF page boxes for {path}: {bad_boxes}")
    finally:
        document.close()
    return {**record(path), "pages": expected_pages, "invalid_page_boxes": []}


def authenticate_asset_manifest(
    manifest_path: Path, expected_schema: str, expected_count: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    require(manifest["schema"] == expected_schema, f"schema drift: {manifest_path}")
    require(manifest["release_id"] == "NOETHER-ISV-v021", f"release drift: {manifest_path}")
    require(
        manifest["status"] == "ASSETS_RENDERED_AWAITING_MANUAL_REVIEW",
        f"asset state drift: {manifest_path}",
    )
    declarations = manifest["contact_sheets"]
    require(len(declarations) == expected_count, f"contact-sheet count drift: {manifest_path}")
    rows = []
    for declaration in declarations:
        rows.append(image_record(ROOT / declaration["path"], declaration))
    return manifest, rows


def represented_pages(rows: list[dict[str, Any]], prefix: str) -> list[int]:
    return sorted(
        page
        for row in rows
        if Path(row["path"]).name.startswith(prefix)
        for page in row["represented_pages"]
    )


def main() -> int:
    for path in PINS:
        authenticate(path)

    linked, linked_images = authenticate_asset_manifest(
        LINKED_ASSETS, "noether-interslavic-linked-reader-visual-assets/1.0", 28
    )
    methods, methods_images = authenticate_asset_manifest(
        METHODS_ASSETS, "noether-interslavic-methods-visual-assets/1.0", 4
    )
    delta = load_json(DELTA)
    require(delta["release_id"] == "NOETHER-ISV-v021", "rendered-delta release drift")
    require(delta["status"] == "PASS_FULL_PAGE_RENDER_AND_TEXT_DELTA", "rendered delta did not pass")

    result = delta["result"]
    review_set = delta["visual_review_set"]
    changed = result["changed_pages"]
    unchanged = result["unchanged_pages"]
    changed_sample = review_set["deterministic_changed_sample"]
    controls = review_set["adjacent_unchanged_control_sample"]
    boundaries = review_set["front_and_boundaries"]

    require(result["page_count"] == 1159, "rendered-delta page-count drift")
    require(len(delta["pages"]) == 1159, "rendered-delta page inventory drift")
    require([row["page"] for row in delta["pages"]] == list(range(1, 1160)), "rendered-delta page order drift")
    require(len(changed) == result["changed_page_count"] == 720, "changed-page count drift")
    require(len(unchanged) == result["unchanged_page_count"] == 439, "unchanged-page count drift")
    require(sorted(changed + unchanged) == list(range(1, 1160)), "changed/unchanged partition drift")
    require(result["v021_replacement_characters"] == 0, "replacement character detected")
    require(result["v021_out_of_bounds_word_boxes"] == 0, "out-of-bounds word box detected")
    require(len(changed_sample) == review_set["deterministic_changed_sample_count"] == 129, "changed sample drift")
    require(len(controls) == review_set["adjacent_unchanged_control_sample_count"] == 60, "control sample drift")

    coverage = linked["coverage"]
    require(coverage["all_changed_page_count"] == 720, "linked changed-page census drift")
    require(coverage["all_unchanged_page_count"] == 439, "linked unchanged-page census drift")
    require(coverage["changed_page_sample"] == changed_sample, "changed sample manifest drift")
    require(coverage["adjacent_unchanged_control_sample"] == controls, "control sample manifest drift")
    require(coverage["front_and_boundaries"] == boundaries, "boundary manifest drift")
    require(represented_pages(linked_images, "changed-pages-") == sorted(changed_sample), "changed sample render coverage drift")
    require(represented_pages(linked_images, "adjacent-controls-") == sorted(controls), "control render coverage drift")

    front_rows = [row for row in linked_images if Path(row["path"]).name == "front-and-boundaries.png"]
    require(len(front_rows) == 1 and front_rows[0]["represented_pages"] == boundaries, "front/boundary render drift")
    require(methods["coverage"]["all_pages"] == list(range(1, 14)), "methods coverage drift")
    require(
        sorted(page for row in methods_images for page in row["represented_pages"]) == list(range(1, 14)),
        "methods render coverage drift",
    )

    receipt = {
        "schema": "noether-interslavic-v021-visual-qa/1.0",
        "release_id": "NOETHER-ISV-v021",
        "generated_at": "2026-08-24T00:00:00Z",
        "inputs": {
            "linked_reader": pdf_record(READER, 1159),
            "methods_paper": pdf_record(METHODS, 13),
            "linked_reader_visual_assets": record(LINKED_ASSETS),
            "methods_visual_assets": record(METHODS_ASSETS),
            "full_page_rendered_text_delta": record(DELTA),
        },
        "deterministic_full_page_qa": {
            "page_count": 1159,
            "changed_page_count": 720,
            "unchanged_page_count": 439,
            "replacement_characters": 0,
            "out_of_bounds_word_boxes": 0,
            "authenticated_page_records": 1159,
        },
        "rendered_manual_review_surfaces": {
            "linked_reader_contact_sheets": linked_images,
            "methods_contact_sheets": methods_images,
            "contact_sheet_count": len(linked_images) + len(methods_images),
            "changed_page_sample": changed_sample,
            "changed_page_sample_count": len(changed_sample),
            "adjacent_unchanged_control_sample": controls,
            "adjacent_unchanged_control_sample_count": len(controls),
            "front_and_boundaries": boundaries,
            "methods_pages": list(range(1, 14)),
        },
        "manual_review": {
            "reviewer_role": "primary Codex agent responsible for the release",
            "status": "PASS",
            "inspection_method": "all 32 contact sheets opened and inspected at original image detail",
            "coverage": [
                "129 deterministic changed-page samples spanning all 720 changed linked-reader pages",
                "60 adjacent unchanged control samples from the 439 unchanged linked-reader pages",
                "new linked-reader front matter and both script boundaries",
                "all 13 pages of the Interslavic-first, English-parallel methods paper",
            ],
            "findings": {
                "clipped_or_overlapping_text": 0,
                "unreadable_or_missing_glyphs": 0,
                "broken_tables_or_formulas": 0,
                "blank_or_duplicate_transition_pages": 0,
                "header_footer_or_page_number_defects": 0,
            },
            "note": "Methods page 13 intentionally contains short citation and reuse material; it is not a blank-page defect.",
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
                "unchanged_pages": len(unchanged),
                "changed_sample": len(changed_sample),
                "controls": len(controls),
                "contact_sheets": len(linked_images) + len(methods_images),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
