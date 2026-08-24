#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0004 to Work 44."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
EDIT_ID = "ISV021-EDIT-0004"
CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_SHA256 = "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87"
GERMAN_AUTHORITY = Path(
    r"<WORKSPACE_ROOT>\03_projects\noether"
    r"\07_german_canon_control\candidates\ED0015\noether.tex"
)
GERMAN_PIN = (
    2_154_017,
    "51A25101C04877AE740989E72B2AD65A7A7E65B081077C4A518BF1737AD5B907",
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)

# EDIT-0004 is sequenced after the already frozen Paper-45 EDIT-0003.
PREDECESSOR = {
    "44-book-isv.tex": (
        168_422,
        "1B7432A5D2D8BF31D286CCDE43D6935BE3619C06D6C3582B60BF680591625A68",
    ),
    "45-isv.tex": (
        26_043,
        "403E22F8770C9180ED2A54430CDE0E09F6E3DDF919115413E11A05CFA16B8C11",
    ),
    "base-papers1-43-isv.tex": (
        1_894_577,
        "EACFE1473BBF5D82A4B07309C33787A198FE9B111F2228323D4A6076578D389E",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}

SUCCESSOR = {
    "44-book-isv.tex": (
        168_427,
        "D3029CFFB856ACF30E55DEA6086AE3E63F90AA733BBD1B2F0E4DC19D9CB05F88",
    ),
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": PREDECESSOR["base-papers1-43-isv.tex"],
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}

# One-based Unicode-character columns against the exact EDIT-0002 Work-44
# bytes.  Repeated short surfaces are bound to these locators, never replaced
# globally.  R018 is the sole intended line/paragraph-structure change.
LOCATOR_MANIFEST: list[dict[str, Any]] = [
    {"after": "Grupovy", "before": "Grupovo", "category": "prsten", "column": 13, "file": "44-book-isv.tex", "id": "R001", "line": 65},
    {"after": "prěkriženyh", "before": "skrěženyh", "category": "toc", "column": 22, "file": "44-book-isv.tex", "id": "R002", "line": 81},
    {"after": "prěkriženyh", "before": "skrěženyh", "category": "toc", "column": 36, "file": "44-book-isv.tex", "id": "R003", "line": 83},
    {"after": "prěkrižene", "before": "skrěžene", "category": "toc", "column": 48, "file": "44-book-isv.tex", "id": "R004", "line": 84},
    {"after": "grupovy", "before": "grupovo", "category": "prsten", "column": 39, "file": "44-book-isv.tex", "id": "R005", "line": 101},
    {"after": "libovoljny", "before": "libovoljno", "category": "prsten", "column": 28, "file": "44-book-isv.tex", "id": "R006", "line": 102},
    {"after": "ktory", "before": "ktore", "category": "prsten", "column": 46, "file": "44-book-isv.tex", "id": "R007", "line": 126},
    {"after": "drugi", "before": "drugo", "category": "prsten", "column": 13, "file": "44-book-isv.tex", "id": "R008", "line": 127},
    {"after": "toj", "before": "to", "category": "prsten", "column": 30, "file": "44-book-isv.tex", "id": "R009", "line": 127},
    {"after": "izomorfny", "before": "izomorfno", "category": "prsten", "column": 73, "file": "44-book-isv.tex", "id": "R010", "line": 148},
    {"after": "linearna", "before": "linearnaja", "category": "morphology", "column": 5, "file": "44-book-isv.tex", "id": "R011", "line": 261},
    {"after": "razširjujući", "before": "razširjujuće", "category": "prsten", "column": 249, "file": "44-book-isv.tex", "id": "R012", "line": 339},
    {"after": "Grupovy", "before": "Grupovo", "category": "prsten", "column": 20, "file": "44-book-isv.tex", "id": "R013", "line": 643},
    {"after": "grupovy", "before": "grupovo", "category": "prsten", "column": 7, "file": "44-book-isv.tex", "id": "R014", "line": 649},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 44, "file": "44-book-isv.tex", "id": "R015", "line": 1236},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 54, "file": "44-book-isv.tex", "id": "R016", "line": 1238},
    {"after": "izomorfny", "before": "izomorfno", "category": "prsten", "column": 79, "file": "44-book-isv.tex", "id": "R017", "line": 1324},
    {"after": "izomorfizm", "before": "izo-\n\nmorfizm", "category": "page_break", "column": 658, "file": "44-book-isv.tex", "id": "R018", "line": 1336},
    {"after": "ktory", "before": "ktoro", "category": "prsten", "column": 471, "file": "44-book-isv.tex", "id": "R019", "line": 1462},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 193, "file": "44-book-isv.tex", "id": "R020", "line": 1470},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 456, "file": "44-book-isv.tex", "id": "R021", "line": 1470},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 636, "file": "44-book-isv.tex", "id": "R022", "line": 1472},
    {"after": "Matricny", "before": "Matricno", "category": "prsten", "column": 1, "file": "44-book-isv.tex", "id": "R023", "line": 1479},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 79, "file": "44-book-isv.tex", "id": "R024", "line": 1479},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 344, "file": "44-book-isv.tex", "id": "R025", "line": 1493},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 57, "file": "44-book-isv.tex", "id": "R026", "line": 1526},
    {"after": "razširjeny", "before": "razširjeno", "category": "prsten", "column": 64, "file": "44-book-isv.tex", "id": "R027", "line": 1567},
    {"after": "matricny", "before": "matricno", "category": "prsten", "column": 143, "file": "44-book-isv.tex", "id": "R028", "line": 1575},
    {"after": "vsaky", "before": "vsako", "category": "prsten", "column": 178, "file": "44-book-isv.tex", "id": "R029", "line": 1687},
    {"after": "Vsaky", "before": "Vsako", "category": "left_ideal", "column": 10, "file": "44-book-isv.tex", "id": "R030", "line": 1768},
    {"after": "izomorfny", "before": "izomorfno", "category": "left_ideal", "column": 37, "file": "44-book-isv.tex", "id": "R031", "line": 1768},
    {"after": "někoje", "before": "nykoje", "category": "typo", "column": 199, "file": "44-book-isv.tex", "id": "R032", "line": 2557},
    {"after": "Vsaky", "before": "Vsako", "category": "prsten", "column": 41, "file": "44-book-isv.tex", "id": "R033", "line": 2561},
    {"after": "ktory", "before": "ktoro", "category": "prsten", "column": 90, "file": "44-book-isv.tex", "id": "R034", "line": 2561},
    {"after": "prosty", "before": "prosto", "category": "prsten", "column": 187, "file": "44-book-isv.tex", "id": "R035", "line": 2561},
    {"after": "Vsaky", "before": "Vsako", "category": "prsten", "column": 24, "file": "44-book-isv.tex", "id": "R036", "line": 2563},
    {"after": "ktory", "before": "ktoro", "category": "prsten", "column": 54, "file": "44-book-isv.tex", "id": "R037", "line": 2563},
    {"after": "izomorfny", "before": "izomorfno", "category": "prsten", "column": 144, "file": "44-book-isv.tex", "id": "R038", "line": 2603},
    {"after": "toj", "before": "to", "category": "prsten", "column": 227, "file": "44-book-isv.tex", "id": "R039", "line": 2603},
    {"after": "izomorfny", "before": "izomorfno", "category": "prsten", "column": 167, "file": "44-book-isv.tex", "id": "R040", "line": 2605},
    {"after": "toj", "before": "to", "category": "prsten", "column": 184, "file": "44-book-isv.tex", "id": "R041", "line": 2613},
    {"after": "izomorfny", "before": "izomorfno", "category": "prsten", "column": 232, "file": "44-book-isv.tex", "id": "R042", "line": 2613},
    {"after": "ktory", "before": "ktoro", "category": "prsten", "column": 265, "file": "44-book-isv.tex", "id": "R043", "line": 2617},
    {"after": "izomorfny", "before": "izomorfno", "category": "prsten", "column": 276, "file": "44-book-isv.tex", "id": "R044", "line": 2617},
]

