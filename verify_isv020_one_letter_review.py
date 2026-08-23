#!/usr/bin/env python3
"""Fail-closed verifier for the 690-record ISV020 I/V/M review.

This verifier is read-only. It binds the reviewed correction tuples to the
exact public v019 inventory and Latin sources, independently re-enumerates the
visible one-letter census, and rejects project decisions swallowed by a wider
protected range. It does not itself generate or install Cyrillic output.
"""

from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
PRED = ROOT / "predecessor_v019"
INVENTORY_PATH = PRED / "decision_records/ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json"
CORRECTIONS_PATH = ROOT / "decision_records/ISV020-ONE-LETTER-CORRECTIONS.json"
V2_PATH = PRED / "project_isv_cyrillic_v2.py"
SOURCE_DIR = ROOT / "source_latin"

INVENTORY_PIN = (
    3_505_137,
    "E7B8CDE438E9B72A61F6FA3AE0422AF6CBFBCBB7965E139BD123709CC1EEF818",
)
INVENTORY_INTERNAL = "96CE41A7C076142F36697B93004E7A4F92BF0B90296C0A265B0A32CA99A29DBC"
ONE_LETTER_INVENTORY_SHA256 = "650B9ACCB9F349077BABC099A54A58C14F0E7B1CC437CA29CB9610F45B9A3AFD"
CORRECTIONS_PIN = (
    4_805,
    "2FC8216DB1CD666E037C4B33CE8964889551E43E58311AC6F24F457DC93CE2D6",
)
V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
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
VISIBLE_ROLES = frozenset({"visible_prose", "visible_math_text", "visible_metadata"})
CODE_TO_DISPOSITION = {
    "P": "PROJECT_LEXICAL_INTERSLAVIC_WORD",
    "R": "PRESERVE_STRUCTURAL_ROMAN_LABEL",
}
EXPECTED_EFFECTIVE_COUNTS = {
    "PRESERVE_COVERED_BY_ALLOWED_LETTER_FOREIGN_RANGE": 19,
    "PRESERVE_DOTTED_INITIAL_OR_ROMAN_ORDINAL": 32,
    "PRESERVE_FOREIGN_INITIAL_OR_CITATION_ABBREVIATION": 32,
    "PRESERVE_STRUCTURAL_ROMAN_LABEL": 249,
    "PROJECT_LEXICAL_INTERSLAVIC_WORD": 358,
}


