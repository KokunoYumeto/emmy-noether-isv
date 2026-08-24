#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0005."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
EDIT_ID = "ISV021-EDIT-0005"
CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_SHA256 = "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87"
DICTIONARY = Path(
    r"<WORKSPACE_ROOT>\01_methodology\claude_fable_program"
    r"\data\interslavic_dictionary_official_snapshot_20260816\source_sheet_basic.csv"
)
DICTIONARY_PIN = (
    8_101_157,
    "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561",
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)

# EDIT-0005 is sequenced after the frozen Paper-45 and Work-44 candidates.
PREDECESSOR = {
    "44-book-isv.tex": (
        168_427,
        "D3029CFFB856ACF30E55DEA6086AE3E63F90AA733BBD1B2F0E4DC19D9CB05F88",
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
    "44-book-isv.tex": PREDECESSOR["44-book-isv.tex"],
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_621,
        "2EA6BC47DDFFB8190B2865A5DD2138628922A517FF1158EE23A2884725E68CD9",
    ),
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}

LOCATOR_MANIFEST: list[dict[str, Any]] = [
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 105, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13060},
    {"after": "nerazložimy", "before": "nerazlozimy", "column": 42, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13068},
    {"after": "razložimy", "before": "razlozimy", "column": 119, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13112},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 194, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13148},
    {"after": "nerazložime", "before": "nerazlozime", "column": 259, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13148},
    {"after": "nerazložimosti", "before": "nerazlozimosti", "column": 35, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13156},
    {"after": "nerazložimosti", "before": "nerazlozimosti", "column": 950, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13156},
    {"after": "nerazložime", "before": "nerazlozime", "column": 83, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13164},
    {"after": "nerazložimosti", "before": "nerazlozimosti", "column": 668, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13164},
    {"after": "nerazložimy", "before": "nerazlozimy", "column": 715, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13164},
    {"after": "razložimosti", "before": "razlozimosti", "column": 740, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13164},
    {"after": "nerazložime", "before": "nerazlozime", "column": 986, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13164},
    {"after": "nerazložime", "before": "nerazlozime", "column": 64, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13170},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 165, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13190},
    {"after": "nerazložime", "before": "nerazlozime", "column": 153, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13220},
    {"after": "nerazložime", "before": "nerazlozime", "column": 392, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13220},
    {"after": "nerazložime", "before": "nerazlozime", "column": 136, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13222},
    {"after": "nerazložime", "before": "nerazlozime", "column": 153, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13242},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 112, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13244},
    {"after": "nerazložime", "before": "nerazlozime", "column": 171, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13244},
    {"after": "nerazložime", "before": "nerazlozime", "column": 289, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13244},
    {"after": "nerazložime", "before": "nerazlozime", "column": 43, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13246},
    {"after": "nerazložime", "before": "nerazlozime", "column": 396, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13252},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 83, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13274},
    {"after": "nerazložimy", "before": "nerazlozimy", "column": 271, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13278},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 313, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13302},
    {"after": "nerazložime", "before": "nerazlozime", "column": 366, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13302},
    {"after": "nerazložime", "before": "nerazlozime", "column": 513, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13302},
    {"after": "nerazložime", "before": "nerazlozime", "column": 51, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13304},
    {"after": "nerazložimost", "before": "nerazlozimost", "column": 1537, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13304},
    {"after": "nerazložimosti", "before": "nerazlozimosti", "column": 241, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13306},
    {"after": "nerazložime", "before": "nerazlozime", "column": 57, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13312},
    {"after": "nerazložimy", "before": "nerazlozimy", "column": 325, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13312},
    {"after": "nerazložime", "before": "nerazlozime", "column": 178, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13314},
    {"after": "nerazložimymi", "before": "nerazlozimymi", "column": 430, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13314},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 142, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13337},
    {"after": "nerazložime", "before": "nerazlozime", "column": 101, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13360},
    {"after": "nerazložimym", "before": "nerazlozimym", "column": 72, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13362},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 358, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13405},
    {"after": "razložimost", "before": "razlozimost", "column": 509, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13405},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 738, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13405},
    {"after": "nerazložimy", "before": "nerazlozimy", "column": 918, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13409},
    {"after": "nerazložime", "before": "nerazlozime", "column": 1129, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13409},
    {"after": "nerazložimyh", "before": "nerazlozimyh", "column": 1332, "family": "ascii_loz_to_lož", "file": "base-papers1-43-isv.tex", "line": 13409},
    {"after": "dodatnogo", "before": "dodatnoho", "column": 288, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 6165},
    {"after": "dobytogo", "before": "dobytoho", "column": 242, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 6230},
    {"after": "svęzanogo", "before": "svęzanoho", "column": 967, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 9293},
    {"after": "ktorogo", "before": "ktoroho", "column": 219, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 16120},
    {"after": "navedenogo", "before": "navedenoho", "column": 393, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 17277},
    {"after": "recipročnogo", "before": "recipročnoho", "column": 127, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 23566},
    {"after": "učinjenogo", "before": "učinjenoho", "column": 125, "family": "genitive_oho_to_ogo", "file": "base-papers1-43-isv.tex", "line": 24580},
]