EXPECTED_LOCATOR_BYTES = 5_332
EXPECTED_LOCATOR_SHA256 = "874891089884BB43922DD3C6A38187ABD18FAE5EF1F5E0B6FFFF0E9F723A6D62"
EXPECTED_CATEGORY_COUNTS = {
    "left_ideal": 2,
    "morphology": 1,
    "page_break": 1,
    "prsten": 36,
    "toc": 3,
    "typo": 1,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_transaction_core() -> Any:
    data = CORE_PATH.read_bytes()
    if sha256(data) != CORE_SHA256:
        raise RuntimeError("hardened transaction core pin drifted")
    module = types.ModuleType("isv021_edit0002_core")
    module.__file__ = str(CORE_PATH)
    module.__package__ = ""
    code = compile(data, str(CORE_PATH), "exec")
    exec(code, module.__dict__)
    return module


CORE = load_transaction_core()


def authenticate_core_disk() -> dict[str, Any]:
    data = CORE_PATH.read_bytes()
    if sha256(data) != CORE_SHA256:
        raise RuntimeError("on-disk transaction core pin drifted")
    return {"path": str(CORE_PATH), **pin(data)}


def read_cohort() -> dict[str, bytes]:
    return {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def cohort_state(cohort: dict[str, bytes]) -> str:
    pins = observed_pins(cohort)
    if pins == PREDECESSOR:
        return "predecessor"
    if pins == SUCCESSOR:
        return "successor"
    raise RuntimeError(f"live source cohort pin drift: {pins}")


def line_starts(text: str) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    return starts


def exact_locators(text: str) -> list[dict[str, Any]]:
    starts = line_starts(text)
    located: list[dict[str, Any]] = []
    for item in LOCATOR_MANIFEST:
        line_no = int(item["line"])
        column = int(item["column"])
        before = str(item["before"])
        start = starts[line_no - 1] + column - 1
        if text[start : start + len(before)] != before:
            observed = text[start : start + len(before)]
            raise RuntimeError(
                f"locator mismatch at 44-book-isv.tex:{line_no}:{column}: {observed!r}"
            )
        line_end = text.find("\n", starts[line_no - 1])
        if line_end == -1:
            line_end = len(text)
        line_text = text[starts[line_no - 1] : line_end]
        CORE.assert_visible_text(line_text, column - 1, "44-book-isv.tex", line_no)
        record = dict(item)
        record["char_index0"] = start
        record["byte_offset0"] = len(text[:start].encode("utf-8"))
        located.append(record)

    ordered = sorted(located, key=lambda value: int(value["char_index0"]))
    for left, right in zip(ordered, ordered[1:]):
        if int(left["char_index0"]) + len(str(left["before"])) > int(
            right["char_index0"]
        ):
            raise RuntimeError(f"overlapping locators: {left} / {right}")
    if Counter(item["category"] for item in located) != EXPECTED_CATEGORY_COUNTS:
        raise RuntimeError("category-count drift")
    return located


def transform_work44(data: bytes) -> tuple[bytes, dict[str, Any]]:
    text = data.decode("utf-8", errors="strict")
    located = exact_locators(text)
    projected = text
    for item in sorted(located, key=lambda value: int(value["char_index0"]), reverse=True):
        start = int(item["char_index0"])
        before = str(item["before"])
        after = str(item["after"])
        projected = projected[:start] + after + projected[start + len(before) :]

    running_delta = 0
    for item in sorted(located, key=lambda value: int(value["char_index0"])):
        item["projected_char_index0"] = int(item["char_index0"]) + running_delta
        running_delta += len(str(item["after"])) - len(str(item["before"]))

    reversed_text = projected
    for item in sorted(
        located,
        key=lambda value: int(value["projected_char_index0"]),
        reverse=True,
    ):
        start = int(item["projected_char_index0"])
        before = str(item["before"])
        after = str(item["after"])
        if reversed_text[start : start + len(after)] != after:
            raise RuntimeError("projected reverse locator drift")
        reversed_text = (
            reversed_text[:start] + before + reversed_text[start + len(after) :]
        )
    if reversed_text != text:
        raise RuntimeError("exact reverse replay failed")

    before_structure = CORE.structural_signature(text)
    after_structure = CORE.structural_signature(projected)
    allowed_line_delta = before_structure["line_count"] - 2
    for key, value in before_structure.items():
        if key == "line_count":
            if after_structure[key] != allowed_line_delta:
                raise RuntimeError("unexpected Work-44 line-count delta")
        elif after_structure[key] != value:
            raise RuntimeError(f"Work-44 protected structure changed: {key}")
    if text.count("\n") != 2_852 or projected.count("\n") != 2_850:
        raise RuntimeError("Work-44 LF inventory drift")
    if text.count("\n\n") != 629 or projected.count("\n\n") != 628:
        raise RuntimeError("Work-44 paragraph-separator inventory drift")

    canonical_manifest = canonical_bytes(LOCATOR_MANIFEST)
    if len(canonical_manifest) != EXPECTED_LOCATOR_BYTES:
        raise RuntimeError("canonical locator-manifest byte count drift")
    if sha256(canonical_manifest) != EXPECTED_LOCATOR_SHA256:
        raise RuntimeError("canonical locator-manifest hash drift")
    output = projected.encode("utf-8")
    if (len(output), sha256(output)) != SUCCESSOR["44-book-isv.tex"]:
        raise RuntimeError("projected Work-44 successor pin mismatch")

    return output, {
        "locators": [
            {
                **{key: item[key] for key in ("file", "line", "column", "id", "category", "before", "after")},
                "byte_offset0": item["byte_offset0"],
            }
            for item in located
        ],
        "category_counts": dict(sorted(EXPECTED_CATEGORY_COUNTS.items())),
        "locator_manifest": {
            "canonical_bytes": len(canonical_manifest),
            "sha256": sha256(canonical_manifest),
        },
        "exact_reverse": True,
        "visible_text_only": True,
        "protected_structure_equal": True,
        "intended_structural_delta": {
            "operation": "R018",
            "before": "izo-\\n\\nmorfizm",
            "after": "izomorfizm",
            "lf": {"before": 2852, "after": 2850},
            "double_lf": {"before": 629, "after": 628},
        },
        "structural_signature_before": before_structure,
        "structural_signature_after": after_structure,
    }


def authenticate_authority() -> dict[str, Any]:
    data = GERMAN_AUTHORITY.read_bytes()
    if (len(data), sha256(data)) != GERMAN_PIN:
        raise RuntimeError("German authority pin drift")
    return {"path": str(GERMAN_AUTHORITY), **pin(data)}


def source_precheck_report(data: bytes, output: bytes, audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "noether-isv-v021-work44-source-transform-precheck-v1",
        "edit_id": EDIT_ID,
        "status": "SOURCE_TRANSFORM_PRECHECK_ONLY",
        "source": pin(data),
        "projected_source": pin(output),
        "coverage": {
            "sites": len(LOCATOR_MANIFEST),
            "starting_lines": len({item["line"] for item in LOCATOR_MANIFEST}),
            "categories": audit["category_counts"],
        },
        "audit": audit,
        "authority": {"german_ed0015": authenticate_authority()},
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "claims": {"applied": False, "cohort_authenticated": False},
    }


def candidate_report(
    cohort: dict[str, bytes], outputs: dict[str, bytes], audit: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "noether-isv-v021-work44-high-confidence-candidate-v1",
        "edit_id": EDIT_ID,
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": len(LOCATOR_MANIFEST),
            "starting_lines": len({item["line"] for item in LOCATOR_MANIFEST}),
            "categories": audit["category_counts"],
        },
        "audit": audit,
        "authority": {"german_ed0015": authenticate_authority()},
        "semantic_basis": {
            "prsten": "Masculine noun agreement repaired at thirty-six exact loci.",
            "left_ideal": "Masculine lěvy ideal controls both repaired agreements.",
            "toc": "Three table-of-contents outliers now match their established prěkriženy body headings.",
            "morphology": "The isolated Russian-style linearnaja is normalized to line 261's feminine nominative linearna.",
            "typo": "nykoje is normalized to official někoj-.",
            "page_break": "The printed German page-end Iso-/morphismus division is joined as one word and paragraph.",
        },
        "explicit_exclusions": [
            "Vsi lěve idealy at predecessor line 2609 remains outside this tranche.",
            "Inherited formula anomalies and ToC/body source-symbol differences remain unchanged.",
        ],
        "transaction_core": authenticate_core_disk(),
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "claims": {
            "applied": False,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
            "native_or_community_certification": False,
        },
    }


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live Work-44 successor cohort drifted")
    return {
        "schema": "noether-isv-v021-work44-high-confidence-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": len(LOCATOR_MANIFEST),
            "starting_lines": len({item["line"] for item in LOCATOR_MANIFEST}),
            "categories": dict(sorted(EXPECTED_CATEGORY_COUNTS.items())),
        },
        "locator_manifest": {
            "canonical_bytes": EXPECTED_LOCATOR_BYTES,
            "sha256": EXPECTED_LOCATOR_SHA256,
        },
        "authority": {"german_ed0015": authenticate_authority()},
        "transaction_core": authenticate_core_disk(),
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "claims": {
            "applied": True,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
            "native_or_community_certification": False,
        },
    }


