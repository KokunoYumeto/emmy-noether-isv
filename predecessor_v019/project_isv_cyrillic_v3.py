#!/usr/bin/env python3
"""Fail-closed Interslavic Cyrillic preflight with reviewed identities.

Version 3 is an append-only overlay on the frozen v2 TeX segmenter/projector.
It admits only the 722 exact structural identities reviewed against sealed
ISV019-EDIT-0153 bytes.  The overlay changes no Latin source and writes no
Cyrillic output.  Every other v2 issue remains blocking.
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
from typing import Any, Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
V2_PATH = ROOT / "project_isv_cyrillic_v2.py"
MANIFEST_PATH = (
    ROOT
    / "decision_records"
    / "ISV019-CYR2-EDIT0153-STRUCTURAL-IDENTITY-MANIFEST.json"
)

V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
MANIFEST_PIN = (
    692_764,
    "E6249BDEFEA6713EADAE5AF23C313D38E3DB3EB0DAAC3107A161BC0A0BC3E6E9",
)
MANIFEST_INTERNAL_PIN = (
    "D5D33712D70B9541E2D5A05ED134291F87C141B2CE6A29212EB657C1F940D683"
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
        1_892_324,
        "9490F4C09573ABC4FFC97AE80F2DF08330488B7EA2148AD6CC1C8B39756B02E9",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
EXPECTED_V2 = {
    "blocked_occurrences": 1_095,
    "unsupported_occurrences": 489,
    "roman_identity_hold_occurrences": 704,
    "parse_errors": 0,
    "coverage_failures": 0,
    "unknown_argument_commands": 0,
}
EXPECTED_APPROVALS = {
    "records": 722,
    "multi_letter_roman_identities": 704,
    "single_letter_X_theorem_identities": 18,
    "mapping_blocking_structural_identities": 116,
}
EXPECTED_REMAINING = {
    "blocked_occurrences": 373,
    "unsupported_occurrences": 373,
    "roman_identity_hold_occurrences": 0,
    "parse_errors": 0,
    "coverage_failures": 0,
    "unknown_argument_commands": 0,
}

ISSUE_FIELDS = (
    "file",
    "token",
    "token_casefold",
    "token_sha256",
    "scalar_offset",
    "byte_offset",
    "line",
    "column",
    "role",
    "reasons",
    "line_sha256",
    "context_sha256",
)


class ProjectionV3Error(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def read_exact(path: Path, pin: tuple[int, str]) -> bytes:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != pin:
        raise ProjectionV3Error(
            f"pin mismatch: {path}; expected={pin}; observed={observed}"
        )
    return data


def reject_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionV3Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(data: bytes, label: str) -> Any:
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise ProjectionV3Error(f"non-canonical JSON transport: {label}")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ProjectionV3Error(f"invalid UTF-8 JSON: {label}") from error
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ProjectionV3Error(f"JSON must have exactly one terminal LF: {label}")
    try:
        return json.loads(text, object_pairs_hook=reject_duplicate_object)
    except (json.JSONDecodeError, ProjectionV3Error) as error:
        raise ProjectionV3Error(f"invalid JSON: {label}: {error}") from error


def load_v2() -> Any:
    read_exact(V2_PATH, V2_PIN)
    spec = importlib.util.spec_from_file_location("isv_cyr2_for_v3", V2_PATH)
    if spec is None or spec.loader is None:
        raise ProjectionV3Error("cannot load pinned v2 implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def manifest_without_receipt(manifest: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(manifest)
    if "receipt_sha256_excluding_this_field" not in value:
        raise ProjectionV3Error("manifest receipt field missing")
    value.pop("receipt_sha256_excluding_this_field")
    return value


def load_manifest() -> dict[str, Any]:
    payload = read_exact(MANIFEST_PATH, MANIFEST_PIN)
    value = strict_json(payload, str(MANIFEST_PATH))
    if not isinstance(value, dict):
        raise ProjectionV3Error("manifest root must be an object")
    observed = sha256(canonical_json_bytes(manifest_without_receipt(value)))
    claimed = value.get("receipt_sha256_excluding_this_field")
    if claimed != MANIFEST_INTERNAL_PIN or observed != MANIFEST_INTERNAL_PIN:
        raise ProjectionV3Error(
            f"manifest internal receipt mismatch: claimed={claimed}; observed={observed}"
        )
    return value


def issue_key(issue: dict[str, Any]) -> tuple[str, int, str]:
    return issue["file"], issue["scalar_offset"], issue["token"]


def issue_projection(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record[field] for field in ISSUE_FIELDS}


def expected_excerpt(text: str, issue: dict[str, Any]) -> str:
    scalar = issue["scalar_offset"]
    return text[
        max(0, scalar - 80) : min(
            len(text), scalar + len(issue["token"]) + 120
        )
    ]


def structural_issues(v2_report: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for file_report in v2_report["files"]:
        for issue in file_report["issues"]:
            if (
                "unlisted_structural_roman_identity" in issue["reasons"]
                or issue["token"] == "X"
            ):
                result.append(issue)
    return result


def validate_manifest(
    manifest: dict[str, Any],
    v2_report: dict[str, Any],
    source_texts: dict[str, str],
) -> dict[tuple[str, int, str], dict[str, Any]]:
    if manifest.get("schema") != (
        "noether-isv-cyrillic-edit0153-structural-identity-manifest-v1"
    ):
        raise ProjectionV3Error("manifest schema drift")
    if manifest.get("status") != "reviewed_candidate_not_yet_registered":
        raise ProjectionV3Error("manifest status drift")
    if manifest.get("classification_head") != "ISV019-EDIT-0153":
        raise ProjectionV3Error("manifest head drift")
    if manifest.get("source_manifest") != v2_report["source_manifest"]:
        raise ProjectionV3Error("manifest source vector drift")

    scanner = manifest.get("scanner")
    if not isinstance(scanner, dict):
        raise ProjectionV3Error("manifest scanner block missing")
    if scanner.get("path") != "project_isv_cyrillic_v2.py":
        raise ProjectionV3Error("manifest scanner path drift")
    if (scanner.get("bytes"), scanner.get("sha256")) != V2_PIN:
        raise ProjectionV3Error("manifest scanner pin drift")
    for key, expected in EXPECTED_V2.items():
        if scanner.get(key) != expected or v2_report["summary"].get(key) != expected:
            raise ProjectionV3Error(f"v2 census drift at {key}")

    summary = manifest.get("summary")
    if not isinstance(summary, dict):
        raise ProjectionV3Error("manifest summary missing")
    for key, expected in EXPECTED_APPROVALS.items():
        if summary.get(key) != expected:
            raise ProjectionV3Error(f"manifest approval count drift at {key}")

    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_APPROVALS["records"]:
        raise ProjectionV3Error("manifest records cardinality drift")
    if [record.get("ordinal") for record in records] != list(range(1, 723)):
        raise ProjectionV3Error("manifest ordinal sequence drift")

    direct = structural_issues(v2_report)
    direct_by_key = {issue_key(issue): issue for issue in direct}
    if len(direct_by_key) != 722 or len(direct) != 722:
        raise ProjectionV3Error("direct structural issue cardinality drift")

    approvals: dict[tuple[str, int, str], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ProjectionV3Error("manifest record must be an object")
        key = issue_key(record)
        if key in approvals:
            raise ProjectionV3Error(f"duplicate manifest locator: {key}")
        direct_issue = direct_by_key.get(key)
        if direct_issue is None:
            raise ProjectionV3Error(f"manifest locator absent from current scan: {key}")
        if issue_projection(record) != issue_projection(direct_issue):
            raise ProjectionV3Error(f"manifest issue fields drift: {key}")
        if record.get("adjudication") != "preserve_exact_latin_identity":
            raise ProjectionV3Error(f"manifest adjudication drift: {key}")
        subrole = record.get("subrole")
        if "unlisted_structural_roman_identity" in direct_issue["reasons"]:
            if subrole != "multi_letter_roman_identity":
                raise ProjectionV3Error(f"multi-letter subrole drift: {key}")
        elif direct_issue["token"] == "X":
            if subrole != "single_letter_X_theorem_identity":
                raise ProjectionV3Error(f"X subrole drift: {key}")
            source_line = source_texts[record["file"]].splitlines()[record["line"] - 1]
            if "teorem" not in source_line.casefold():
                raise ProjectionV3Error(f"X theorem context drift: {key}")
        else:
            raise ProjectionV3Error(f"unrecognized structural class: {key}")
        if record.get("context_excerpt") != expected_excerpt(
            source_texts[record["file"]], direct_issue
        ):
            raise ProjectionV3Error(f"manifest context excerpt drift: {key}")
        approvals[key] = record

    if set(approvals) != set(direct_by_key):
        raise ProjectionV3Error("manifest/direct structural issue set mismatch")
    return approvals


def filter_file_report(
    v2: Any,
    file_report: dict[str, Any],
    approvals: dict[tuple[str, int, str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(file_report)
    original_issues = result["issues"]
    approved = [issue for issue in original_issues if issue_key(issue) in approvals]
    remaining = [issue for issue in original_issues if issue_key(issue) not in approvals]
    mapping = [issue for issue in remaining if v2.has_mapping_block(issue["reasons"])]
    roman = [
        issue
        for issue in remaining
        if "unlisted_structural_roman_identity" in issue["reasons"]
    ]
    approved_bytes = canonical_json_bytes(
        [
            [issue["file"], issue["scalar_offset"], issue["token"], issue["token_sha256"]]
            for issue in approved
        ]
    )
    result.update(
        {
            "issues": remaining,
            "blocked_occurrences": len(remaining),
            "blocked_inventory_sha256": v2.issue_inventory_sha256(remaining),
            "unique_blocked_surfaces": len({issue["token"] for issue in remaining}),
            "unique_blocked_casefolds": len(
                {issue["token_casefold"] for issue in remaining}
            ),
            "unsupported_occurrences": len(mapping),
            "unsupported_inventory_sha256": v2.issue_inventory_sha256(mapping),
            "unique_unsupported_surfaces": len({issue["token"] for issue in mapping}),
            "unique_unsupported_casefolds": len(
                {issue["token_casefold"] for issue in mapping}
            ),
            "roman_identity_hold_occurrences": len(roman),
            "roman_identity_inventory_sha256": v2.issue_inventory_sha256(roman),
            "unique_roman_identity_hold_surfaces": len(
                {issue["token"] for issue in roman}
            ),
            "unique_roman_identity_hold_casefolds": len(
                {issue["token_casefold"] for issue in roman}
            ),
            "approved_structural_identities": len(approved),
            "approved_structural_identity_stream": {
                "bytes": len(approved_bytes),
                "sha256": sha256(approved_bytes),
            },
            "status": (
                "BLOCKED_FAIL_CLOSED"
                if remaining or result["unknown_argument_commands"]
                else "READY_IN_MEMORY_ONLY"
            ),
        }
    )
    return result, approved


def scan_corpus() -> dict[str, Any]:
    v2 = load_v2()
    for filename, pin in SOURCE_PINS.items():
        read_exact(SOURCE_DIR / filename, pin)
    manifest = load_manifest()
    v2_report = v2.scan_corpus(SOURCE_DIR)
    source_texts = {
        filename: (SOURCE_DIR / filename).read_text(encoding="utf-8")
        for filename in v2.SOURCE_ORDER
    }
    approvals = validate_manifest(manifest, v2_report, source_texts)

    files: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    approved: list[dict[str, Any]] = []
    for file_report in v2_report["files"]:
        filtered, file_approved = filter_file_report(v2, file_report, approvals)
        files.append(filtered)
        remaining.extend(filtered["issues"])
        approved.extend(file_approved)

    if len(approved) != 722 or {issue_key(issue) for issue in approved} != set(approvals):
        raise ProjectionV3Error("approval consumption mismatch")
    mapping = [issue for issue in remaining if v2.has_mapping_block(issue["reasons"])]
    roman = [
        issue
        for issue in remaining
        if "unlisted_structural_roman_identity" in issue["reasons"]
    ]
    summary = {
        "files": len(files),
        "blocked_occurrences": len(remaining),
        "blocked_inventory_sha256": v2.issue_inventory_sha256(remaining),
        "unique_blocked_surfaces": len({issue["token"] for issue in remaining}),
        "unique_blocked_casefolds": len(
            {issue["token_casefold"] for issue in remaining}
        ),
        "unsupported_occurrences": len(mapping),
        "unsupported_inventory_sha256": v2.issue_inventory_sha256(mapping),
        "unique_unsupported_surfaces": len({issue["token"] for issue in mapping}),
        "unique_unsupported_casefolds": len(
            {issue["token_casefold"] for issue in mapping}
        ),
        "roman_identity_hold_occurrences": len(roman),
        "roman_identity_inventory_sha256": v2.issue_inventory_sha256(roman),
        "unique_roman_identity_hold_surfaces": len(
            {issue["token"] for issue in roman}
        ),
        "unique_roman_identity_hold_casefolds": len(
            {issue["token_casefold"] for issue in roman}
        ),
        "approved_structural_identities": len(approved),
        "approved_multi_letter_roman_identities": 704,
        "approved_single_letter_X_theorem_identities": 18,
        "parse_errors": 0,
        "coverage_failures": 0,
        "unknown_argument_commands": sum(
            len(file_report["unknown_argument_commands"]) for file_report in files
        ),
        "by_file": {
            file_report["label"]: {
                key: file_report[key]
                for key in (
                    "blocked_occurrences",
                    "blocked_inventory_sha256",
                    "unsupported_occurrences",
                    "unsupported_inventory_sha256",
                    "roman_identity_hold_occurrences",
                    "roman_identity_inventory_sha256",
                    "approved_structural_identities",
                )
            }
            for file_report in files
        },
        "status": (
            "BLOCKED_FAIL_CLOSED"
            if remaining
            or any(file_report["unknown_argument_commands"] for file_report in files)
            else "READY_IN_MEMORY_ONLY"
        ),
    }
    for key, expected in EXPECTED_REMAINING.items():
        if summary[key] != expected:
            raise ProjectionV3Error(
                f"v3 remaining census drift at {key}: expected={expected}; "
                f"actual={summary[key]}"
            )
    if summary["by_file"]["44-book-isv.tex"]["blocked_occurrences"] != 0:
        raise ProjectionV3Error("book structural identities were not fully admitted")
    if summary["by_file"]["45-isv.tex"]["blocked_occurrences"] != 0:
        raise ProjectionV3Error("Paper45 structural identities were not fully admitted")
    if summary["by_file"]["bib-isv.tex"]["blocked_occurrences"] != 0:
        raise ProjectionV3Error("bibliography structural identities were not fully admitted")
    if summary["by_file"]["base-papers1-43-isv.tex"]["blocked_occurrences"] != 373:
        raise ProjectionV3Error("base remaining census drift")

    return {
        "schema": "noether-isv-cyrillic-projection-v3-preflight-v1",
        "classification": (
            "read-only deterministic projection preflight with exact reviewed "
            "structural identities; blocked output is not a release"
        ),
        "source_manifest": v2_report["source_manifest"],
        "source_order": list(v2.SOURCE_ORDER),
        "dependencies": {
            "v2_scanner": {
                "path": "project_isv_cyrillic_v2.py",
                "bytes": V2_PIN[0],
                "sha256": V2_PIN[1],
            },
            "structural_identity_manifest": {
                "path": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
                "bytes": MANIFEST_PIN[0],
                "sha256": MANIFEST_PIN[1],
                "internal_receipt": MANIFEST_INTERNAL_PIN,
            },
        },
        "approval_policy": manifest["decision"],
        "summary": summary,
        "files": [
            {key: value for key, value in file_report.items() if key != "projected_text"}
            for file_report in files
        ],
        "limitations": [
            "The remaining 373 blockers require complete foreign/citation identity protection or whole-family integrated-name adjudication.",
            "One-letter I/V/M tokens remain outside this manifest and require a separate context review.",
            "Allowed-letter personal names and titles remain outside unsupported-letter detection.",
            "A successful preflight does not freeze Latin sources or authorize publication.",
            "No projected file is written by this module.",
        ],
    }


def compact_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report["schema"],
        "classification": report["classification"],
        "source_manifest": report["source_manifest"],
        "dependencies": report["dependencies"],
        "summary": report["summary"],
        "limitations": report["limitations"],
    }


def expect_failure(label: str, action: Callable[[], Any]) -> dict[str, Any]:
    try:
        action()
    except Exception as error:  # adversarial test boundary
        return {"case": label, "rejected": True, "error_type": type(error).__name__}
    raise ProjectionV3Error(f"hostile case passed: {label}")


def run_self_test() -> dict[str, Any]:
    v2 = load_v2()
    manifest = load_manifest()
    v2_report = v2.scan_corpus(SOURCE_DIR)
    source_texts = {
        filename: (SOURCE_DIR / filename).read_text(encoding="utf-8")
        for filename in v2.SOURCE_ORDER
    }
    validate_manifest(manifest, v2_report, source_texts)
    hostiles: list[dict[str, Any]] = []

    def mutated(action: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        value = copy.deepcopy(manifest)
        action(value)
        return value

    hostiles.append(
        expect_failure(
            "missing_record",
            lambda: validate_manifest(
                mutated(lambda value: value["records"].pop()), v2_report, source_texts
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "duplicate_record",
            lambda: validate_manifest(
                mutated(lambda value: value["records"].append(value["records"][0])),
                v2_report,
                source_texts,
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "wrong_line_hash",
            lambda: validate_manifest(
                mutated(
                    lambda value: value["records"][0].__setitem__(
                        "line_sha256", "0" * 64
                    )
                ),
                v2_report,
                source_texts,
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "wrong_context_excerpt",
            lambda: validate_manifest(
                mutated(
                    lambda value: value["records"][0].__setitem__(
                        "context_excerpt", "drift"
                    )
                ),
                v2_report,
                source_texts,
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "wrong_source_manifest",
            lambda: validate_manifest(
                mutated(
                    lambda value: value["source_manifest"][0].__setitem__(
                        "sha256", "0" * 64
                    )
                ),
                v2_report,
                source_texts,
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "wrong_scanner_pin",
            lambda: validate_manifest(
                mutated(
                    lambda value: value["scanner"].__setitem__("sha256", "0" * 64)
                ),
                v2_report,
                source_texts,
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "wrong_head",
            lambda: validate_manifest(
                mutated(
                    lambda value: value.__setitem__(
                        "classification_head", "ISV019-EDIT-0152"
                    )
                ),
                v2_report,
                source_texts,
            ),
        )
    )
    hostiles.append(
        expect_failure(
            "duplicate_json_key",
            lambda: strict_json(b'{"a":1,"a":2}\n', "duplicate-key-fixture"),
        )
    )
    hostiles.append(
        expect_failure(
            "noncanonical_transport",
            lambda: strict_json(b'{"a":1}\r\n', "crlf-fixture"),
        )
    )
    report = scan_corpus()
    return {
        "schema": "noether-isv-cyrillic-v3-self-test-v1",
        "status": "PASS",
        "hostile_cases": hostiles,
        "hostile_case_count": len(hostiles),
        "summary": report["summary"],
        "workspace_files_mutated": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only fail-closed v3 Interslavic Cyrillic preflight"
    )
    parser.add_argument("--full-report", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        payload = run_self_test()
        report_status = payload["status"]
    else:
        report = scan_corpus()
        payload = report if args.full_report else compact_summary(report)
        report_status = report["summary"]["status"]
    # Write canonical UTF-8 bytes directly.  On Windows, ``print`` otherwise
    # inherits the active console code page; full reports containing names such
    # as Weitzenböck then cease to be portable machine-readable JSON.
    sys.stdout.buffer.write(canonical_json_bytes(payload))
    if args.require_ready and report_status != "READY_IN_MEMORY_ONLY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
