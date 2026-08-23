#!/usr/bin/env python3
"""Localize every rendered-page delta from public v019 to v020 Cyrillic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import fitz


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
ARCHIVED_OLD_LINKED = ROOT / "comparison" / "v019-linked-reader.pdf"
TASK_LOCAL_OLD_LINKED = ROOT / "tmp" / "pdfs" / "isv_release_v020" / "comparison" / "v019-linked-reader.pdf"
OLD_LINKED = ARCHIVED_OLD_LINKED if ARCHIVED_OLD_LINKED.is_file() else TASK_LOCAL_OLD_LINKED
NEW_LINKED = ROOT / "release_v020" / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
OUTPUT = ROOT / "release_v020" / "evidence" / "cyrillic-rendered-page-delta-v019-to-v020.json"
OLD_PIN = (6_885_443, "E14B2C9336E94878370332913360ECC52935AE93A89701BC7A5AE22C0552C401")
NEW_PIN = (6_885_841, "7DCB4C852BF3CCE5928921E13F73FA34E80EA4FEB2A82F967FEE29657150AE20")
OLD_FIRST_CYRILLIC_INDEX = 571  # zero-based linked-reader page index; public page 572
EXPECTED_PAGES = 588


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, object]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def authenticate(path: Path, pin: tuple[int, str], label: str) -> None:
    actual = (path.stat().st_size, sha256_file(path))
    if actual != pin:
        raise RuntimeError(f"{label} pin drift: {actual}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def main() -> int:
    authenticate(OLD_LINKED, OLD_PIN, "v019 public linked reader")
    authenticate(NEW_LINKED, NEW_PIN, "v020 public-candidate linked reader")
    old_doc = fitz.open(OLD_LINKED)
    new_doc = fitz.open(NEW_LINKED)
    if len(old_doc) != 1_159 or len(new_doc) != 1_159:
        raise RuntimeError(f"page topology drift: old={len(old_doc)}, new={len(new_doc)}")

    changed: list[dict[str, object]] = []
    unchanged = 0
    matrix = fitz.Matrix(1.0, 1.0)
    for component_index in range(EXPECTED_PAGES):
        old_page = old_doc[OLD_FIRST_CYRILLIC_INDEX + component_index]
        new_page = new_doc[OLD_FIRST_CYRILLIC_INDEX + component_index]
        old_pix = old_page.get_pixmap(
            matrix=matrix, colorspace=fitz.csGRAY, alpha=False, annots=False
        )
        new_pix = new_page.get_pixmap(
            matrix=matrix, colorspace=fitz.csGRAY, alpha=False, annots=False
        )
        dimensions = (old_pix.width, old_pix.height, new_pix.width, new_pix.height)
        old_samples = old_pix.samples
        new_samples = new_pix.samples
        if dimensions[:2] != dimensions[2:]:
            raise RuntimeError(
                f"render dimension drift on component page {component_index + 1}: {dimensions}"
            )
        if old_samples == new_samples:
            unchanged += 1
            continue
        width = old_pix.width
        differing = [
            offset
            for offset, (before, after) in enumerate(zip(old_samples, new_samples))
            if before != after
        ]
        xs = [offset % width for offset in differing]
        ys = [offset // width for offset in differing]
        old_text = old_page.get_text("text").encode("utf-8")
        new_text = new_page.get_text("text").encode("utf-8")
        changed.append(
            {
                "component_page": component_index + 1,
                "linked_reader_page": OLD_FIRST_CYRILLIC_INDEX + component_index + 1,
                "dimensions": [old_pix.width, old_pix.height],
                "differing_pixels": len(differing),
                "difference_bbox": [min(xs), min(ys), max(xs), max(ys)],
                "old_render_sha256": sha256_bytes(old_samples),
                "new_render_sha256": sha256_bytes(new_samples),
                "old_text_sha256": sha256_bytes(old_text),
                "new_text_sha256": sha256_bytes(new_text),
                "text_changed": old_text != new_text,
            }
        )

    changed_pages = [int(row["component_page"]) for row in changed]
    adjacent_controls = sorted(
        {
            neighbor
            for page in changed_pages
            for neighbor in (page - 1, page + 1)
            if 1 <= neighbor <= EXPECTED_PAGES and neighbor not in changed_pages
        }
    )
    receipt = {
        "schema": "noether-interslavic-cyrillic-render-delta/1.0",
        "release_id": "NOETHER-ISV-v020",
        "comparison": "public v019 embedded Cyrillic pages against v020 public-candidate embedded Cyrillic pages",
        "render": {
            "engine": f"PyMuPDF {fitz.VersionBind}",
            "matrix": [1.0, 1.0],
            "colorspace": "grayscale",
            "alpha": False,
            "annotations": False,
        },
        "inputs": {
            "v019_public_linked_reader": {**record(OLD_LINKED), "pages": len(old_doc)},
            "v020_public_candidate_linked_reader": {**record(NEW_LINKED), "pages": len(new_doc)},
            "v019_embedded_cyrillic_page_range": [572, 1159],
        },
        "result": {
            "compared_pages": EXPECTED_PAGES,
            "unchanged_pages": unchanged,
            "changed_pages": len(changed),
            "changed_component_pages": changed_pages,
            "changed_linked_reader_pages": [
                int(row["linked_reader_page"]) for row in changed
            ],
            "adjacent_unchanged_control_component_pages": adjacent_controls,
            "adjacent_unchanged_control_linked_reader_pages": [
                page + OLD_FIRST_CYRILLIC_INDEX for page in adjacent_controls
            ],
            "details": changed,
        },
        "status": "PASS",
    }
    OUTPUT.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if json.loads(OUTPUT.read_text(encoding="utf-8")) != receipt:
        raise RuntimeError("render-delta receipt readback mismatch")
    print(
        json.dumps(
            {
                "status": "PASS",
                "changed_pages": len(changed),
                "changed_component_pages": changed_pages,
                "adjacent_controls": adjacent_controls,
                "receipt": record(OUTPUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