def configure_transaction_core() -> None:
    authenticate_core_disk()
    CORE.ROOT = ROOT
    CORE.SOURCE_DIR = SOURCE_DIR
    CORE.EDIT_ID = EDIT_ID
    CORE.SOURCE_ORDER = SOURCE_ORDER
    CORE.PREDECESSOR = PREDECESSOR
    CORE.SUCCESSOR = SUCCESSOR
    CORE.EXPECTED_LOCATOR_SHA256 = EXPECTED_LOCATOR_SHA256


def write_receipt(path: Path, report: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite receipt: {path}")
    CORE.write_exclusive(
        path,
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--write-receipt", type=Path)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--audit-source-only", action="store_true")
    args = parser.parse_args()

    if args.audit_source_only:
        if args.apply or args.write_receipt is not None:
            raise RuntimeError("source-only precheck cannot apply or write a receipt")
        data = (SOURCE_DIR / "44-book-isv.tex").read_bytes()
        if (len(data), sha256(data)) != PREDECESSOR["44-book-isv.tex"]:
            raise RuntimeError("Work-44 source pin drift during source-only precheck")
        output, audit = transform_work44(data)
        report = source_precheck_report(data, output, audit)
    else:
        cohort = read_cohort()
        state = cohort_state(cohort)
        if state == "predecessor":
            work44_output, audit = transform_work44(cohort["44-book-isv.tex"])
            outputs = dict(cohort)
            outputs["44-book-isv.tex"] = work44_output
            if observed_pins(outputs) != SUCCESSOR:
                raise RuntimeError("projected Work-44 cohort pin mismatch")
            report = candidate_report(cohort, outputs, audit)
            if args.apply:
                configure_transaction_core()
                CORE.apply_transaction(cohort, outputs)
                cohort = read_cohort()
                if cohort_state(cohort) != "successor":
                    raise RuntimeError("postapply cohort did not reach exact successor")
                report = successor_report(cohort)
        else:
            if args.apply:
                raise RuntimeError("edit is already applied")
            report = successor_report(cohort)

        if args.write_receipt is not None:
            write_receipt(args.write_receipt, report)

    if args.compact:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
