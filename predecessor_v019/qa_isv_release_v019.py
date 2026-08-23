#!/usr/bin/env python3
"""Independent structural, text, font, and PDF QA for NOETHER-ISV-v019."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
import unicodedata

from pypdf import PdfReader


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v019"
EVIDENCE = RELEASE / "evidence"
BUILD_MANIFEST = EVIDENCE / "build-manifest.json"
SOURCE_PAIRS = (
    ("44-book-isv.tex", "44-book-isv-cyrl.tex"),
    ("45-isv.tex", "45-isv-cyrl.tex"),
    ("base-papers1-43-isv.tex", "base-papers1-43-isv-cyrl.tex"),
    ("bib-isv.tex", "bib-isv-cyrl.tex"),
)
FATAL_LOG_PATTERNS = (
    "! LaTeX Error",
    "Undefined control sequence",
    "Emergency stop",
    "Fatal error",
    "TeX capacity exceeded",
    "Missing character:",
    "There were undefined references",
    "There were undefined citations",
)


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


def require(condition: bool, code: str, detail: Any, checks: list, errors: list) -> None:
    row = {"code": code, "pass": bool(condition), "detail": detail}
    checks.append(row)
    if not condition:
        errors.append(row)


def resolve(row: dict[str, Any]) -> Path:
    return ROOT / row["path"]


def extract_text(pdf: Path, output: Path) -> tuple[str, dict[str, Any]]:
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["pdftotext", "-layout", str(pdf.resolve()), str(output.resolve())],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(f"pdftotext failed for {pdf}: {completed.stderr}")
    text = output.read_text(encoding="utf-8", errors="replace")
    return text, {
        **record(output),
        "characters": len(text),
        "non_whitespace_characters": len(re.sub(r"\s+", "", text)),
        "replacement_characters": text.count("\ufffd"),
        "form_feeds": text.count("\f"),
        "stderr": completed.stderr.strip(),
    }


def text_pages(text: str) -> list[str]:
    pages = text.split("\f")
    while pages and not pages[-1].strip():
        pages.pop()
    return pages


def script_census(text: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for char in text:
        name = unicodedata.name(char, "")
        if "LATIN" in name and unicodedata.category(char).startswith("L"):
            counts["Latin"] += 1
        elif "CYRILLIC" in name and unicodedata.category(char).startswith("L"):
            counts["Cyrillic"] += 1
    return dict(counts)


def nonletter_signature(text: str) -> str:
    payload = "".join(
        char
        for char in text
        if not (
            unicodedata.category(char).startswith("L")
            or unicodedata.category(char).startswith("M")
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def pdf_record(pdf: Path) -> dict[str, Any]:
    reader = PdfReader(str(pdf))
    if reader.is_encrypted:
        raise RuntimeError(f"encrypted release PDF: {pdf}")
    sizes: Counter[str] = Counter()
    rotations: Counter[str] = Counter()
    annotations = 0
    blank_content_objects = 0
    for page in reader.pages:
        box = page.mediabox
        sizes[f"{float(box.width):.3f}x{float(box.height):.3f}"] += 1
        rotations[str(page.get("/Rotate", 0))] += 1
        annots = page.get("/Annots", [])
        if hasattr(annots, "get_object"):
            annots = annots.get_object()
        annotations += len(annots)
        if page.get_contents() is None:
            blank_content_objects += 1
    return {
        **record(pdf),
        "pages": len(reader.pages),
        "encrypted": False,
        "media_boxes": dict(sizes),
        "rotations": dict(rotations),
        "annotations": annotations,
        "pages_without_content_object": blank_content_objects,
        "metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items()},
    }


def font_record(pdf: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["pdffonts", str(pdf.resolve())],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(f"pdffonts failed for {pdf}: {completed.stderr}")
    rows = []
    for line in completed.stdout.splitlines()[2:]:
        match = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
        if match:
            rows.append({"line": line, "embedded": match.group(1), "subset": match.group(2), "unicode": match.group(3)})
    return {
        "font_rows": len(rows),
        "all_embedded": bool(rows) and all(row["embedded"] == "yes" for row in rows),
        "unicode_mapped_rows": sum(row["unicode"] == "yes" for row in rows),
        "unicode_unmapped_math_symbol_rows": sum(row["unicode"] == "no" for row in rows),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    manifest_raw = BUILD_MANIFEST.read_bytes()
    manifest = json.loads(manifest_raw.decode("utf-8"))
    checks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    require(manifest["release_id"] == "NOETHER-ISV-v019", "release-id", manifest["release_id"], checks, errors)
    require(manifest["build_policy"]["serial"] is True, "serial-build-policy", manifest["build_policy"], checks, errors)
    require(set(manifest["surfaces"]) == {"latn", "cyrl"}, "surface-topology", sorted(manifest["surfaces"]), checks, errors)

    source_checks = []
    for relative, expected in manifest["authenticated_inputs"].items():
        path = ROOT / relative
        actual = record(path)
        okay = actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]
        source_checks.append({"source": relative, "expected": expected, "actual": actual, "pass": okay})
    require(all(row["pass"] for row in source_checks), "authenticated-source-readback", source_checks, checks, errors)

    structure_pairs = []
    for latin_name, cyrillic_name in SOURCE_PAIRS:
        latin = (RELEASE / "source" / "latn" / latin_name).read_text(encoding="utf-8")
        cyrillic = (RELEASE / "source" / "cyrl" / cyrillic_name).read_text(encoding="utf-8")
        latin_signature = nonletter_signature(latin)
        cyrillic_signature = nonletter_signature(cyrillic)
        row = {
            "latin": latin_name,
            "cyrillic": cyrillic_name,
            "latin_nonletter_sha256": latin_signature,
            "cyrillic_nonletter_sha256": cyrillic_signature,
            "pass": latin_signature == cyrillic_signature,
        }
        structure_pairs.append(row)
    require(all(row["pass"] for row in structure_pairs), "cross-script-nonletter-structure", structure_pairs, checks, errors)

    log_rows = []
    for surface in ("latn", "cyrl"):
        data = manifest["surfaces"][surface]
        groups = [item["build_logs"] for item in data["components"]] + [data["build_logs"]]
        for group in groups:
            for log in group:
                tex_log = resolve(log["tex_log"])
                text = tex_log.read_text(encoding="utf-8", errors="replace")
                hits = [pattern for pattern in FATAL_LOG_PATTERNS if pattern.casefold() in text.casefold()]
                log_rows.append({"surface": surface, "log": record(tex_log), "fatal_patterns": hits, "warnings": log["warnings"]})
    require(all(not row["fatal_patterns"] for row in log_rows), "build-log-fatal-scan", log_rows, checks, errors)

    text_dir = EVIDENCE / "text"
    surface_results: dict[str, Any] = {}
    for surface in ("latn", "cyrl"):
        data = manifest["surfaces"][surface]
        reader_pdf = resolve(data["reader_pdf"])
        reader_pdf_record = pdf_record(reader_pdf)
        require(reader_pdf_record["sha256"] == data["reader_pdf"]["sha256"], f"reader-hash-{surface}", reader_pdf_record, checks, errors)
        require(reader_pdf_record["pages"] == data["reader_pdf"]["pages"], f"reader-pages-{surface}", reader_pdf_record, checks, errors)
        reader_fonts = font_record(reader_pdf)
        require(reader_fonts["all_embedded"], f"reader-font-embedding-{surface}", reader_fonts, checks, errors)
        reader_text, reader_extract = extract_text(reader_pdf, text_dir / f"reader-{surface}.txt")
        reader_pages = text_pages(reader_text)
        require(len(reader_pages) == reader_pdf_record["pages"], f"reader-text-page-count-{surface}", {"text_pages": len(reader_pages), "pdf_pages": reader_pdf_record["pages"]}, checks, errors)
        require(reader_extract["replacement_characters"] == 0 and reader_extract["non_whitespace_characters"] > 100_000, f"reader-text-integrity-{surface}", reader_extract, checks, errors)

        component_text_pages: list[str] = []
        component_results = []
        for component in data["components"]:
            pdf = resolve(component["pdf"])
            pdf_info = pdf_record(pdf)
            require(pdf_info["sha256"] == component["pdf"]["sha256"], f"component-hash-{surface}-{component['component']}", pdf_info, checks, errors)
            text, extraction = extract_text(pdf, text_dir / f"component-{surface}-{component['component']}.txt")
            pages = text_pages(text)
            require(len(pages) == component["pdf"]["pages"], f"component-text-pages-{surface}-{component['component']}", {"text_pages": len(pages), "pdf_pages": component["pdf"]["pages"]}, checks, errors)
            component_text_pages.extend(pages)
            component_results.append({"component": component["component"], "pdf": pdf_info, "text": extraction})
        pagewise_sequence_identical = component_text_pages == reader_pages
        pagewise_character_multiset_identical = all(
            Counter(re.sub(r"\s+", "", component_page))
            == Counter(re.sub(r"\s+", "", reader_page))
            for component_page, reader_page in zip(component_text_pages, reader_pages)
        )
        require(
            pagewise_character_multiset_identical,
            f"cumulative-pagewise-character-identity-{surface}",
            {
                "component_pages": len(component_text_pages),
                "reader_pages": len(reader_pages),
                "layout_sequence_identical": pagewise_sequence_identical,
                "note": "pdfpages coordinate transforms can change pdftotext -layout ordering; the exact non-whitespace character multiset is required page by page",
            },
            checks,
            errors,
        )
        census = script_census(reader_text)
        if surface == "latn":
            script_ok = census.get("Latin", 0) > max(10_000, census.get("Cyrillic", 0) * 20)
        else:
            script_ok = census.get("Cyrillic", 0) > max(10_000, census.get("Latin", 0) * 3)
        require(script_ok, f"reader-script-census-{surface}", census, checks, errors)
        boundaries = []
        cursor = 0
        for component in data["components"]:
            start = cursor
            cursor += component["pdf"]["pages"]
            boundaries.append(
                {
                    "component": component["component"],
                    "first_page_non_whitespace": len(re.sub(r"\s+", "", reader_pages[start])),
                    "last_page_non_whitespace": len(re.sub(r"\s+", "", reader_pages[cursor - 1])),
                }
            )
        require(all(row["first_page_non_whitespace"] > 20 and row["last_page_non_whitespace"] > 20 for row in boundaries), f"component-boundary-text-{surface}", boundaries, checks, errors)
        surface_results[surface] = {
            "reader": reader_pdf_record,
            "fonts": reader_fonts,
            "text": reader_extract,
            "script_census": census,
            "pagewise_component_character_identity": pagewise_character_multiset_identical,
            "pagewise_layout_sequence_identity": pagewise_sequence_identical,
            "boundaries": boundaries,
            "components": component_results,
        }

    report = {
        "schema": "noether-interslavic-v019-release-qa/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-21T00:00:00Z",
        "pass": not errors,
        "scope": "frozen Latin edition and deterministic Cyrillic projection; two cumulative pre-publication readers",
        "build_manifest": {**record(BUILD_MANIFEST), "internal_release_id": manifest["release_id"]},
        "checks": checks,
        "errors": errors,
        "source_readback": source_checks,
        "cross_script_structure": structure_pairs,
        "build_logs": log_rows,
        "surfaces": surface_results,
        "claim_boundary": {
            "cyrillic": "deterministic script projection; not an independent translation witness",
            "review": "model/agent-produced and machine-assisted; no native-speaker or community certification claimed",
            "visual": "rendered-page review is a separate required receipt",
        },
    }
    output = EVIDENCE / "qa-report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    readback = json.loads(output.read_text(encoding="utf-8"))
    if readback != report:
        raise RuntimeError("QA report readback mismatch")
    print(json.dumps({"status": "PASS" if report["pass"] else "FAIL", "checks": len(checks), "errors": len(errors), "report": record(output)}, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