EXPECTED_LOCATOR_BYTES = 6_969
EXPECTED_LOCATOR_SHA256 = "DE220D8FAE58BBE75F6DE9A9CD17C74F446B9066388C0CDF7820EFDB2464A5C7"
EXPECTED_FAMILY_COUNTS = {"ascii_loz_to_lož": 44, "genitive_oho_to_ogo": 7}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_transaction_core() -> Any:
    data = CORE_PATH.read_bytes()
    if sha256(data) != CORE_SHA256:
        raise RuntimeError("hardened transaction core pin drifted")
    module = types.ModuleType("isv021_edit0002_core")
    module.__file__ = str(CORE_PATH)
    module.__package__ = ""
    exec(compile(data, str(CORE_PATH), "exec"), module.__dict__)
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


def transform_base(data: bytes) -> tuple[bytes, dict[str, Any]]:
    text = data.decode("utf-8", errors="strict")
    starts = line_starts(text)
    located: list[dict[str, Any]] = []
    for item in LOCATOR_MANIFEST:
        line = int(item["line"])
        column = int(item["column"])
        before = str(item["before"])
        index = starts[line - 1] + column - 1
        if text[index : index + len(before)] != before:
            raise RuntimeError(f"locator mismatch at base:{line}:{column}")
        line_end = text.find("\n", starts[line - 1])
        if line_end == -1:
            line_end = len(text)
        CORE.assert_visible_text(text[starts[line - 1] : line_end], column - 1, "base-papers1-43-isv.tex", line)
        record = dict(item)
        record["char_index0"] = index
        record["byte_offset0"] = len(text[:index].encode("utf-8"))
        located.append(record)
    ordered = sorted(located, key=lambda item: int(item["char_index0"]))
    for left, right in zip(ordered, ordered[1:]):
        if int(left["char_index0"]) + len(str(left["before"])) > int(right["char_index0"]):
            raise RuntimeError("locator overlap")
    if Counter(item["family"] for item in located) != EXPECTED_FAMILY_COUNTS:
        raise RuntimeError("family-count drift")

    projected = text
    for item in reversed(ordered):
        index = int(item["char_index0"])
        before = str(item["before"])
        after = str(item["after"])
        projected = projected[:index] + after + projected[index + len(before) :]
    delta = 0
    for item in ordered:
        item["projected_char_index0"] = int(item["char_index0"]) + delta
        delta += len(str(item["after"])) - len(str(item["before"]))
    reversed_text = projected
    for item in sorted(ordered, key=lambda value: int(value["projected_char_index0"]), reverse=True):
        index = int(item["projected_char_index0"])
        before = str(item["before"])
        after = str(item["after"])
        if reversed_text[index : index + len(after)] != after:
            raise RuntimeError("reverse locator mismatch")
        reversed_text = reversed_text[:index] + before + reversed_text[index + len(after) :]
    if reversed_text != text:
        raise RuntimeError("exact reverse replay failed")
    if CORE.structural_signature(projected) != CORE.structural_signature(text):
        raise RuntimeError("protected TeX structure changed")
    if len(re.findall(r"\b(?:ne)?razloz[^\W\d_]*\b", text, flags=re.UNICODE)) != 44:
        raise RuntimeError("predecessor razloz-family count drift")
    if re.search(r"\b(?:ne)?razloz[^\W\d_]*\b", projected, flags=re.UNICODE):
        raise RuntimeError("projected razloz-family residue")
    for item in LOCATOR_MANIFEST:
        if item["family"] == "genitive_oho_to_ogo" and str(item["before"]) in projected:
            raise RuntimeError(f"projected genitive residue: {item['before']}")

    manifest_bytes = canonical_bytes(LOCATOR_MANIFEST)
    if (len(manifest_bytes), sha256(manifest_bytes)) != (EXPECTED_LOCATOR_BYTES, EXPECTED_LOCATOR_SHA256):
        raise RuntimeError("canonical locator-manifest drift")
    output = projected.encode("utf-8")
    if (len(output), sha256(output)) != SUCCESSOR["base-papers1-43-isv.tex"]:
        raise RuntimeError("projected base successor pin mismatch")
    return output, {
        "locators": [
            {**{key: item[key] for key in ("file", "line", "column", "family", "before", "after")}, "byte_offset0": item["byte_offset0"]}
            for item in located
        ],
        "family_counts": dict(sorted(EXPECTED_FAMILY_COUNTS.items())),
        "locator_manifest": {"canonical_bytes": len(manifest_bytes), "sha256": sha256(manifest_bytes)},
        "exact_reverse": True,
        "visible_text_only": True,
        "structure_equal": True,
        "structural_signature": CORE.structural_signature(text),
        "old_form_residue": 0,
    }


