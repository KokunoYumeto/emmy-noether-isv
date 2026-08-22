#!/usr/bin/env python3
"""Deterministic ISV019 Latin-to-Cyrillic projector with reviewed role manifest.

Version 5 closes the two gates deliberately left open by v4.  It consumes the
exact EDIT0171 source vector and the final completeness inventory, protects
the reviewed foreign/title/name and one-letter structural spans, consumes the
722 already-reviewed multi-letter Roman identities, and delegates every other
visible word to the frozen v2 transliterator.  Latin and Cyrillic remain two
scripts of the same Interslavic edition; no translation witness is created.

Default execution is read-only.  ``--write-output`` may create the four
derived files in one explicit directory.  Existing non-identical outputs are
never overwritten.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Iterable, Mapping, Sequence
import unicodedata


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
STATE_PATH = ROOT / "00_SESSION_INDEPENDENT_STATE_v019.json"
V4_PATH = ROOT / "project_isv_cyrillic_v4.py"
AUDIT_SCRIPT_PATH = ROOT / "audit_isv_final_projection_completeness_v019.py"
MANIFEST_PATH = (
    ROOT / "decision_records/ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json"
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
OUTPUT_NAMES = {
    "44-book-isv.tex": "44-book-isv-cyrl.tex",
    "45-isv.tex": "45-isv-cyrl.tex",
    "base-papers1-43-isv.tex": "base-papers1-43-isv-cyrl.tex",
    "bib-isv.tex": "bib-isv-cyrl.tex",
}
SOURCE_PINS = {
    "44-book-isv.tex": (
        168_422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    "45-isv.tex": (
        26_053,
        "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91",
    ),
    "base-papers1-43-isv.tex": (
        1_894_721,
        "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
V4_PIN = (
    34_849,
    "A63A6F697A99F5A8D64C0B69D24875C3031C8EFE7DE8A137DE8F844CD460E341",
)
AUDIT_SCRIPT_PIN = (
    27_831,
    "19F3AC0B759B89E77A7C5B25A1CDF8605DC9DF1BB5BFFF3F0BC05E559C954476",
)
MANIFEST_PIN = (
    3_505_137,
    "E7B8CDE438E9B72A61F6FA3AE0422AF6CBFBCBB7965E139BD123709CC1EEF818",
)
MANIFEST_INTERNAL = (
    "96CE41A7C076142F36697B93004E7A4F92BF0B90296C0A265B0A32CA99A29DBC"
)
EXPECTED_DISPOSITIONS = {
    "unprotected_style_payloads": {
        "KEEP_PROJECTABLE_INTERSLAVIC_STYLE_PAYLOAD": 731,
        "PROTECT_COMPLETE_ORIGINAL_LANGUAGE_STYLE_PAYLOAD": 152,
    },
    "unprotected_name_candidates": {
        "KEEP_PROJECTABLE_INTEGRATED_OR_NONNAME_CANDIDATE": 374,
        "PROTECT_COMPLETE_UNINFLECTED_IDENTITY": 242,
    },
    "unprotected_foreign_lexicon_hits": {
        "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT": 1_346,
        "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN": 1_025,
    },
    "visible_one_letter_tokens": {
        "PRESERVE_COVERED_BY_ALLOWED_LETTER_FOREIGN_RANGE": 19,
        "PRESERVE_DOTTED_INITIAL_OR_ROMAN_ORDINAL": 32,
        "PRESERVE_FOREIGN_INITIAL_OR_CITATION_ABBREVIATION": 32,
        "PRESERVE_STRUCTURAL_ROMAN_LABEL": 158,
        "PROJECT_LEXICAL_INTERSLAVIC_WORD": 449,
    },
}
VISIBLE_ROLES = frozenset({"visible_prose", "visible_math_text", "visible_metadata"})


class ProjectionV5Error(RuntimeError):
    pass


_LINE_TABLE_CACHE: dict[int, tuple[str, tuple[list[int], list[int], list[str]]]] = {}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProjectionV5Error(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def describe(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def read_regular(path: Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as error:
        raise ProjectionV5Error(f"cannot stat {label}: {path}") from error
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink(), f"unsafe {label}: {path}")
    try:
        return path.read_bytes()
    except OSError as error:
        raise ProjectionV5Error(f"cannot read {label}: {path}") from error


def read_exact(path: Path, pin: tuple[int, str], label: str) -> bytes:
    raw = read_regular(path, label)
    require((len(raw), sha256(raw)) == pin, f"{label} pin drift: {describe(raw)}")
    return raw


def reject_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(raw: bytes, label: str) -> Any:
    require(not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, f"transport drift: {label}")
    require(raw.endswith(b"\n") and not raw.endswith(b"\n\n"), f"terminal LF drift: {label}")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectionV5Error(f"invalid JSON: {label}: {error}") from error


def load_v4() -> Any:
    read_exact(V4_PATH, V4_PIN, "v4 predecessor")
    spec = importlib.util.spec_from_file_location("isv019_cyr_v4_for_v5", V4_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v4 predecessor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_manifest() -> dict[str, Any]:
    read_exact(AUDIT_SCRIPT_PATH, AUDIT_SCRIPT_PIN, "completeness audit implementation")
    raw = read_exact(MANIFEST_PATH, MANIFEST_PIN, "completeness manifest")
    value = strict_json(raw, str(MANIFEST_PATH))
    require(isinstance(value, dict), "manifest root must be an object")
    require(
        value.get("schema") == "noether-isv-final-projection-completeness-inventory-v1",
        "manifest schema drift",
    )
    claimed = value.get("inventory_sha256_excluding_this_field")
    without = copy.deepcopy(value)
    without.pop("inventory_sha256_excluding_this_field", None)
    require(claimed == MANIFEST_INTERNAL, "manifest embedded hash drift")
    require(sha256(canonical_json(without)) == MANIFEST_INTERNAL, "manifest internal hash mismatch")
    require(value.get("scope", {}).get("sealed_head") == "ISV019-EDIT-0171", "manifest head drift")
    require(tuple(value.get("scope", {}).get("source_order", ())) == SOURCE_ORDER, "manifest source order drift")
    for key, expected in EXPECTED_DISPOSITIONS.items():
        observed = value.get("summaries", {}).get(key, {}).get("by_disposition")
        require(observed == expected, f"manifest disposition drift: {key}: {observed}")
    return value


def source_raws(source_dir: Path = SOURCE_DIR) -> dict[str, bytes]:
    raws: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        raw = read_exact(source_dir / filename, SOURCE_PINS[filename], filename)
        raws[filename] = raw
    return raws


def validate_row(v2: Any, text: str, row: dict[str, Any], filename: str) -> tuple[int, int]:
    require(row.get("file") == filename, f"manifest file partition drift: {filename}")
    span = row.get("scalar_span")
    require(
        isinstance(span, list)
        and len(span) == 2
        and all(isinstance(item, int) for item in span),
        f"invalid scalar span: {filename}",
    )
    start, end = span
    require(0 <= start < end <= len(text), f"out-of-range scalar span: {filename}:{span}")
    surface = row.get("surface")
    require(isinstance(surface, str) and text[start:end] == surface, f"surface drift: {filename}:{span}")
    require(sha256(surface.encode("utf-8")) == row.get("surface_sha256"), f"surface hash drift: {filename}:{span}")
    cache_key = id(text)
    cached = _LINE_TABLE_CACHE.get(cache_key)
    if cached is None or cached[0] is not text:
        cached = (text, v2.line_tables(text))
        _LINE_TABLE_CACHE[cache_key] = cached
    scalar_starts, byte_starts, lines = cached[1]
    observed = v2.locator(text, start, scalar_starts, byte_starts, lines)
    for key in ("line", "column", "byte_offset", "line_sha256", "context_sha256"):
        require(observed[key] == row.get(key), f"locator drift {key}: {filename}:{span}")
    return start, end


def selected_manifest_ranges(
    v2: Any, manifest: dict[str, Any], texts: Mapping[str, str]
) -> tuple[dict[str, list[tuple[int, int, str]]], dict[str, Any]]:
    categories = (
        "unprotected_style_payloads",
        "unprotected_name_candidates",
        "unprotected_foreign_lexicon_hits",
        "visible_one_letter_tokens",
    )
    selected: dict[str, list[tuple[int, int, str]]] = {name: [] for name in SOURCE_ORDER}
    selection_counts: Counter[str] = Counter()
    all_counts: Counter[str] = Counter()
    for category in categories:
        rows = manifest.get(category)
        require(isinstance(rows, list), f"manifest category missing: {category}")
        for row in rows:
            filename = row.get("file")
            require(filename in texts, f"unknown manifest source: {filename}")
            start, end = validate_row(v2, texts[filename], row, filename)
            disposition = row.get("disposition")
            require(isinstance(disposition, str), f"missing disposition: {category}")
            all_counts[disposition] += 1
            if disposition.startswith(("PROTECT", "PRESERVE")):
                selected[filename].append((start, end, f"manifest:{category}:{disposition}"))
                selection_counts[disposition] += 1
    return selected, {
        "all_dispositions": dict(sorted(all_counts.items())),
        "selected_dispositions": dict(sorted(selection_counts.items())),
        "selected_occurrences_before_union": sum(selection_counts.values()),
    }


def structural_ranges(
    v4: Any,
    v2: Any,
    raws: Mapping[str, bytes],
    texts: Mapping[str, str],
) -> tuple[dict[str, list[tuple[int, int, str]]], dict[str, Any]]:
    head = v4.validate_head_sources(raws, STATE_PATH)
    report = v4.scan_raws(raws, head_validation=head)
    summary = report["summary"]
    require(summary["status"] == "READY_IN_MEMORY_ONLY", "v4 predecessor not ready")
    require(summary["blocked_occurrences"] == 0, "v4 predecessor blockers remain")
    require(summary["approved_structural_identities"] == 722, "v4 structural count drift")
    result: dict[str, list[tuple[int, int, str]]] = {name: [] for name in SOURCE_ORDER}
    issues: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        scanned = v2.scan_text(texts[filename], filename)
        for issue in scanned["issues"]:
            require(v4.structural_issue(issue), f"v4-approved source has nonstructural issue: {issue}")
            start = issue["scalar_offset"]
            end = start + len(issue["token"])
            require(texts[filename][start:end] == issue["token"], f"structural surface drift: {filename}")
            result[filename].append((start, end, "v4:reviewed_structural_identity"))
            issues.append(issue)
    require(len(issues) == 722, f"structural issue census drift: {len(issues)}")
    return result, {
        "head_validation": head,
        "v4_report_sha256_excluding_this_field": report["report_sha256_excluding_this_field"],
        "approved_occurrences": len(issues),
        "inventory_sha256": v2.issue_inventory_sha256(issues),
    }


def union_ranges(
    text: str, ranges: Sequence[tuple[int, int, str]], label: str
) -> tuple[list[tuple[int, int]], dict[str, Any]]:
    ordered = sorted((start, end) for start, end, _reason in ranges)
    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        require(0 <= start < end <= len(text), f"range out of bounds: {label}:{start}:{end}")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    stream = "".join(text[start:end] for start, end in merged).encode("utf-8")
    rows = [[start, end, sha256(text[start:end].encode("utf-8"))] for start, end in merged]
    return merged, {
        "input_occurrences": len(ranges),
        "union_ranges": len(merged),
        "protected_scalars": sum(end - start for start, end in merged),
        "protected_stream": describe(stream),
        "range_manifest_sha256": sha256(canonical_json(rows)),
    }


def split_segments(v2: Any, text: str, ranges: Sequence[tuple[int, int]]) -> tuple[Any, ...]:
    original = v2.TexSegmenter(text).segment()
    builder = v2.SegmentBuilder()
    range_index = 0
    for segment in original:
        cursor = segment.start
        while range_index < len(ranges) and ranges[range_index][1] <= segment.start:
            range_index += 1
        local_index = range_index
        while local_index < len(ranges) and ranges[local_index][0] < segment.end:
            left, right = ranges[local_index]
            overlap_start = max(segment.start, left)
            overlap_end = min(segment.end, right)
            if cursor < overlap_start:
                builder.add(cursor, overlap_start, segment.role, segment.detail)
            if overlap_start < overlap_end:
                require(segment.role in VISIBLE_ROLES or segment.role.startswith("protected"), f"manifest range crosses unsafe role: {segment}")
                builder.add(
                    overlap_start,
                    overlap_end,
                    "protected_identity_arg",
                    "v5_reviewed_projection_role_manifest",
                )
                cursor = overlap_end
            local_index += 1
        if cursor < segment.end:
            builder.add(cursor, segment.end, segment.role, segment.detail)
    return builder.finish(len(text))


def project_with_trace(
    v2: Any, text: str, segments: Sequence[Any], label: str
) -> tuple[str, Counter[str], list[dict[str, Any]]]:
    output: list[str] = []
    conversions: Counter[str] = Counter()
    protected: list[dict[str, Any]] = []
    output_cursor = 0
    for segment in segments:
        raw = text[segment.start : segment.end]
        if segment.role not in VISIBLE_ROLES:
            chunk = raw
        else:
            parts: list[str] = []
            local_cursor = 0
            for match in v2.LETTER_RE.finditer(raw):
                parts.append(raw[local_cursor : match.start()])
                word = match.group(0)
                reasons = v2.token_block_reasons(word)
                require(not reasons, f"trace projection issue: {label}:{word}:{reasons}")
                converted, classification = v2.project_word(word)
                parts.append(converted)
                conversions[classification] += 1
                local_cursor = match.end()
            parts.append(raw[local_cursor:])
            chunk = "".join(parts)
        output.append(chunk)
        if segment.detail == "v5_reviewed_projection_role_manifest":
            protected.append(
                {
                    "input_span": [segment.start, segment.end],
                    "output_span": [output_cursor, output_cursor + len(chunk)],
                    "surface_sha256": sha256(chunk.encode("utf-8")),
                }
            )
        output_cursor += len(chunk)
    return "".join(output), conversions, protected


def merge_output_spans(rows: Sequence[dict[str, Any]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for row in rows:
        start, end = row["output_span"]
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def latin_visible_residuals(
    v2: Any,
    output_text: str,
    protected_output_ranges: Sequence[tuple[int, int]],
    label: str,
) -> list[dict[str, Any]]:
    residuals: list[dict[str, Any]] = []
    scalar_starts, byte_starts, lines = v2.line_tables(output_text)
    for segment in v2.TexSegmenter(output_text).segment():
        if segment.role not in VISIBLE_ROLES:
            continue
        raw = output_text[segment.start : segment.end]
        for match in v2.LETTER_RE.finditer(raw):
            token = match.group(0)
            if not any("LATIN" in unicodedata.name(char, "") for char in token):
                continue
            start = segment.start + match.start()
            end = segment.start + match.end()
            require(
                any(left <= start and end <= right for left, right in protected_output_ranges),
                f"unmanifested visible Latin residual: {label}:{token}:{start}",
            )
            residuals.append(
                {
                    "token": token,
                    "token_sha256": sha256(token.encode("utf-8")),
                    "scalar_span": [start, end],
                    "role": segment.role,
                    **v2.locator(
                        output_text, start, scalar_starts, byte_starts, lines
                    ),
                }
            )
    return residuals


def project_raws(raws: Mapping[str, bytes]) -> tuple[dict[str, Any], dict[str, bytes]]:
    require(set(raws) == set(SOURCE_ORDER), "source topology drift")
    for filename in SOURCE_ORDER:
        require((len(raws[filename]), sha256(raws[filename])) == SOURCE_PINS[filename], f"source pin drift: {filename}")
    v4 = load_v4()
    v2 = v4.load_v2()
    manifest = validate_manifest()
    texts = {filename: v2.strict_transport(raws[filename], filename) for filename in SOURCE_ORDER}
    manifest_ranges, selection = selected_manifest_ranges(v2, manifest, texts)
    approved_ranges, structural = structural_ranges(v4, v2, raws, texts)

    projected: dict[str, bytes] = {}
    files: list[dict[str, Any]] = []
    total_conversions: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        all_ranges = manifest_ranges[filename] + approved_ranges[filename]
        merged, protection = union_ranges(texts[filename], all_ranges, filename)
        segments = split_segments(v2, texts[filename], merged)
        output_text, issues, conversions, issue_types = v2.project_segments(
            texts[filename], segments, filename
        )
        require(not issues and not issue_types, f"projection issue remains: {filename}: {issues[:1]}")
        traced_text, traced_conversions, trace_rows = project_with_trace(
            v2, texts[filename], segments, filename
        )
        require(traced_text == output_text, f"independent trace output drift: {filename}")
        require(traced_conversions == conversions, f"independent trace conversion drift: {filename}")
        protected_output_ranges = merge_output_spans(trace_rows)
        residuals = latin_visible_residuals(
            v2, output_text, protected_output_ranges, filename
        )
        trace_raw = canonical_json(trace_rows)
        residual_raw = canonical_json(residuals)
        structure = v2.validate_structure(output_text)
        output_raw = output_text.encode("utf-8")
        require(output_raw.endswith(b"\n") and b"\r" not in output_raw, f"output transport drift: {filename}")
        projected[filename] = output_raw
        total_conversions.update(conversions)
        files.append(
            {
                "source": filename,
                "output": OUTPUT_NAMES[filename],
                "input": describe(raws[filename]),
                "output_identity": describe(output_raw),
                "input_scalars": len(texts[filename]),
                "output_scalars": len(output_text),
                "segments": len(segments),
                "segment_sha256": v2.segment_digest(segments),
                "protection": protection,
                "conversion_classes": dict(sorted(conversions.items())),
                "projection_issues": 0,
                "output_role_trace": {
                    "fragments": len(trace_rows),
                    "union_ranges": len(protected_output_ranges),
                    "bytes": len(trace_raw),
                    "sha256": sha256(trace_raw),
                },
                "visible_latin_residuals": {
                    "occurrences": len(residuals),
                    "unique_surfaces": len({row["token"] for row in residuals}),
                    "by_surface": dict(
                        sorted(Counter(row["token"] for row in residuals).items())
                    ),
                    "bytes": len(residual_raw),
                    "sha256": sha256(residual_raw),
                    "all_covered_by_reviewed_output_ranges": True,
                },
                "structure": structure,
            }
        )
    output_manifest = [
        {"file": OUTPUT_NAMES[name], **describe(projected[name])} for name in SOURCE_ORDER
    ]
    report: dict[str, Any] = {
        "schema": "noether-isv-cyrillic-projection-v5-report-v1",
        "status": "READY_DETERMINISTIC_DERIVATION_IN_MEMORY",
        "classification": "deterministic script projection of one Interslavic edition; not an independent translation witness",
        "source_order": list(SOURCE_ORDER),
        "dependencies": {
            "v4_predecessor": {"path": V4_PATH.name, "bytes": V4_PIN[0], "sha256": V4_PIN[1]},
            "completeness_audit": {"path": AUDIT_SCRIPT_PATH.name, "bytes": AUDIT_SCRIPT_PIN[0], "sha256": AUDIT_SCRIPT_PIN[1]},
            "role_manifest": {"path": str(MANIFEST_PATH.relative_to(ROOT)), "bytes": MANIFEST_PIN[0], "sha256": MANIFEST_PIN[1], "internal_sha256": MANIFEST_INTERNAL},
        },
        "selection": selection,
        "structural_policy": structural,
        "files": files,
        "output_manifest": output_manifest,
        "output_manifest_sha256": sha256(canonical_json(output_manifest)),
        "conversion_classes": dict(sorted(total_conversions.items())),
        "projection_issues": 0,
        "limitations": [
            "The Latin source vector is authenticated but not frozen by this projector.",
            "A clean derivation does not substitute for TeX build, text, math, font, link, or visual QA.",
            "No native-speaker, community, or external peer-review certification is claimed.",
        ],
    }
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    return report, projected


def project_corpus(source_dir: Path = SOURCE_DIR) -> tuple[dict[str, Any], dict[str, bytes]]:
    return project_raws(source_raws(source_dir))


def write_outputs(output_dir: Path, projected: Mapping[str, bytes]) -> list[dict[str, Any]]:
    require(output_dir.exists() and output_dir.is_dir() and not output_dir.is_symlink(), f"unsafe output directory: {output_dir}")
    targets = {name: output_dir / OUTPUT_NAMES[name] for name in SOURCE_ORDER}
    for name, target in targets.items():
        if target.exists():
            require(target.is_file() and not target.is_symlink(), f"unsafe existing output: {target}")
            require(target.read_bytes() == projected[name], f"refusing to overwrite non-identical output: {target}")
    installed: list[Path] = []
    try:
        for ordinal, name in enumerate(SOURCE_ORDER, 1):
            target = targets[name]
            if target.exists():
                continue
            stage = output_dir / f".{target.name}.v5-stage-{os.getpid()}-{ordinal}"
            require(not stage.exists(), f"stage collision: {stage}")
            try:
                with stage.open("xb") as handle:
                    handle.write(projected[name])
                    handle.flush()
                    os.fsync(handle.fileno())
                require(stage.read_bytes() == projected[name], f"stage readback mismatch: {stage}")
                os.replace(stage, target)
                require(target.read_bytes() == projected[name], f"install readback mismatch: {target}")
                installed.append(target)
            finally:
                if stage.exists():
                    stage.unlink()
    except Exception:
        for target in reversed(installed):
            if target.exists() and target.read_bytes() in projected.values():
                target.unlink()
        raise
    return [
        {"path": str(target), **describe(target.read_bytes())}
        for target in targets.values()
    ]


def compact(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: report[key]
        for key in (
            "schema", "status", "classification", "source_order", "dependencies",
            "selection", "structural_policy", "output_manifest",
            "output_manifest_sha256", "conversion_classes", "projection_issues",
            "limitations", "report_sha256_excluding_this_field",
        )
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--full-report", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--write-output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report, projected = project_corpus(args.source_dir)
        payload = report if args.full_report else compact(report)
        if args.write_output is not None:
            payload = copy.deepcopy(payload)
            payload["installed_outputs"] = write_outputs(args.write_output, projected)
    except Exception as error:
        failure = {
            "schema": "noether-isv-cyrillic-projection-v5-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        return 1
    sys.stdout.buffer.write(canonical_json(payload))
    if args.require_ready and report["status"] != "READY_DETERMINISTIC_DERIVATION_IN_MEMORY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
