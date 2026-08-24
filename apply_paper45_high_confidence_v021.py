#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0003.

The edit is deliberately bounded to seventeen independently replayed visible-
text locators in Paper 45.  The hardened EDIT-0002 transaction engine is loaded
only after its exact bytes are authenticated; this file supplies a new frozen
cohort, locator manifest, transform, and reports without modifying that engine.
"""

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
EDIT_ID = "ISV021-EDIT-0003"
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

PREDECESSOR = {
    "44-book-isv.tex": (
        168_422,
        "1B7432A5D2D8BF31D286CCDE43D6935BE3619C06D6C3582B60BF680591625A68",
    ),
    "45-isv.tex": (
        26_038,
        "636E873287E0127A58DCBF014CB3C0343EF9D4545D90C2A6475E9F1E5F8B8ADD",
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
    "44-book-isv.tex": PREDECESSOR["44-book-isv.tex"],
    "45-isv.tex": (
        26_043,
        "403E22F8770C9180ED2A54430CDE0E09F6E3DDF919115413E11A05CFA16B8C11",
    ),
    "base-papers1-43-isv.tex": PREDECESSOR["base-papers1-43-isv.tex"],
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}

# The key set and ordering below intentionally match the independent canonical
# manifest.  Columns are one-based Unicode-character columns in the exact
# EDIT-0002 successor, not UTF-8 byte columns.
LOCATOR_MANIFEST: list[dict[str, Any]] = [
    {"after": "Čęst", "before": "Čest", "column": 8, "family": "P45-NEXT-WRAP-001", "file": "45-isv.tex", "line": 30},
    {"after": "Čęst", "before": "Čest", "column": 29, "family": "P45-NEXT-WRAP-001", "file": "45-isv.tex", "line": 31},
    {"after": "najmenše", "before": "prinajmenje", "column": 54, "family": "P45-NEXT-001", "file": "45-isv.tex", "line": 55},
    {"after": "zadače", "before": "zadači", "column": 13, "family": "P45-NEXT-002", "file": "45-isv.tex", "line": 89},
    {"after": "k prostějšej", "before": "k prostějši", "column": 20, "family": "P45-NEXT-002", "file": "45-isv.tex", "line": 89},
    {"after": "S obzirom na produktny teorem rezultantov", "before": "S urědnjenjem produktnogo teorema rezultantov", "column": 1, "family": "P45-NEXT-003", "file": "45-isv.tex", "line": 213},
    {"after": "vzame v obzir", "before": "urědni", "column": 1, "family": "P45-NEXT-004", "file": "45-isv.tex", "line": 266},
    {"after": "nahodęt", "before": "nahodet", "column": 20, "family": "P45-NEXT-005", "file": "45-isv.tex", "line": 274},
    {"after": "najmenšim", "before": "prinajmenje", "column": 45, "family": "P45-NEXT-006", "file": "45-isv.tex", "line": 278},
    {"after": "takogo", "before": "takoho", "column": 25, "family": "P45-NEXT-006", "file": "45-isv.tex", "line": 279},
    {"after": "jedinym uslovjem", "before": "jedino uslovjem", "column": 44, "family": "P45-NEXT-007", "file": "45-isv.tex", "line": 327},
    {"after": "navedenom", "before": "navednom", "column": 49, "family": "P45-NEXT-008", "file": "45-isv.tex", "line": 361},
    {"after": "jednakogo", "before": "jednakoho", "column": 30, "family": "P45-NEXT-009", "file": "45-isv.tex", "line": 384},
    {"after": "govoręt", "before": "govoret", "column": 34, "family": "P45-NEXT-010", "file": "45-isv.tex", "line": 458},
    {"after": "primarny komponent", "before": "primarna komponenta", "column": 47, "family": "P45-NEXT-011", "file": "45-isv.tex", "line": 489},
    {"after": "taky stepen", "before": "tak stepen", "column": 27, "family": "P45-NEXT-012", "file": "45-isv.tex", "line": 575},
    {"after": "taky stepen", "before": "tako stepen", "column": 39, "family": "P45-NEXT-012", "file": "45-isv.tex", "line": 590},
]

EXPECTED_LOCATOR_BYTES = 1_966
EXPECTED_LOCATOR_SHA256 = "46D716A8490E90C5514775664E312C1495EC517527645B476CA68393CBDA165A"
EXPECTED_FAMILY_COUNTS = {
    "P45-NEXT-WRAP-001": 2,
    "P45-NEXT-001": 1,
    "P45-NEXT-002": 2,
    "P45-NEXT-003": 1,
    "P45-NEXT-004": 1,
    "P45-NEXT-005": 1,
    "P45-NEXT-006": 2,
    "P45-NEXT-007": 1,
    "P45-NEXT-008": 1,
    "P45-NEXT-009": 1,
    "P45-NEXT-010": 1,
    "P45-NEXT-011": 1,
    "P45-NEXT-012": 2,
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
    core_bytes = CORE_PATH.read_bytes()
    if sha256(core_bytes) != CORE_SHA256:
        raise RuntimeError("hardened transaction core pin drifted")
    module = types.ModuleType("isv021_edit0002_core")
    module.__file__ = str(CORE_PATH)
    module.__package__ = ""
    code = compile(core_bytes, str(CORE_PATH), "exec")
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
        if line_no < 1 or line_no > len(starts):
            raise RuntimeError(f"locator line outside file: {line_no}")
        start = starts[line_no - 1] + column - 1
        if text[start : start + len(before)] != before:
            observed = text[start : start + len(before)]
            raise RuntimeError(
                f"locator mismatch at 45-isv.tex:{line_no}:{column}: {observed!r}"
            )
        line_end = text.find("\n", starts[line_no - 1])
        if line_end == -1:
            line_end = len(text)
        line_text = text[starts[line_no - 1] : line_end]
        CORE.assert_visible_text(line_text, column - 1, "45-isv.tex", line_no)
        record = dict(item)
        record["char_index0"] = start
        record["byte_offset0"] = len(text[:start].encode("utf-8"))
        located.append(record)

    ordered = sorted(located, key=lambda value: int(value["char_index0"]))
    for left, right in zip(ordered, ordered[1:]):
        left_end = int(left["char_index0"]) + len(str(left["before"]))
        if left_end > int(right["char_index0"]):
            raise RuntimeError(f"overlapping locators: {left} / {right}")
    if Counter(item["family"] for item in located) != EXPECTED_FAMILY_COUNTS:
        raise RuntimeError("family-count drift")
    return located


def transform_paper45(data: bytes) -> tuple[bytes, dict[str, Any]]:
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
    if before_structure != after_structure:
        raise RuntimeError("Paper 45 TeX structural signature changed")

    canonical_manifest = canonical_bytes(LOCATOR_MANIFEST)
    if len(canonical_manifest) != EXPECTED_LOCATOR_BYTES:
        raise RuntimeError("canonical locator-manifest byte count drift")
    if sha256(canonical_manifest) != EXPECTED_LOCATOR_SHA256:
        raise RuntimeError("canonical locator-manifest hash drift")

    output = projected.encode("utf-8")
    if (len(output), sha256(output)) != SUCCESSOR["45-isv.tex"]:
        raise RuntimeError("projected Paper 45 successor pin mismatch")
    report_locators = [
        {
            **{key: item[key] for key in ("file", "line", "column", "family", "before", "after")},
            "byte_offset0": item["byte_offset0"],
        }
        for item in located
    ]
    return output, {
        "locators": report_locators,
        "family_counts": dict(sorted(EXPECTED_FAMILY_COUNTS.items())),
        "locator_manifest": {
            "canonical_bytes": len(canonical_manifest),
            "sha256": sha256(canonical_manifest),
        },
        "exact_reverse": True,
        "visible_text_only": True,
        "structure_equal": True,
        "structural_signature": before_structure,
    }


def authenticate_authority() -> dict[str, Any]:
    data = GERMAN_AUTHORITY.read_bytes()
    observed = (len(data), sha256(data))
    if observed != GERMAN_PIN:
        raise RuntimeError(f"German authority pin drift: {observed}")
    return {"path": str(GERMAN_AUTHORITY), **pin(data)}


def candidate_report(
    cohort: dict[str, bytes], outputs: dict[str, bytes], audit: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "noether-isv-v021-paper45-high-confidence-candidate-v1",
        "edit_id": EDIT_ID,
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": len(LOCATOR_MANIFEST),
            "physical_lines": len({item["line"] for item in LOCATOR_MANIFEST}),
            "families": audit["family_counts"],
        },
        "audit": audit,
        "authority": {
            "german_ed0015": authenticate_authority(),
            "line_map": {
                "P45-NEXT-001": [23752],
                "P45-NEXT-002": [23767],
                "P45-NEXT-003": [23805],
                "P45-NEXT-004": [23842, 23844],
                "P45-NEXT-005": [23850],
                "P45-NEXT-006": [23852],
                "P45-NEXT-007": [23866],
                "P45-NEXT-008": [23882],
                "P45-NEXT-009": [23884],
                "P45-NEXT-010": [23911],
                "P45-NEXT-011": [23919, 23921],
                "P45-NEXT-012": [23971, 23978],
            },
        },
        "refinements": [
            "Retain hard-adjective postavjenoj; correct only zadači and the k-governed comparative prostějši.",
            "Use adjectival taky stepen at both German-aligned loci rather than preserving or introducing adverbial tak/tako.",
            "Retain official masculine genitive plural komponentov and repair the locally inconsistent singular primarna komponenta to official primarny komponent.",
        ],
        "explicit_exclusions": [
            "No formula or primary-print anomaly is changed.",
            "The documented capital-P and q_i primary-print dispositions are not reopened.",
            "Variant-sensitive s toj, prěryv, pohodit od, zelo, and sjedinenje remain unchanged.",
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
        raise RuntimeError("live Paper 45 successor cohort drifted")
    return {
        "schema": "noether-isv-v021-paper45-high-confidence-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": len(LOCATOR_MANIFEST),
            "physical_lines": len({item["line"] for item in LOCATOR_MANIFEST}),
            "families": dict(sorted(EXPECTED_FAMILY_COUNTS.items())),
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
    args = parser.parse_args()

    cohort = read_cohort()
    state = cohort_state(cohort)
    if state == "predecessor":
        paper45_output, audit = transform_paper45(cohort["45-isv.tex"])
        outputs = dict(cohort)
        outputs["45-isv.tex"] = paper45_output
        if observed_pins(outputs) != SUCCESSOR:
            raise RuntimeError("projected cohort pin mismatch")
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