def authenticate_dictionary() -> dict[str, Any]:
    data = DICTIONARY.read_bytes()
    if (len(data), sha256(data)) != DICTIONARY_PIN:
        raise RuntimeError("dictionary pin drift")
    observed: dict[str, dict[str, str]] = {}
    with DICTIONARY.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row and row[0] in {"18608", "30231", "2643", "36196", "3512"}:
                observed[row[0]] = {"isv": row[1], "part_of_speech": row[3]}
    if observed.get("18608", {}).get("isv") != "råzložiti" or observed.get("30231", {}).get("isv") != "råzložiti":
        raise RuntimeError("official råzložiti rows drifted")
    if observed.get("2643", {}).get("isv") != "ktory":
        raise RuntimeError("official ktory row drifted")
    return {"path": str(DICTIONARY), **pin(data), "rows": observed}


def source_precheck_report(data: bytes, output: bytes, audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "noether-isv-v021-base-residual-source-transform-precheck-v1",
        "edit_id": EDIT_ID,
        "status": "SOURCE_TRANSFORM_PRECHECK_ONLY",
        "source": pin(data),
        "projected_source": pin(output),
        "coverage": {"sites": len(LOCATOR_MANIFEST), "physical_lines": len({item["line"] for item in LOCATOR_MANIFEST}), "families": audit["family_counts"]},
        "audit": audit,
        "authority": {"official_dictionary": authenticate_dictionary()},
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "claims": {"applied": False, "cohort_authenticated": False},
    }


def candidate_report(cohort: dict[str, bytes], outputs: dict[str, bytes], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "noether-isv-v021-base-residual-families-candidate-v1",
        "edit_id": EDIT_ID,
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "predecessor": {name: pin(data) for name, data in cohort.items()},
        "projected_successor": {name: pin(data) for name, data in outputs.items()},
        "coverage": {"sites": len(LOCATOR_MANIFEST), "physical_lines": len({item["line"] for item in LOCATOR_MANIFEST}), "families": audit["family_counts"]},
        "audit": audit,
        "authority": {"official_dictionary": authenticate_dictionary()},
        "semantic_basis": {
            "ascii_loz_to_lož": "Forty-four localized Paper-19 ASCII-z corruptions join the overwhelmingly established razlož-/nerazlož- family and official råzložiti root.",
            "genitive_oho_to_ogo": "Seven unambiguous masculine/neuter genitives join the official and predominant -ogo house surface without changing meaning.",
        },
        "transaction_core": authenticate_core_disk(),
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "claims": {"applied": False, "build": False, "render": False, "git": False, "network": False, "publication": False, "native_or_community_certification": False},
    }


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live EDIT-0005 successor drifted")
    return {
        "schema": "noether-isv-v021-base-residual-families-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(data) for name, data in cohort.items()},
        "coverage": {"sites": len(LOCATOR_MANIFEST), "physical_lines": len({item["line"] for item in LOCATOR_MANIFEST}), "families": dict(sorted(EXPECTED_FAMILY_COUNTS.items()))},
        "locator_manifest": {"canonical_bytes": EXPECTED_LOCATOR_BYTES, "sha256": EXPECTED_LOCATOR_SHA256},
        "authority": {"official_dictionary": authenticate_dictionary()},
        "transaction_core": authenticate_core_disk(),
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "claims": {"applied": True, "build": False, "render": False, "git": False, "network": False, "publication": False, "native_or_community_certification": False},
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
    CORE.write_exclusive(path, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


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
        data = (SOURCE_DIR / "base-papers1-43-isv.tex").read_bytes()
        if (len(data), sha256(data)) != PREDECESSOR["base-papers1-43-isv.tex"]:
            raise RuntimeError("base source pin drift during source-only precheck")
        output, audit = transform_base(data)
        report = source_precheck_report(data, output, audit)
    else:
        cohort = read_cohort()
        state = cohort_state(cohort)
        if state == "predecessor":
            base_output, audit = transform_base(cohort["base-papers1-43-isv.tex"])
            outputs = dict(cohort)
            outputs["base-papers1-43-isv.tex"] = base_output
            if observed_pins(outputs) != SUCCESSOR:
                raise RuntimeError("projected EDIT-0005 cohort pin mismatch")
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
