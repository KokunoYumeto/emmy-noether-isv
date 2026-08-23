#!/usr/bin/env python3
"""Fail-closed NOETHER-ISV-v020 Latin-to-Cyrillic projector.

The four Latin sources are unchanged from the public v019 release.  This
successor pins the complete v019 v6 implementation chain, replaces only its
role-policy manifest with the exhaustively reviewed v020 manifest, adds the
eight source-bound identity spans absent from the predecessor inventory, and
retains v6's TeX-dimension protection.  Every corrected disposition is audited
against the actual output, and every v019-to-v020 changed line must be licensed
by a reviewed correction locator.  Default execution is read-only.
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
import sys
from typing import Any, Callable, Mapping, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
PRED = ROOT / "predecessor_v019"
SOURCE_DIR = ROOT / "source_latin"
OUTPUT_DIR = ROOT / "source_cyrillic"
V6_PATH = PRED / "project_isv_cyrillic_v6.py"
MANIFEST_PATH = ROOT / "decision_records/ISV020-REVIEWED-PROJECTION-ROLE-MANIFEST.json"
OLD_OUTPUT_DIR = PRED / "source_cyrillic"

V6_PIN = (
    13_333,
    "C7AE344B1E01DC0A8B655067173B66550D93E4D357CEB4FDB9713E80F9B9C0D6",
)
MANIFEST_PIN = (
    3_577_349,
    "192BAE284EDC9BBA4A458EEBA9F7541CE16CA377A68668A70F5CFD0A2E182462",
)
MANIFEST_INTERNAL = "90EAFFEA8C2B8C17E301CCA94F80029CD1A3454E514EA3B3390376C300FDBCDE"

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
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
OUTPUT_NAMES = {
    "44-book-isv.tex": "44-book-isv-cyrl.tex",
    "45-isv.tex": "45-isv-cyrl.tex",
    "base-papers1-43-isv.tex": "base-papers1-43-isv-cyrl.tex",
    "bib-isv.tex": "bib-isv-cyrl.tex",
}
OLD_OUTPUT_PINS = {
    "44-book-isv-cyrl.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "45-isv-cyrl.tex": (
        35_902,
        "E1568BAB1E389E07816178A2FBDEE3833508C79BF0C7C19DD5120812E24646FE",
    ),
    "base-papers1-43-isv-cyrl.tex": (
        2_706_660,
        "23C242AABD938C605A4B2293ED6E68B723F94DBD23279FD8E75CB50CAEF099F1",
    ),
    "bib-isv-cyrl.tex": (
        13_255,
        "5A6AE75FF94360BC104CE240E0EC18A2329C5229F68B198F763EDF7E786B816B",
    ),
}
CATEGORIES = (
    "unprotected_style_payloads",
    "unprotected_name_candidates",
    "unprotected_foreign_lexicon_hits",
    "visible_one_letter_tokens",
)
CATEGORY_COUNTS = {
    "unprotected_style_payloads": 883,
    "unprotected_name_candidates": 616,
    "unprotected_foreign_lexicon_hits": 2_371,
    "visible_one_letter_tokens": 690,
}
EXPECTED_DISPOSITIONS = {
    "unprotected_style_payloads": {
        "KEEP_PROJECTABLE_INTERSLAVIC_STYLE_PAYLOAD": 730,
        "PROTECT_COMPLETE_ORIGINAL_LANGUAGE_STYLE_PAYLOAD": 153,
    },
    "unprotected_name_candidates": {
        "KEEP_PROJECTABLE_INTEGRATED_OR_NONNAME_CANDIDATE": 374,
        "PROTECT_COMPLETE_UNINFLECTED_IDENTITY": 242,
    },
    "unprotected_foreign_lexicon_hits": {
        "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT": 1_126,
        "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN": 1_245,
    },
    "visible_one_letter_tokens": {
        "PRESERVE_COVERED_BY_ALLOWED_LETTER_FOREIGN_RANGE": 19,
        "PRESERVE_DOTTED_INITIAL_OR_ROMAN_ORDINAL": 32,
        "PRESERVE_FOREIGN_INITIAL_OR_CITATION_ABBREVIATION": 32,
        "PRESERVE_STRUCTURAL_ROMAN_LABEL": 249,
        "PROJECT_LEXICAL_INTERSLAVIC_WORD": 358,
    },
}
EXPECTED_REVIEWED_RECORDS = 4_560
EXPECTED_CLASSIFICATION_CORRECTIONS = 364
EXPECTED_ADDITIONAL_SPANS = 8
EXPECTED_TOTAL_CORRECTIONS = 372
EXPECTED_EFFECT_MODES = {"preserve": 346, "project": 26}


class ProjectionV7Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProjectionV7Error(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def describe(raw: bytes) -> dict[str, Any]:
    return {"bytes": len(raw), "sha256": sha256(raw)}


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(raw: bytes, label: str) -> Any:
    require(raw.endswith(b"\n") and b"\r" not in raw, f"transport drift: {label}")
    require(not raw.startswith(b"\xef\xbb\xbf"), f"BOM not allowed: {label}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)


def read_regular(path: Path, label: str) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe {label}: {path}")
    return path.read_bytes()


def read_exact(path: Path, pin: tuple[int, str], label: str) -> bytes:
    raw = read_regular(path, label)
    require((len(raw), sha256(raw)) == pin, f"pin drift: {label}")
    return raw


def load_v6() -> Any:
    read_exact(V6_PATH, V6_PIN, "v019 v6 predecessor projector")
    spec = importlib.util.spec_from_file_location("isv020_v019_v6", V6_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v6")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_raws(source_dir: Path = SOURCE_DIR) -> dict[str, bytes]:
    require(source_dir.resolve() == SOURCE_DIR.resolve(), "source directory must be exact v020 source_latin")
    return {
        filename: read_exact(source_dir / filename, SOURCE_PINS[filename], filename)
        for filename in SOURCE_ORDER
    }


def validate_manifest() -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    raw = read_exact(MANIFEST_PATH, MANIFEST_PIN, "v020 reviewed role manifest")
    value = strict_json(raw, str(MANIFEST_PATH))
    require(isinstance(value, dict), "manifest root must be an object")
    require(value.get("schema") == "noether-isv-reviewed-projection-role-manifest/2.0", "manifest schema drift")
    require(value.get("status") == "FULLY_REVIEWED_ZERO_AMBIGUITY_BINDING_RELEASE_GATE", "manifest status drift")
    claimed = value.get("inventory_sha256_excluding_this_field")
    without = copy.deepcopy(value)
    without.pop("inventory_sha256_excluding_this_field", None)
    require(claimed == MANIFEST_INTERNAL, "manifest embedded digest drift")
    require(sha256(canonical_json(without)) == MANIFEST_INTERNAL, "manifest internal digest mismatch")
    scope = value.get("scope", {})
    require(scope.get("successor_release") == "NOETHER-ISV-v020", "manifest successor drift")
    require(scope.get("latin_source_bytes_changed") == 0, "manifest permits a Latin source change")
    require(tuple(scope.get("source_order", ())) == SOURCE_ORDER, "manifest source order drift")
    review = value.get("review", {})
    require(review.get("review_status") == "FULL_INDEPENDENT_REVIEW_COMPLETE", "review status drift")
    require(review.get("records_reviewed") == EXPECTED_REVIEWED_RECORDS, "reviewed-record count drift")
    require(review.get("classification_defects_corrected") == EXPECTED_CLASSIFICATION_CORRECTIONS, "classification-correction count drift")
    require(review.get("coverage_defects_corrected") == EXPECTED_ADDITIONAL_SPANS, "coverage-correction count drift")
    require(review.get("defects_corrected") == EXPECTED_TOTAL_CORRECTIONS, "total-correction count drift")
    require(review.get("ambiguities") == 0, "manifest has unresolved ambiguity")

    corrected: list[dict[str, Any]] = []
    seen_corrections: set[tuple[Any, ...]] = set()
    for category in CATEGORIES:
        rows = value.get(category)
        require(isinstance(rows, list) and len(rows) == CATEGORY_COUNTS[category], f"category count drift: {category}")
        observed = dict(sorted(Counter(row.get("disposition") for row in rows).items()))
        require(observed == EXPECTED_DISPOSITIONS[category], f"category disposition drift: {category}: {observed}")
        for index, row in enumerate(rows):
            require(isinstance(row, dict), f"non-object manifest row: {category}:{index}")
            correction = row.get("review_correction")
            if correction is None:
                continue
            require(correction.get("successor") == "NOETHER-ISV-v020", f"correction successor drift: {category}:{index}")
            require(correction.get("category_index0") == index, f"correction index drift: {category}:{index}")
            key = (category, index, row.get("file"), *row.get("scalar_span", []))
            require(key not in seen_corrections, f"duplicate correction: {key}")
            seen_corrections.add(key)
            corrected.append({"category": category, "category_index0": index, **row})
    require(len(corrected) == EXPECTED_CLASSIFICATION_CORRECTIONS, "corrected-row census drift")
    additions = value.get("additional_protected_spans")
    require(isinstance(additions, list) and len(additions) == EXPECTED_ADDITIONAL_SPANS, "additional-span census drift")
    for index, row in enumerate(additions):
        require(row.get("disposition") == "PROTECT_COMPLETE_UNINFLECTED_IDENTITY", f"additional disposition drift: {index}")
    return value, raw, corrected


def patched_v5(v6: Any, manifest: dict[str, Any]) -> tuple[Any, Callable[..., Any]]:
    v5 = v6.load_v5()
    base_selector = v5.selected_manifest_ranges

    def manifest_override() -> dict[str, Any]:
        return copy.deepcopy(manifest)

    def reviewed_selector(v2: Any, supplied: dict[str, Any], texts: Mapping[str, str]):
        require(supplied.get("inventory_sha256_excluding_this_field") == MANIFEST_INTERNAL, "selector received wrong manifest")
        selected, selection = base_selector(v2, supplied, texts)
        all_counts = Counter(selection["all_dispositions"])
        selected_counts = Counter(selection["selected_dispositions"])
        for ordinal, row in enumerate(supplied["additional_protected_spans"], 1):
            filename = row.get("file")
            require(filename in texts, f"unknown additional-span source: {ordinal}")
            start, end = v5.validate_row(v2, texts[filename], row, filename)
            disposition = row.get("disposition")
            require(disposition == "PROTECT_COMPLETE_UNINFLECTED_IDENTITY", f"additional-span disposition drift: {ordinal}")
            selected[filename].append((start, end, f"manifest:additional_protected_spans:{disposition}"))
            all_counts[disposition] += 1
            selected_counts[disposition] += 1
        result = copy.deepcopy(selection)
        result["all_dispositions"] = dict(sorted(all_counts.items()))
        result["selected_dispositions"] = dict(sorted(selected_counts.items()))
        result["selected_occurrences_before_union"] += EXPECTED_ADDITIONAL_SPANS
        result["additional_protected_spans"] = EXPECTED_ADDITIONAL_SPANS
        return selected, result

    v5.validate_manifest = manifest_override
    v5.selected_manifest_ranges = reviewed_selector
    return v5, reviewed_selector


def project_visible(v2: Any, raw: str, label: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in v2.LETTER_RE.finditer(raw):
        parts.append(raw[cursor : match.start()])
        word = match.group(0)
        reasons = v2.token_block_reasons(word)
        require(not reasons, f"effect-audit projection issue: {label}:{word}:{reasons}")
        converted, _classification = v2.project_word(word)
        parts.append(converted)
        cursor = match.end()
    parts.append(raw[cursor:])
    return "".join(parts)


def effect_audit(
    v6: Any,
    v5: Any,
    reviewed_selector: Callable[..., Any],
    manifest: dict[str, Any],
    corrected: Sequence[dict[str, Any]],
    raws: Mapping[str, bytes],
    projected: Mapping[str, bytes],
) -> dict[str, Any]:
    v4 = v5.load_v4()
    v2 = v4.load_v2()
    texts = {filename: v2.strict_transport(raws[filename], filename) for filename in SOURCE_ORDER}
    manifest_ranges, selection = reviewed_selector(v2, manifest, texts)
    dimensions, dimension_evidence = v6.dimension_inventory(v5, v2, texts)
    structural_ranges, _structural = v5.structural_ranges(v4, v2, raws, texts)
    for filename in SOURCE_ORDER:
        manifest_ranges[filename].extend(dimensions[filename])

    protected_maps: dict[str, list[dict[str, Any]]] = {}
    word_maps: dict[str, dict[tuple[int, int], tuple[int, int, str]]] = {}
    for filename in SOURCE_ORDER:
        merged, _protection = v5.union_ranges(
            texts[filename], manifest_ranges[filename] + structural_ranges[filename], filename
        )
        segments = v5.split_segments(v2, texts[filename], merged)
        output_text = projected[filename].decode("utf-8")
        rebuilt: list[str] = []
        output_cursor = 0
        protected_maps[filename] = []
        word_maps[filename] = {}
        for segment in segments:
            raw = texts[filename][segment.start : segment.end]
            if segment.role in v5.VISIBLE_ROLES:
                parts: list[str] = []
                local_cursor = 0
                local_output_cursor = output_cursor
                for match in v2.LETTER_RE.finditer(raw):
                    prefix = raw[local_cursor : match.start()]
                    parts.append(prefix)
                    local_output_cursor += len(prefix)
                    word = match.group(0)
                    reasons = v2.token_block_reasons(word)
                    require(not reasons, f"effect map projection issue: {filename}:{word}:{reasons}")
                    converted, _classification = v2.project_word(word)
                    absolute_span = (segment.start + match.start(), segment.start + match.end())
                    require(absolute_span not in word_maps[filename], f"duplicate projected word span: {filename}:{absolute_span}")
                    word_maps[filename][absolute_span] = (
                        local_output_cursor,
                        local_output_cursor + len(converted),
                        converted,
                    )
                    parts.append(converted)
                    local_output_cursor += len(converted)
                    local_cursor = match.end()
                parts.append(raw[local_cursor:])
                chunk = "".join(parts)
            else:
                chunk = raw
                if segment.detail == "v5_reviewed_projection_role_manifest":
                    protected_maps[filename].append(
                        {
                            "input_span": (segment.start, segment.end),
                            "output_span": (output_cursor, output_cursor + len(chunk)),
                        }
                    )
            rebuilt.append(chunk)
            output_cursor += len(chunk)
        require("".join(rebuilt) == output_text, f"effect-audit rebuild drift: {filename}")

    effect_rows: list[dict[str, Any]] = []
    modes: Counter[str] = Counter()
    all_rows = list(corrected) + [
        {"category": "additional_protected_spans", "category_index0": index, **row}
        for index, row in enumerate(manifest["additional_protected_spans"])
    ]
    for row in all_rows:
        filename = row["file"]
        start, end = row["scalar_span"]
        source_surface = texts[filename][start:end]
        require(source_surface == row["surface"], f"effect source surface drift: {filename}:{start}:{end}")
        disposition = row["disposition"]
        preserve = disposition.startswith(("PROTECT", "PRESERVE"))
        if preserve:
            covering = [
                segment
                for segment in protected_maps[filename]
                if segment["input_span"][0] <= start and end <= segment["input_span"][1]
            ]
            require(len(covering) == 1, f"protected effect not uniquely covered: {filename}:{start}:{end}")
            segment = covering[0]
            output_start = segment["output_span"][0] + start - segment["input_span"][0]
            output_end = output_start + (end - start)
            observed = projected[filename].decode("utf-8")[output_start:output_end]
            require(observed == source_surface, f"preservation effect drift: {filename}:{start}:{end}")
            mode = "preserve"
        else:
            require((start, end) in word_maps[filename], f"projectable correction swallowed or non-word: {filename}:{start}:{end}")
            output_start, output_end, expected = word_maps[filename][(start, end)]
            observed = projected[filename].decode("utf-8")[output_start:output_end]
            require(observed == expected, f"projection effect drift: {filename}:{start}:{end}")
            require(observed != source_surface, f"projectable correction had no script effect: {filename}:{start}:{end}")
            mode = "project"
        modes[mode] += 1
        effect_rows.append(
            {
                "category": row["category"],
                "category_index0": row["category_index0"],
                "file": filename,
                "line": row["line"],
                "column": row["column"],
                "surface": source_surface,
                "disposition": disposition,
                "mode": mode,
                "observed_output_sha256": sha256(observed.encode("utf-8")),
            }
        )
    require(dict(sorted(modes.items())) == EXPECTED_EFFECT_MODES, f"effect-mode census drift: {modes}")
    effect_raw = canonical_json(effect_rows)
    return {
        "status": "PASS_ALL_REVIEWED_CORRECTIONS_CONSUMED",
        "classification_corrections": len(corrected),
        "coverage_spans": EXPECTED_ADDITIONAL_SPANS,
        "effects_verified": len(effect_rows),
        "by_mode": dict(sorted(modes.items())),
        "effect_inventory": describe(effect_raw),
        "selected_occurrences_before_union_excluding_dimensions": selection["selected_occurrences_before_union"],
        "tex_dimension_occurrences": dimension_evidence["occurrences"],
        "unverified_corrections": 0,
        "projectable_corrections_swallowed_by_protection": 0,
    }


def delta_audit(
    manifest: Mapping[str, Any],
    corrected: Sequence[Mapping[str, Any]],
    projected: Mapping[str, bytes],
) -> dict[str, Any]:
    allowed: dict[str, set[int]] = {filename: set() for filename in SOURCE_ORDER}
    for row in list(corrected) + list(manifest["additional_protected_spans"]):
        allowed[row["file"]].add(row["line"])
    changed_rows: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        output_name = OUTPUT_NAMES[filename]
        old_raw = read_exact(OLD_OUTPUT_DIR / output_name, OLD_OUTPUT_PINS[output_name], f"frozen v019 output {output_name}")
        new_raw = projected[filename]
        old_lines = old_raw.splitlines(keepends=True)
        new_lines = new_raw.splitlines(keepends=True)
        require(len(old_lines) == len(new_lines), f"line topology drift: {filename}")
        local_changed = 0
        for line_number, (old_line, new_line) in enumerate(zip(old_lines, new_lines), 1):
            if old_line == new_line:
                continue
            require(line_number in allowed[filename], f"unlicensed changed line: {filename}:{line_number}")
            local_changed += 1
            changed_rows.append(
                {
                    "file": filename,
                    "line": line_number,
                    "old_line": describe(old_line),
                    "new_line": describe(new_line),
                }
            )
        files.append(
            {
                "source": filename,
                "output": output_name,
                "v019": describe(old_raw),
                "v020": describe(new_raw),
                "size_delta": len(new_raw) - len(old_raw),
                "lines": len(old_lines),
                "allowed_changed_lines": len(allowed[filename]),
                "actual_changed_lines": local_changed,
            }
        )
    require(changed_rows, "v020 unexpectedly identical to defective v019 outputs")
    changed_raw = canonical_json(changed_rows)
    return {
        "status": "PASS_ALL_CHANGES_WITHIN_REVIEWED_LOCATORS",
        "allowed_changed_lines": sum(len(rows) for rows in allowed.values()),
        "actual_changed_lines": len(changed_rows),
        "unlicensed_changed_lines": 0,
        "changed_line_inventory": describe(changed_raw),
        "files": files,
    }


def project_raws(raws: Mapping[str, bytes]) -> tuple[dict[str, Any], dict[str, bytes]]:
    require(set(raws) == set(SOURCE_ORDER), "source topology drift")
    for filename in SOURCE_ORDER:
        require((len(raws[filename]), sha256(raws[filename])) == SOURCE_PINS[filename], f"source pin drift: {filename}")
    manifest, manifest_raw, corrected = validate_manifest()
    v6 = load_v6()
    v5, reviewed_selector = patched_v5(v6, manifest)
    v6.load_v5 = lambda: v5
    predecessor_report, projected = v6.project_raws(raws)
    require(set(projected) == set(SOURCE_ORDER), "output topology drift")
    effects = effect_audit(v6, v5, reviewed_selector, manifest, corrected, raws, projected)
    delta = delta_audit(manifest, corrected, projected)

    report = copy.deepcopy(predecessor_report)
    report.pop("report_sha256_excluding_this_field", None)
    report["schema"] = "noether-isv-cyrillic-projection-v7-report-v1"
    report["status"] = "READY_DETERMINISTIC_V020_DERIVATION_IN_MEMORY"
    report["release"] = "NOETHER-ISV-v020"
    report["classification"] = "deterministic Cyrillic representation of the unchanged Latin Interslavic canon; not an independent translation witness"
    report["dependencies"].pop("role_manifest", None)
    report["dependencies"] = {
        "v019_v6_predecessor": {
            "path": "predecessor_v019/project_isv_cyrillic_v6.py",
            "bytes": V6_PIN[0],
            "sha256": V6_PIN[1],
        },
        "reviewed_role_manifest": {
            "path": "decision_records/ISV020-REVIEWED-PROJECTION-ROLE-MANIFEST.json",
            **describe(manifest_raw),
            "internal_sha256": MANIFEST_INTERNAL,
        },
        **report["dependencies"],
    }
    report["latin_source_freeze"] = {
        "bytes_changed_from_v019": 0,
        "files": [
            {"file": filename, **describe(raws[filename])} for filename in SOURCE_ORDER
        ],
    }
    report["review_effect_audit"] = effects
    report["predecessor_delta_audit"] = delta
    report["limitations"] = [
        "Role classification was exhaustive and source-bound but is not native-speaker, community, official-standard, or external scholarly-peer-review certification.",
        "A deterministic text derivation does not replace complete TeX build, text, math, font, link, or visual QA.",
        "The v019 public bytes remain immutable; v020 is a monotonic successor correcting only the derived Cyrillic role policy.",
    ]
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    return report, projected


def project_corpus(source_dir: Path = SOURCE_DIR) -> tuple[dict[str, Any], dict[str, bytes]]:
    return project_raws(source_raws(source_dir))


def install_outputs(output_dir: Path, projected: Mapping[str, bytes]) -> list[dict[str, Any]]:
    require(output_dir.resolve() == OUTPUT_DIR.resolve(), "output directory must be exact v020 source_cyrillic")
    require(output_dir.is_dir() and not output_dir.is_symlink(), "unsafe output directory")
    targets = {filename: output_dir / OUTPUT_NAMES[filename] for filename in SOURCE_ORDER}
    for filename, target in targets.items():
        if target.exists():
            require(target.is_file() and not target.is_symlink(), f"unsafe existing output: {target}")
            require(target.read_bytes() == projected[filename], f"refusing to overwrite different output: {target}")
    installed: list[Path] = []
    try:
        for ordinal, filename in enumerate(SOURCE_ORDER, 1):
            target = targets[filename]
            if target.exists():
                continue
            stage = output_dir / f".{target.name}.v7-stage-{os.getpid()}-{ordinal}"
            require(not stage.exists(), f"stage collision: {stage}")
            try:
                with stage.open("xb") as handle:
                    handle.write(projected[filename])
                    handle.flush()
                    os.fsync(handle.fileno())
                require(stage.read_bytes() == projected[filename], f"stage readback mismatch: {stage}")
                os.replace(stage, target)
                require(target.read_bytes() == projected[filename], f"install readback mismatch: {target}")
                installed.append(target)
            finally:
                if stage.exists():
                    stage.unlink()
    except Exception:
        for target in reversed(installed):
            matching = next((raw for name, raw in projected.items() if OUTPUT_NAMES[name] == target.name), None)
            if matching is not None and target.is_file() and not target.is_symlink() and target.read_bytes() == matching:
                target.unlink()
        raise
    return [
        {"path": str(target), **describe(target.read_bytes())}
        for target in targets.values()
    ]


def compact(report: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "schema",
        "status",
        "release",
        "classification",
        "output_manifest",
        "output_manifest_sha256",
        "conversion_classes",
        "projection_issues",
        "tex_dimension_policy",
        "latin_source_freeze",
        "review_effect_audit",
        "predecessor_delta_audit",
        "report_sha256_excluding_this_field",
    )
    return {key: report[key] for key in keys}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-output-dir", type=Path)
    parser.add_argument("--full-report", action="store_true")
    args = parser.parse_args(argv)
    report, projected = project_corpus()
    payload: dict[str, Any] = copy.deepcopy(report if args.full_report else compact(report))
    if args.write_output_dir is not None:
        output_dir = args.write_output_dir if args.write_output_dir.is_absolute() else ROOT / args.write_output_dir
        payload["install"] = install_outputs(output_dir, projected)
    sys.stdout.buffer.write(canonical_json(payload))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema": "noether-isv-cyrillic-projection-v7-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
