#!/usr/bin/env python3
"""Compare every rendered/text page of the v020 and v021 linked readers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import fitz


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
OLD = ROOT / "comparison" / "v020-linked-reader.pdf"
NEW = ROOT / "release_v021" / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
OUTPUT = ROOT / "release_v021" / "evidence" / "linked-reader-rendered-text-delta-v020-to-v021.json"
OLD_PIN = (6_885_841, "7DCB4C852BF3CCE5928921E13F73FA34E80EA4FEB2A82F967FEE29657150AE20")
NEW_PIN = (6_878_076, "C296AFCAB42B68E228B4438B11D6BBF6B6054DC48683B13BFC31EB4132C8E8D1")
EXPECTED_PAGES = 1_159
FRONT_AND_BOUNDARIES = (1, 2, 3, 4, 5, 6, 570, 571, 572, 1_159)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def authenticate(path: Path, pin: tuple[int, str], label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"missing or unsafe {label}: {path}")
    actual = (path.stat().st_size, sha256_file(path))
    if actual != pin:
        raise RuntimeError(f"{label} pin drift: {actual}")


def page_evidence(page: fitz.Page) -> dict[str, Any]:
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(0.75, 0.75),
        colorspace=fitz.csGRAY,
        alpha=False,
        annots=False,
    )
    text = page.get_text("text", sort=True)
    text_raw = text.encode("utf-8")
    words = page.get_text("words", sort=True)
    width, height = page.rect.width, page.rect.height
    out_of_bounds = [
        [round(float(value), 3) for value in word[:4]]
        for word in words
        if word[0] < -0.5 or word[1] < -0.5 or word[2] > width + 0.5 or word[3] > height + 0.5
    ]
    return {
        "render_sha256": sha256_bytes(pixmap.samples),
        "render_dimensions": [pixmap.width, pixmap.height],
        "text_bytes": len(text_raw),
        "text_sha256": sha256_bytes(text_raw),
        "text_characters": len(text),
        "replacement_characters": text.count("\ufffd"),
        "word_count": len(words),
        "out_of_bounds_word_boxes": out_of_bounds,
    }


def even_sample(values: list[int], limit: int) -> list[int]:
    if len(values) <= limit:
        return list(values)
    if limit <= 1:
        return [values[0]]
    indexes = {round(index * (len(values) - 1) / (limit - 1)) for index in range(limit)}
    return [values[index] for index in sorted(indexes)]


def main() -> int:
    authenticate(OLD, OLD_PIN, "v020 linked reader")
    authenticate(NEW, NEW_PIN, "v021 linked reader")
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite delta receipt: {OUTPUT}")
    old_document = fitz.open(OLD)
    new_document = fitz.open(NEW)
    if len(old_document) != EXPECTED_PAGES or len(new_document) != EXPECTED_PAGES:
        raise RuntimeError(f"page topology drift: {len(old_document)} / {len(new_document)}")

    rows: list[dict[str, Any]] = []
    changed: list[int] = []
    unchanged: list[int] = []
    new_replacement_characters = 0
    new_out_of_bounds: list[dict[str, Any]] = []
    for page_number in range(1, EXPECTED_PAGES + 1):
        old = page_evidence(old_document[page_number - 1])
        new = page_evidence(new_document[page_number - 1])
        render_changed = old["render_sha256"] != new["render_sha256"]
        text_changed = old["text_sha256"] != new["text_sha256"]
        is_changed = render_changed or text_changed
        (changed if is_changed else unchanged).append(page_number)
        new_replacement_characters += int(new["replacement_characters"])
        if new["out_of_bounds_word_boxes"]:
            new_out_of_bounds.append({"page": page_number, "boxes": new["out_of_bounds_word_boxes"]})
        rows.append({
            "page": page_number,
            "part": (
                "front"
                if page_number <= 4
                else "latin_divider"
                if page_number == 5
                else "latin"
                if page_number <= 570
                else "cyrillic_divider"
                if page_number == 571
                else "cyrillic"
            ),
            "changed": is_changed,
            "render_changed": render_changed,
            "text_changed": text_changed,
            "v020": old,
            "v021": new,
        })

    changed_set = set(changed)
    adjacent_controls = sorted({
        neighbor
        for page in changed
        for neighbor in (page - 1, page + 1)
        if 1 <= neighbor <= EXPECTED_PAGES and neighbor not in changed_set
    })
    sampled_changed = sorted(set(FRONT_AND_BOUNDARIES) | set(even_sample(changed, 120)))
    sampled_controls = even_sample(adjacent_controls, 60)
    by_part: dict[str, dict[str, int]] = {}
    for row in rows:
        part = str(row["part"])
        bucket = by_part.setdefault(part, {"pages": 0, "changed": 0, "unchanged": 0})
        bucket["pages"] += 1
        bucket["changed" if row["changed"] else "unchanged"] += 1
    if new_replacement_characters:
        raise RuntimeError(f"replacement characters in v021 reader: {new_replacement_characters}")
    if new_out_of_bounds:
        raise RuntimeError(f"out-of-bounds word boxes in v021 reader: {new_out_of_bounds[:3]}")

    receipt = {
        "schema": "noether-interslavic-linked-reader-rendered-text-delta/1.0",
        "release_id": "NOETHER-ISV-v021",
        "status": "PASS_FULL_PAGE_RENDER_AND_TEXT_DELTA",
        "inputs": {
            "v020": {**record(OLD), "pages": len(old_document)},
            "v021": {**record(NEW), "pages": len(new_document)},
        },
        "method": {
            "render_engine": f"PyMuPDF {fitz.VersionBind}",
            "render_matrix": [0.75, 0.75],
            "render_colorspace": "GRAY",
            "annotations_rendered": False,
            "text_extraction": "PyMuPDF page.get_text('text', sort=True)",
            "page_changed_if": "render SHA-256 differs or extracted-text SHA-256 differs",
        },
        "result": {
            "page_count": EXPECTED_PAGES,
            "changed_pages": changed,
            "changed_page_count": len(changed),
            "unchanged_pages": unchanged,
            "unchanged_page_count": len(unchanged),
            "adjacent_unchanged_control_pages": adjacent_controls,
            "adjacent_unchanged_control_page_count": len(adjacent_controls),
            "by_part": by_part,
            "v021_replacement_characters": new_replacement_characters,
            "v021_out_of_bounds_word_boxes": len(new_out_of_bounds),
        },
        "visual_review_set": {
            "front_and_boundaries": list(FRONT_AND_BOUNDARIES),
            "deterministic_changed_sample": sampled_changed,
            "deterministic_changed_sample_count": len(sampled_changed),
            "adjacent_unchanged_control_sample": sampled_controls,
            "adjacent_unchanged_control_sample_count": len(sampled_controls),
            "sampling_rule": "All front/boundary controls plus at most 120 evenly spaced changed pages and at most 60 evenly spaced adjacent unchanged controls.",
        },
        "pages": rows,
    }
    raw = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    OUTPUT.write_bytes(raw)
    if OUTPUT.read_bytes() != raw:
        raise RuntimeError("delta receipt readback mismatch")
    print(json.dumps({
        "status": receipt["status"],
        "changed_pages": len(changed),
        "unchanged_pages": len(unchanged),
        "changed_sample": len(sampled_changed),
        "control_sample": len(sampled_controls),
        "by_part": by_part,
        "receipt": record(OUTPUT),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
