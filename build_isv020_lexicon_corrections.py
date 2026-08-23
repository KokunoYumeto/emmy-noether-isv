#!/usr/bin/env python3
"""Materialize the independently reviewed 270-record lexicon correction set."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "predecessor_v019/decision_records/ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json"
DEFAULT_OUTPUT = ROOT / "decision_records/ISV020-LEXICON-CORRECTIONS.json"
INVENTORY_PIN = (
    3_505_137,
    "E7B8CDE438E9B72A61F6FA3AE0422AF6CBFBCBB7965E139BD123709CC1EEF818",
)
K = "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT"
F = "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN"

ROMAN_COUNTS = {"II": 215, "IIa": 3, "XIII": 10, "XXII": 1}
K_TO_F_EXPLICIT = {
    73: "in",
    479: "teoria",
    665: "Algebra",
    719: "in",
    752: "Algebra",
    775: "teoria",
    844: "in",
    1054: "in",
    1222: "Ideale",
    1398: "No",
    1404: "Ideale",
    1426: "No",
    1567: "in",
    1756: "in",
    1915: "Algebra",
    2090: "in",
}
F_TO_K_EXPLICIT = {
    71: "On",
    105: "On",
    147: "On",
    193: "On",
    520: "Grassmann",
    658: "On",
    659: "On",
    663: "On",
    1197: "On",
    1372: "jan",
    1764: "On",
    1817: "van",
    1818: "der",
    1945: "Jordan",
    1954: "van",
    1955: "der",
    1956: "van",
    1957: "der",
    1999: "On",
    2002: "On",
    2068: "On",
    2102: "On",
    2259: "On",
    2267: "On",
    2323: "On",
}
EXPECTED_BY_FILE = {
    "44-book-isv.tex": 4,
    "45-isv.tex": 12,
    "base-papers1-43-isv.tex": 240,
    "bib-isv.tex": 14,
}


class CorrectionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CorrectionError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def build() -> tuple[list[list[Any]], bytes, dict[str, Any]]:
    raw = INVENTORY.read_bytes()
    require((len(raw), sha256(raw)) == INVENTORY_PIN, "inventory pin drift")
    value = json.loads(raw.decode("utf-8"))
    rows = value.get("unprotected_foreign_lexicon_hits")
    require(isinstance(rows, list) and len(rows) == 2_371, "lexicon inventory topology drift")

    roman_indices = [
        index
        for index, row in enumerate(rows)
        if row.get("disposition") == K and row.get("surface") in ROMAN_COUNTS
    ]
    require(
        Counter(rows[index]["surface"] for index in roman_indices) == Counter(ROMAN_COUNTS),
        "Roman-label census drift",
    )
    require(len(roman_indices) == 229, "Roman-label correction count drift")
    require(not (set(roman_indices) & set(K_TO_F_EXPLICIT)), "duplicate K-to-F correction index")
    require(not (set(roman_indices) & set(F_TO_K_EXPLICIT)), "opposed correction index")
    require(not (set(K_TO_F_EXPLICIT) & set(F_TO_K_EXPLICIT)), "opposed explicit correction index")

    transitions: dict[int, tuple[str, str, str]] = {
        index: (rows[index]["surface"], "K", "F") for index in roman_indices
    }
    for index, surface in K_TO_F_EXPLICIT.items():
        row = rows[index]
        require(row.get("surface") == surface and row.get("disposition") == K, f"K-to-F binding drift: {index}")
        transitions[index] = (surface, "K", "F")
    for index, surface in F_TO_K_EXPLICIT.items():
        row = rows[index]
        require(row.get("surface") == surface and row.get("disposition") == F, f"F-to-K binding drift: {index}")
        transitions[index] = (surface, "F", "K")

    require(len(transitions) == 270, f"correction count drift: {len(transitions)}")
    corrections: list[list[Any]] = []
    for index in sorted(transitions):
        row = rows[index]
        surface, old_code, new_code = transitions[index]
        corrections.append(
            [
                index,
                row["file"],
                row["line"],
                row["column"],
                surface,
                old_code,
                new_code,
            ]
        )
    require(Counter(row[5] + "->" + row[6] for row in corrections) == Counter({"K->F": 245, "F->K": 25}), "transition count drift")
    require(dict(sorted(Counter(row[1] for row in corrections).items())) == EXPECTED_BY_FILE, "file count drift")
    require(len({tuple(row[1:5]) for row in corrections}) == 270, "duplicate correction locator")
    output = canonical_json(corrections)
    report = {
        "schema": "noether-isv-lexicon-correction-build/1.0",
        "status": "READY_IN_MEMORY",
        "records": 270,
        "transitions": {"K->F": 245, "F->K": 25},
        "by_file": EXPECTED_BY_FILE,
        "output": {"bytes": len(output), "sha256": sha256(output)},
        "inventory": {"bytes": len(raw), "sha256": sha256(raw)},
    }
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    return corrections, output, report


def install(path: Path, raw: bytes) -> str:
    require(path.parent.resolve() == (ROOT / "decision_records").resolve(), "output must stay in decision_records")
    if path.exists():
        require(path.is_file() and not path.is_symlink(), "unsafe existing output")
        require(path.read_bytes() == raw, "refusing to overwrite different output")
        return "EXISTING_IDENTICAL"
    path.write_bytes(raw)
    require(path.read_bytes() == raw, "output readback mismatch")
    return "CREATED_AND_READ_BACK"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-output", type=Path)
    args = parser.parse_args(argv)
    _corrections, raw, report = build()
    if args.write_output is not None:
        path = args.write_output if args.write_output.is_absolute() else ROOT / args.write_output
        report["install"] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "status": install(path, raw),
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
            "schema": "noether-isv-lexicon-correction-build-failure/1.0",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