class ReviewError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewError(message)


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
            raise ReviewError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(raw: bytes, label: str) -> Any:
    require(raw.endswith(b"\n") and b"\r" not in raw, f"transport drift: {label}")
    require(raw.startswith((b"{", b"[")) and not raw.startswith(b"\xef\xbb\xbf"), f"encoding drift: {label}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)


def read_exact(path: Path, pin: tuple[int, str], label: str) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe {label}: {path}")
    raw = path.read_bytes()
    require((len(raw), sha256(raw)) == pin, f"pin drift: {label}")
    return raw


def load_v2() -> Any:
    read_exact(V2_PATH, V2_PIN, "v2 parser/projector")
    spec = importlib.util.spec_from_file_location("isv020_review_v2", V2_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v2")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def record_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["file"], row["line"], row["column"], row["surface"])


def span_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["file"], *row["scalar_span"], row["surface"])


def validate_record(v2: Any, row: dict[str, Any], texts: dict[str, str]) -> None:
    filename = row.get("file")
    require(filename in texts, f"unknown source: {filename}")
    text = texts[filename]
    span = row.get("scalar_span")
    require(
        isinstance(span, list)
        and len(span) == 2
        and all(isinstance(value, int) for value in span),
        f"invalid span: {filename}",
    )
    start, end = span
    require(0 <= start < end <= len(text), f"span out of range: {filename}:{span}")
    surface = row.get("surface")
    require(surface in {"I", "V", "M"}, f"unexpected one-letter surface: {surface}")
    require(text[start:end] == surface, f"surface drift: {filename}:{span}")
    require(sha256(surface.encode("utf-8")) == row.get("surface_sha256"), f"surface hash drift: {filename}:{span}")
    scalar_starts, byte_starts, lines = v2.line_tables(text)
    locator = v2.locator(text, start, scalar_starts, byte_starts, lines)
    for key in ("line", "column", "byte_offset", "line_sha256", "context_sha256"):
        require(locator[key] == row.get(key), f"locator drift {key}: {filename}:{span}")


def independent_census(v2: Any, texts: dict[str, str]) -> list[tuple[Any, ...]]:
    result: list[tuple[Any, ...]] = []
    for filename in SOURCE_ORDER:
        text = texts[filename]
        for segment in v2.TexSegmenter(text).segment():
            if segment.role not in VISIBLE_ROLES:
                continue
            chunk = text[segment.start : segment.end]
            for match in v2.LETTER_RE.finditer(chunk):
                surface = match.group(0)
                if surface not in {"I", "V", "M"}:
                    continue
                start = segment.start + match.start()
                end = segment.start + match.end()
                result.append((filename, start, end, surface))
    return result


def main() -> int:
    inventory_raw = read_exact(INVENTORY_PATH, INVENTORY_PIN, "predecessor inventory")
    inventory = strict_json(inventory_raw, str(INVENTORY_PATH))
    require(inventory.get("schema") == "noether-isv-final-projection-completeness-inventory-v1", "inventory schema drift")
    embedded = inventory.get("inventory_sha256_excluding_this_field")
    without = copy.deepcopy(inventory)
    without.pop("inventory_sha256_excluding_this_field", None)
    require(embedded == INVENTORY_INTERNAL, "inventory embedded digest drift")
    require(sha256(canonical_json(without)) == INVENTORY_INTERNAL, "inventory internal digest mismatch")

    one = inventory.get("visible_one_letter_tokens")
    require(isinstance(one, list) and len(one) == 690, "one-letter inventory count drift")
    require(sha256(canonical_json(one)) == ONE_LETTER_INVENTORY_SHA256, "one-letter subinventory digest drift")
    require(
        inventory.get("summaries", {}).get("visible_one_letter_tokens", {}).get("inventory_sha256")
        == ONE_LETTER_INVENTORY_SHA256,
        "one-letter summary digest drift",
    )

    v2 = load_v2()
    raws: dict[str, bytes] = {}
    texts: dict[str, str] = {}
    for filename in SOURCE_ORDER:
        raw = read_exact(SOURCE_DIR / filename, SOURCE_PINS[filename], filename)
        raws[filename] = raw
        texts[filename] = v2.strict_transport(raw, filename)

    for row in one:
        require(isinstance(row, dict), "one-letter row must be an object")
        validate_record(v2, row, texts)
    locator_keys = [record_key(row) for row in one]
    span_keys = [span_key(row) for row in one]
    require(len(set(locator_keys)) == 690, "duplicate locator/surface key")
    require(len(set(span_keys)) == 690, "duplicate span/surface key")
    census = independent_census(v2, texts)
    expected_census = [(row["file"], *row["scalar_span"], row["surface"]) for row in one]
    require(census == expected_census, "live visible I/V/M census differs from the pinned inventory")

    correction_raw = read_exact(CORRECTIONS_PATH, CORRECTIONS_PIN, "one-letter corrections")
    corrections = strict_json(correction_raw, str(CORRECTIONS_PATH))
    require(isinstance(corrections, list) and len(corrections) == 93, "correction count drift")
    indices = [row[0] for row in corrections]
    require(indices == sorted(indices) and len(set(indices)) == 93, "correction indices not strictly increasing and unique")
    require(all(isinstance(index, int) and 0 <= index < 690 for index in indices), "correction index out of range")

    reviewed = copy.deepcopy(one)
    correction_keys: list[tuple[Any, ...]] = []
    transitions: Counter[str] = Counter()
    for correction in corrections:
        require(isinstance(correction, list) and len(correction) == 7, "invalid correction tuple")
        index, filename, line, column, surface, old_code, new_code = correction
        require(old_code in CODE_TO_DISPOSITION and new_code in CODE_TO_DISPOSITION and old_code != new_code, "invalid correction code")
        row = reviewed[index]
        expected = (filename, line, column, surface, CODE_TO_DISPOSITION[old_code])
        observed = (row.get("file"), row.get("line"), row.get("column"), row.get("surface"), row.get("disposition"))
        require(observed == expected, f"correction binding mismatch at index {index}: {observed}")
        row["disposition"] = CODE_TO_DISPOSITION[new_code]
        correction_keys.append((filename, line, column, surface))
        transitions[f"{old_code}->{new_code}"] += 1
    require(len(set(correction_keys)) == 93, "duplicate correction locator key")
    require(transitions == Counter({"P->R": 92, "R->P": 1}), f"correction transition drift: {transitions}")

    effective_counts = dict(sorted(Counter(row["disposition"] for row in reviewed).items()))
    require(effective_counts == EXPECTED_EFFECTIVE_COUNTS, f"effective disposition drift: {effective_counts}")
    require(all(row["disposition"].startswith("PRESERVE") for row in reviewed if row["surface"] == "M"), "an M record became projectable")

    protected_ranges: dict[str, list[tuple[int, int, str]]] = {filename: [] for filename in SOURCE_ORDER}
    for category in (
        "unprotected_style_payloads",
        "unprotected_name_candidates",
        "unprotected_foreign_lexicon_hits",
    ):
        rows = inventory.get(category)
        require(isinstance(rows, list), f"missing category: {category}")
        for row in rows:
            if str(row.get("disposition", "")).startswith(("PROTECT", "PRESERVE")):
                start, end = row["scalar_span"]
                protected_ranges[row["file"]].append((start, end, category))
    for row in reviewed:
        if row["disposition"].startswith("PRESERVE"):
            start, end = row["scalar_span"]
            protected_ranges[row["file"]].append((start, end, "visible_one_letter_tokens"))

    swallowed: list[tuple[Any, ...]] = []
    for row in reviewed:
        if row["disposition"] != "PROJECT_LEXICAL_INTERSLAVIC_WORD":
            continue
        start, end = row["scalar_span"]
        for left, right, category in protected_ranges[row["file"]]:
            if left <= start and end <= right:
                swallowed.append((*record_key(row), category, left, right))
    require(not swallowed, f"project records swallowed by protected ranges: {swallowed[:1]}")

    report: dict[str, Any] = {
        "schema": "noether-isv-one-letter-review-verification/1.0",
        "status": "PASS_READ_ONLY",
        "predecessor_inventory": {**describe(inventory_raw), "internal_sha256": INVENTORY_INTERNAL},
        "one_letter_subinventory": {"records": 690, "sha256": ONE_LETTER_INVENTORY_SHA256},
        "corrections": {**describe(correction_raw), "records": 93, "transitions": dict(sorted(transitions.items()))},
        "sources": [
            {"file": filename, **describe(raws[filename])} for filename in SOURCE_ORDER
        ],
        "uniqueness": {
            "locator_surface_keys": len(set(locator_keys)),
            "scalar_span_surface_keys": len(set(span_keys)),
            "correction_locator_keys": len(set(correction_keys)),
            "duplicates": 0,
        },
        "live_census": {"records": len(census), "exact_order_and_set_match": True},
        "effective_counts": effective_counts,
        "project_records_swallowed_by_other_protection": 0,
        "ambiguous_records": 0,
        "output_generation_authorized_by_this_verifier": False,
    }
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    sys.stdout.buffer.write(canonical_json(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema": "noether-isv-one-letter-review-verification-failure/1.0",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
