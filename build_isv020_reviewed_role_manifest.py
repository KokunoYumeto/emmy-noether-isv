#!/usr/bin/env python3
"""Build the source-bound, fully reviewed ISV020 projection-role manifest.

The public v019 inventory remains immutable. This builder validates every one
of its 4,560 records against the exact unchanged Latin sources, applies only
indexed reviewer corrections whose old dispositions still match, requires a
zero-ambiguity full-review declaration for every category, and emits a new
canonical manifest. Default execution is read-only; ``--write-output`` writes
only the named successor manifest and refuses to overwrite different bytes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
PRED = ROOT / "predecessor_v019"
SOURCE_DIR = ROOT / "source_latin"
V2_PATH = PRED / "project_isv_cyrillic_v2.py"
INVENTORY_PATH = PRED / "decision_records/ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json"
DECLARATIONS_PATH = ROOT / "decision_records/ISV020-ROLE-REVIEW-DECLARATIONS.json"
ADDITIONAL_SPANS_PATH = ROOT / "decision_records/ISV020-ADDITIONAL-PROTECTION-SPANS.json"
DEFAULT_OUTPUT = ROOT / "decision_records/ISV020-REVIEWED-PROJECTION-ROLE-MANIFEST.json"

V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
INVENTORY_PIN = (
    3_505_137,
    "E7B8CDE438E9B72A61F6FA3AE0422AF6CBFBCBB7965E139BD123709CC1EEF818",
)
INVENTORY_INTERNAL = "96CE41A7C076142F36697B93004E7A4F92BF0B90296C0A265B0A32CA99A29DBC"
ADDITIONAL_SPANS_PIN = (
    4_510,
    "40C4CF5EEBAA3BF2A769CA81C5C49142C46A059D8DD735A4D86AC92473523D71",
)
ADDITIONAL_SPAN_COUNT = 8
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
CATEGORY_SUBINVENTORY_SHA256 = {
    "unprotected_style_payloads": "4517933328DD9F5CE71558565E89B6390B13A7E7DE421FC8DC64DCB8627C600C",
    "unprotected_name_candidates": "97A298E267918F7397A4AE030F46A91D96BB52C0FAC748E932C3297149656E5F",
    "unprotected_foreign_lexicon_hits": "F2A53A16C046870B27804B718C7C9C95F973E166BA926D90EB98A44FE7BE6B64",
    "visible_one_letter_tokens": "650B9ACCB9F349077BABC099A54A58C14F0E7B1CC437CA29CB9610F45B9A3AFD",
}
CORRECTION_PATHS = {
    "unprotected_style_payloads": ROOT / "decision_records/ISV020-STYLE-CORRECTIONS.json",
    "unprotected_name_candidates": ROOT / "decision_records/ISV020-NAME-CORRECTIONS.json",
    "unprotected_foreign_lexicon_hits": ROOT / "decision_records/ISV020-LEXICON-CORRECTIONS.json",
    "visible_one_letter_tokens": ROOT / "decision_records/ISV020-ONE-LETTER-CORRECTIONS.json",
}
ALLOWED_DISPOSITIONS = {
    "unprotected_style_payloads": frozenset(
        {
            "KEEP_PROJECTABLE_INTERSLAVIC_STYLE_PAYLOAD",
            "PROTECT_COMPLETE_ORIGINAL_LANGUAGE_STYLE_PAYLOAD",
        }
    ),
    "unprotected_name_candidates": frozenset(
        {
            "KEEP_PROJECTABLE_INTEGRATED_OR_NONNAME_CANDIDATE",
            "PROTECT_COMPLETE_UNINFLECTED_IDENTITY",
        }
    ),
    "unprotected_foreign_lexicon_hits": frozenset(
        {
            "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT",
            "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN",
        }
    ),
    "visible_one_letter_tokens": frozenset(
        {
            "PRESERVE_COVERED_BY_ALLOWED_LETTER_FOREIGN_RANGE",
            "PRESERVE_DOTTED_INITIAL_OR_ROMAN_ORDINAL",
            "PRESERVE_FOREIGN_INITIAL_OR_CITATION_ABBREVIATION",
            "PRESERVE_STRUCTURAL_ROMAN_LABEL",
            "PROJECT_LEXICAL_INTERSLAVIC_WORD",
        }
    ),
}
ONE_LETTER_CODES = {
    "P": "PROJECT_LEXICAL_INTERSLAVIC_WORD",
    "R": "PRESERVE_STRUCTURAL_ROMAN_LABEL",
}
LEXICON_CODES = {
    "K": "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT",
    "F": "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN",
}


class ManifestError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


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
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
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


def load_v2() -> Any:
    read_exact(V2_PATH, V2_PIN, "v2 parser/projector")
    spec = importlib.util.spec_from_file_location("isv020_manifest_v2", V2_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v2")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_source_row(
    v2: Any,
    row: Mapping[str, Any],
    texts: Mapping[str, str],
    locator_tables: Mapping[str, tuple[Any, ...]],
) -> None:
    filename = row.get("file")
    require(filename in texts, f"unknown source: {filename}")
    text = texts[filename]
    span = row.get("scalar_span")
    require(
        isinstance(span, list)
        and len(span) == 2
        and all(isinstance(item, int) for item in span),
        f"invalid span: {filename}",
    )
    start, end = span
    require(0 <= start < end <= len(text), f"span out of range: {filename}:{span}")
    surface = row.get("surface")
    require(isinstance(surface, str) and text[start:end] == surface, f"surface drift: {filename}:{span}")
    require(sha256(surface.encode("utf-8")) == row.get("surface_sha256"), f"surface digest drift: {filename}:{span}")
    scalar_starts, byte_starts, lines = locator_tables[filename]
    locator = v2.locator(text, start, scalar_starts, byte_starts, lines)
    for key in ("line", "column", "byte_offset", "line_sha256", "context_sha256"):
        require(locator[key] == row.get(key), f"locator drift {key}: {filename}:{span}")


def row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (row.get("file"), row.get("line"), row.get("column"), row.get("surface"))


def span_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    span = row.get("scalar_span")
    return (row.get("file"), *span, row.get("surface"))


def summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    raw = canonical_json(list(rows))
    return {
        "occurrences": len(rows),
        "by_file": dict(sorted(Counter(row["file"] for row in rows).items())),
        "by_surface": dict(sorted(Counter(row["surface"] for row in rows).items())),
        "by_disposition": dict(sorted(Counter(row["disposition"] for row in rows).items())),
        "inventory_sha256": sha256(raw),
    }


def normalize_disposition(category: str, value: Any) -> str:
    require(isinstance(value, str), f"non-string disposition in {category}")
    if category == "visible_one_letter_tokens":
        value = ONE_LETTER_CODES.get(value, value)
    elif category == "unprotected_foreign_lexicon_hits":
        value = LEXICON_CODES.get(value, value)
    require(value in ALLOWED_DISPOSITIONS[category], f"invalid disposition in {category}: {value}")
    return value


def load_declarations() -> tuple[dict[str, Any], bytes]:
    raw = read_regular(DECLARATIONS_PATH, "review declarations")
    value = strict_json(raw, str(DECLARATIONS_PATH))
    require(isinstance(value, dict), "review declarations root must be an object")
    require(value.get("schema") == "noether-isv-role-review-declarations/1.0", "declaration schema drift")
    reviews = value.get("categories")
    require(isinstance(reviews, dict) and set(reviews) == set(CATEGORIES), "declaration category topology drift")
    for category in CATEGORIES:
        declaration = reviews[category]
        require(isinstance(declaration, dict), f"missing declaration: {category}")
        require(declaration.get("status") == "FULL_INDEPENDENT_REVIEW_COMPLETE", f"review incomplete: {category}")
        require(declaration.get("records_reviewed") == CATEGORY_COUNTS[category], f"review count drift: {category}")
        require(declaration.get("ambiguities") == 0, f"unresolved ambiguity: {category}")
    additions = value.get("additional_protection_spans")
    require(isinstance(additions, dict), "missing additional protection-span declaration")
    require(additions.get("status") == "FULL_INDEPENDENT_REVIEW_COMPLETE", "additional span review incomplete")
    require(additions.get("records_added") == ADDITIONAL_SPAN_COUNT, "additional span count drift")
    require(additions.get("ambiguities") == 0, "unresolved additional-span ambiguity")
    return value, raw


def apply_corrections(
    category: str,
    predecessor_rows: list[dict[str, Any]],
    correction_raw: bytes,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    corrections = strict_json(correction_raw, str(CORRECTION_PATHS[category]))
    require(isinstance(corrections, list), f"correction root must be an array: {category}")
    rows = copy.deepcopy(predecessor_rows)
    seen_indices: set[int] = set()
    seen_keys: set[tuple[Any, ...]] = set()
    normalized: list[dict[str, Any]] = []
    last_index = -1
    for ordinal, correction in enumerate(corrections, 1):
        require(isinstance(correction, list) and len(correction) == 7, f"invalid correction tuple: {category}:{ordinal}")
        index, filename, line, column, surface, old_value, new_value = correction
        require(isinstance(index, int) and 0 <= index < len(rows), f"correction index out of range: {category}:{index}")
        require(index > last_index and index not in seen_indices, f"correction indices must be strictly increasing: {category}:{index}")
        last_index = index
        seen_indices.add(index)
        old_disposition = normalize_disposition(category, old_value)
        new_disposition = normalize_disposition(category, new_value)
        require(old_disposition != new_disposition, f"no-op correction: {category}:{index}")
        row = rows[index]
        expected = (filename, line, column, surface, old_disposition)
        observed = (*row_key(row), row.get("disposition"))
        require(observed == expected, f"correction binding mismatch: {category}:{index}: {observed}")
        key = row_key(row)
        require(key not in seen_keys, f"duplicate correction locator: {category}:{key}")
        seen_keys.add(key)
        row["predecessor_disposition"] = old_disposition
        row["disposition"] = new_disposition
        row["review_correction"] = {
            "successor": "NOETHER-ISV-v020",
            "category_index0": index,
            "correction_ordinal1": ordinal,
        }
        normalized.append(
            {
                "category_index0": index,
                "file": filename,
                "line": line,
                "column": column,
                "surface": surface,
                "old_disposition": old_disposition,
                "new_disposition": new_disposition,
            }
        )
    return rows, normalized


def build() -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    predecessor_raw = read_exact(INVENTORY_PATH, INVENTORY_PIN, "predecessor role inventory")
    predecessor = strict_json(predecessor_raw, str(INVENTORY_PATH))
    require(isinstance(predecessor, dict), "predecessor inventory root must be an object")
    claimed = predecessor.get("inventory_sha256_excluding_this_field")
    without = copy.deepcopy(predecessor)
    without.pop("inventory_sha256_excluding_this_field", None)
    require(claimed == INVENTORY_INTERNAL, "predecessor embedded digest drift")
    require(sha256(canonical_json(without)) == INVENTORY_INTERNAL, "predecessor internal digest mismatch")

    v2 = load_v2()
    raws: dict[str, bytes] = {}
    texts: dict[str, str] = {}
    for filename in SOURCE_ORDER:
        raw = read_exact(SOURCE_DIR / filename, SOURCE_PINS[filename], filename)
        raws[filename] = raw
        texts[filename] = v2.strict_transport(raw, filename)
    locator_tables = {
        filename: v2.line_tables(texts[filename]) for filename in SOURCE_ORDER
    }

    declarations, declaration_raw = load_declarations()
    additional_raw = read_exact(ADDITIONAL_SPANS_PATH, ADDITIONAL_SPANS_PIN, "additional protected spans")
    additional_spans = strict_json(additional_raw, str(ADDITIONAL_SPANS_PATH))
    require(isinstance(additional_spans, list), "additional protected spans root must be an array")
    require(len(additional_spans) == ADDITIONAL_SPAN_COUNT, "additional protected span count drift")
    additional_locator_keys: list[tuple[Any, ...]] = []
    additional_scalar_keys: list[tuple[Any, ...]] = []
    for ordinal, row in enumerate(additional_spans, 1):
        require(isinstance(row, dict), f"non-object additional span: {ordinal}")
        validate_source_row(v2, row, texts, locator_tables)
        require(row.get("disposition") == "PROTECT_COMPLETE_UNINFLECTED_IDENTITY", f"additional disposition drift: {ordinal}")
        require(row.get("role") == "visible_prose", f"additional role drift: {ordinal}")
        require(row.get("overlaps_existing_protected_range") is False, f"declared overlap drift: {ordinal}")
        require(row.get("overlapping_protected_ranges") == [], f"declared overlap inventory drift: {ordinal}")
        parent_index = row.get("parent_name_record_index0")
        require(isinstance(parent_index, int) and 0 <= parent_index < CATEGORY_COUNTS["unprotected_name_candidates"], f"parent name index drift: {ordinal}")
        additional_locator_keys.append(row_key(row))
        additional_scalar_keys.append(span_key(row))
    require(len(set(additional_locator_keys)) == ADDITIONAL_SPAN_COUNT, "duplicate additional locator keys")
    require(len(set(additional_scalar_keys)) == ADDITIONAL_SPAN_COUNT, "duplicate additional scalar keys")
    result = copy.deepcopy(predecessor)
    result.pop("inventory_sha256_excluding_this_field", None)
    result["schema"] = "noether-isv-reviewed-projection-role-manifest/2.0"
    result["status"] = "FULLY_REVIEWED_ZERO_AMBIGUITY_BINDING_RELEASE_GATE"
    result["scope"] = {
        "purpose": "source-bound role policy for deterministic Cyrillic projection",
        "predecessor_release": "NOETHER-ISV-v019",
        "successor_release": "NOETHER-ISV-v020",
        "latin_editorial_head": "ISV019-EDIT-0171",
        "latin_source_bytes_changed": 0,
        "source_order": list(SOURCE_ORDER),
    }
    result["dependencies"] = {
        "predecessor_inventory": {
            "path": "predecessor_v019/decision_records/ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json",
            **describe(predecessor_raw),
            "internal_sha256": INVENTORY_INTERNAL,
        },
        "v2_parser_projector": {
            "path": "predecessor_v019/project_isv_cyrillic_v2.py",
            "bytes": V2_PIN[0],
            "sha256": V2_PIN[1],
        },
        "review_declarations": {
            "path": str(DECLARATIONS_PATH.relative_to(ROOT)).replace("\\", "/"),
            **describe(declaration_raw),
        },
        "additional_protected_spans": {
            "path": str(ADDITIONAL_SPANS_PATH.relative_to(ROOT)).replace("\\", "/"),
            **describe(additional_raw),
        },
        "official_dictionary_authority": {
            "artifact": "interslavic_dictionary_official_snapshot_20260816/source_sheet_basic.csv",
            "bytes": 8_101_157,
            "sha256": "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561",
            "boundary": "lexical evidence only; not native-speaker or official-project certification of this edition",
        },
    }

    review_files: dict[str, Any] = {}
    corrections_total = 0
    for category in CATEGORIES:
        predecessor_rows = predecessor.get(category)
        require(isinstance(predecessor_rows, list), f"missing predecessor category: {category}")
        require(len(predecessor_rows) == CATEGORY_COUNTS[category], f"category count drift: {category}")
        require(sha256(canonical_json(predecessor_rows)) == CATEGORY_SUBINVENTORY_SHA256[category], f"category digest drift: {category}")
        locator_keys: list[tuple[Any, ...]] = []
        scalar_keys: list[tuple[Any, ...]] = []
        for row in predecessor_rows:
            require(isinstance(row, dict), f"non-object category row: {category}")
            validate_source_row(v2, row, texts, locator_tables)
            require(row.get("disposition") in ALLOWED_DISPOSITIONS[category], f"predecessor disposition drift: {category}")
            locator_keys.append(row_key(row))
            scalar_keys.append(span_key(row))
        require(len(set(locator_keys)) == len(locator_keys), f"duplicate locator keys: {category}")
        require(len(set(scalar_keys)) == len(scalar_keys), f"duplicate scalar keys: {category}")

        correction_path = CORRECTION_PATHS[category]
        correction_raw = read_regular(correction_path, f"corrections for {category}")
        rows, normalized = apply_corrections(category, predecessor_rows, correction_raw)
        declared_defects = declarations["categories"][category].get("defects")
        require(declared_defects == len(normalized), f"declared defect count drift: {category}")
        result[category] = rows
        result.setdefault("summaries", {})[category] = summary(rows)
        corrections_total += len(normalized)
        review_files[category] = {
            "records_reviewed": len(rows),
            "defects_corrected": len(normalized),
            "ambiguities": 0,
            "predecessor_subinventory_sha256": CATEGORY_SUBINVENTORY_SHA256[category],
            "correction_file": {
                "path": str(correction_path.relative_to(ROOT)).replace("\\", "/"),
                **describe(correction_raw),
            },
            "correction_inventory_sha256": sha256(canonical_json(normalized)),
            "unique_locator_keys": len(set(locator_keys)),
            "unique_scalar_span_keys": len(set(scalar_keys)),
        }

    name_rows = result["unprotected_name_candidates"]
    for ordinal, row in enumerate(additional_spans, 1):
        parent = name_rows[row["parent_name_record_index0"]]
        require(parent["file"] == row["file"] and parent["line"] == row["line"], f"additional parent locator drift: {ordinal}")
        start, end = row["scalar_span"]
        parent_start, parent_end = parent["scalar_span"]
        require(max(start, parent_start) < min(end, parent_end), f"additional parent does not intersect: {ordinal}")
    result["additional_protected_spans"] = copy.deepcopy(additional_spans)
    result.setdefault("summaries", {})["additional_protected_spans"] = summary(additional_spans)

    protected: dict[str, list[tuple[int, int, str]]] = {filename: [] for filename in SOURCE_ORDER}
    for category in CATEGORIES:
        for row in result[category]:
            disposition = row["disposition"]
            if disposition.startswith(("PROTECT", "PRESERVE")):
                start, end = row["scalar_span"]
                protected[row["file"]].append((start, end, category))
    for ordinal, row in enumerate(additional_spans, 1):
        start, end = row["scalar_span"]
        for left, right, category in protected[row["file"]]:
            require(end <= left or right <= start, f"additional span overlaps existing protection: {ordinal}:{category}")
        protected[row["file"]].append((start, end, "additional_protected_spans"))
    swallowed_one_letter: list[dict[str, Any]] = []
    for row in result["visible_one_letter_tokens"]:
        if row["disposition"] != "PROJECT_LEXICAL_INTERSLAVIC_WORD":
            continue
        start, end = row["scalar_span"]
        for left, right, category in protected[row["file"]]:
            if left <= start and end <= right:
                swallowed_one_letter.append(
                    {
                        "row": row_key(row),
                        "covering_category": category,
                        "covering_span": [left, right],
                    }
                )
    require(not swallowed_one_letter, f"projectable one-letter rows swallowed by protection: {swallowed_one_letter[:1]}")

    result["review"] = {
        "review_status": "FULL_INDEPENDENT_REVIEW_COMPLETE",
        "records_reviewed": sum(CATEGORY_COUNTS.values()),
        "source_bound_records_emitted": sum(CATEGORY_COUNTS.values()) + ADDITIONAL_SPAN_COUNT,
        "classification_defects_corrected": corrections_total,
        "coverage_defects_corrected": ADDITIONAL_SPAN_COUNT,
        "defects_corrected": corrections_total + ADDITIONAL_SPAN_COUNT,
        "ambiguities": 0,
        "categories": review_files,
        "additional_protection_spans": {
            "records_added": ADDITIONAL_SPAN_COUNT,
            "ambiguities": 0,
            "file": {
                "path": str(ADDITIONAL_SPANS_PATH.relative_to(ROOT)).replace("\\", "/"),
                **describe(additional_raw),
            },
            "unique_locator_keys": len(set(additional_locator_keys)),
            "unique_scalar_span_keys": len(set(additional_scalar_keys)),
        },
        "parent_validation": {
            "all_source_surfaces_and_locators_revalidated": True,
            "all_category_keyspaces_unique": True,
            "projectable_one_letter_rows_swallowed_by_protection": 0,
            "claim_boundary": "role classification review; not native-speaker, community, official-standard, or independent scholarly-peer-review certification",
        },
    }
    result["closure_rule"] = (
        "The projector must pin this manifest and all four source bytes, consume every "
        "protected span, prove every corrected output effect, reject missing/extra/duplicate "
        "records and unsafe overlaps, and report zero unverified corrections before writing."
    )
    result["inventory_sha256_excluding_this_field"] = sha256(canonical_json(result))
    raw = canonical_json(result)
    report = {
        "schema": "noether-isv-reviewed-role-manifest-build/1.0",
        "status": "READY_IN_MEMORY",
        "output": describe(raw),
        "output_internal_sha256": result["inventory_sha256_excluding_this_field"],
        "records_reviewed": result["review"]["records_reviewed"],
        "defects_corrected": corrections_total,
        "coverage_spans_added": ADDITIONAL_SPAN_COUNT,
        "total_defects_corrected": corrections_total + ADDITIONAL_SPAN_COUNT,
        "ambiguities": 0,
        "sources": [{"file": filename, **describe(raws[filename])} for filename in SOURCE_ORDER],
        "correction_files": {
            category: review_files[category]["correction_file"] for category in CATEGORIES
        },
    }
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    return result, raw, report


def install(path: Path, raw: bytes) -> str:
    require(path.parent.resolve() == (ROOT / "decision_records").resolve(), "output must stay in decision_records")
    if path.exists():
        require(path.is_file() and not path.is_symlink(), f"unsafe existing output: {path}")
        require(path.read_bytes() == raw, f"refusing to overwrite different output: {path}")
        return "EXISTING_IDENTICAL"
    path.write_bytes(raw)
    require(path.read_bytes() == raw, "post-write readback mismatch")
    return "CREATED_AND_READ_BACK"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-output", type=Path)
    args = parser.parse_args(argv)
    result, raw, report = build()
    if args.write_output is not None:
        output = args.write_output if args.write_output.is_absolute() else ROOT / args.write_output
        report = copy.deepcopy(report)
        report["install"] = {
            "path": str(output.relative_to(ROOT)).replace("\\", "/"),
            "status": install(output, raw),
        }
        report.pop("report_sha256_excluding_this_field", None)
        report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    sys.stdout.buffer.write(canonical_json(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema": "noether-isv-reviewed-role-manifest-build-failure/1.0",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
