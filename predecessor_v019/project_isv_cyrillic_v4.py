#!/usr/bin/env python3
"""Current-head, fail-closed Interslavic Cyrillic projection preflight.

Version 4 is an append-only wrapper around the frozen v2 TeX segmenter and
projector.  The historical v3 package remains byte-exact evidence tied to its
EDIT0153 source vector; v4 does not patch or import it.  Instead, v4 admits an
exact subset of the 722 reviewed structural Roman identities by a stable
semantic maximum-multiset signature and authenticates the live four-source
vector against the sealed session-independent state.

The default command is read-only.  It never writes a Cyrillic artifact.  Any
unreviewed v2 issue remains blocking, and READY_IN_MEMORY_ONLY still does not
close the separate one-letter I/V/M or allowed-letter identity reviews.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
STATE_PATH = ROOT / "00_SESSION_INDEPENDENT_STATE_v019.json"
V2_PATH = ROOT / "project_isv_cyrillic_v2.py"
V3_PATH = ROOT / "project_isv_cyrillic_v3.py"
V3_TEST_PATH = ROOT / "test_project_isv_cyrillic_v3.py"
V3_RECEIPT_PATH = ROOT / "CYRILLIC_PROJECTION_V3_VALIDATION_RECEIPT_v019.json"
V3_MANIFEST_PATH = (
    ROOT / "decision_records/ISV019-CYR2-EDIT0153-STRUCTURAL-IDENTITY-MANIFEST.json"
)
SIGNATURE_PATH = ROOT / "CYRILLIC_PROJECTION_V4_STRUCTURAL_SIGNATURE_v019.json"

V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
V3_PIN = (
    24_314,
    "84B845424CB2501289220727B1300280894512EDD137DC13B188A577049AF1B7",
)
V3_TEST_PIN = (
    10_239,
    "FA6EA677A55EC10A7375FEAADCD9C3A24F796012E5E02F9F0C08CE763D004365",
)
V3_RECEIPT_PIN = (
    6_998,
    "00C985D8E200E64D48BEF8849A14C8499AAEABD98C748D563CC3EBD51A64857C",
)
V3_RECEIPT_INTERNAL = (
    "20402F4F55D8150A6D64BF406BA2E9AF5DDBF69BB81A14103FBCC5681DB2DF5C"
)
V3_MANIFEST_PIN = (
    692_764,
    "E6249BDEFEA6713EADAE5AF23C313D38E3DB3EB0DAAC3107A161BC0A0BC3E6E9",
)
V3_MANIFEST_INTERNAL = (
    "D5D33712D70B9541E2D5A05ED134291F87C141B2CE6A29212EB657C1F940D683"
)
SIGNATURE_PIN = (
    6_548,
    "DF3DC40242E51B7153EA8C23FD0F579E82CDE1B83157D8F5D6DFB386F775B7D1",
)
SIGNATURE_ROWS_PIN = (
    4_896,
    "81BB5185B423A06153AE27E29C3DB21C8E04C73C14C27A77A3E8E28FBF714DD2",
)

CURRENT_BASELINE = {
    "head": "ISV019-EDIT-0158",
    "v2_blocked": 1_029,
    "v2_blocked_inventory": (
        "25D90453C2DEB0C1744B5422B05BA8DF3A36A2E71C7FC7AB96B8E351F443FFE9"
    ),
    "v2_unsupported": 423,
    "v2_unsupported_inventory": (
        "ABD1B4570D14FEA79BC90A7EC8529FCA29D146F98E657186402A7774802EC5BB"
    ),
    "v2_roman": 704,
    "v2_roman_inventory": (
        "03F5DE4ABE8AC6582BFFE678153CD941B2E5049E70FEF46FE55010F358672F22"
    ),
    "approved_structural": 722,
    "approved_structural_inventory": (
        "426E17980DE3CF5230436253BE397B5A0B70A2BA5B8776051FEE803E16761517"
    ),
    "remaining": 307,
    "remaining_inventory": (
        "87576B93DC184CA5359B8A17D374A57DC790CC8B561AB6AA98651607E712F4A3"
    ),
}

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)


class ProjectionV4Error(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def describe(data: bytes) -> tuple[int, str]:
    return len(data), sha256(data)


def canonical_json_bytes(value: Any, *, terminal_lf: bool = True) -> bytes:
    suffix = "\n" if terminal_lf else ""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + suffix
    ).encode("utf-8")


def read_regular(path: Path, label: str) -> bytes:
    if not path.exists() or not path.is_file() or path.is_symlink():
        raise ProjectionV4Error(f"missing or unsafe {label}: {path}")
    try:
        return path.read_bytes()
    except OSError as error:
        raise ProjectionV4Error(f"unreadable {label}: {path}") from error


def read_exact(path: Path, pin: tuple[int, str], label: str) -> bytes:
    data = read_regular(path, label)
    observed = describe(data)
    if observed != pin:
        raise ProjectionV4Error(
            f"{label} pin mismatch: expected={pin}; observed={observed}; path={path}"
        )
    return data


def reject_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionV4Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(data: bytes, label: str) -> Any:
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise ProjectionV4Error(f"noncanonical JSON transport: {label}")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ProjectionV4Error(f"invalid UTF-8 JSON: {label}") from error
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ProjectionV4Error(f"JSON must have exactly one terminal LF: {label}")
    try:
        return json.loads(text, object_pairs_hook=reject_duplicate_object)
    except (json.JSONDecodeError, ProjectionV4Error) as error:
        raise ProjectionV4Error(f"invalid JSON: {label}: {error}") from error


def load_v2() -> Any:
    read_exact(V2_PATH, V2_PIN, "frozen v2 implementation")
    spec = importlib.util.spec_from_file_location("isv_cyr2_for_v4", V2_PATH)
    if spec is None or spec.loader is None:
        raise ProjectionV4Error("cannot load frozen v2 implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if tuple(module.SOURCE_ORDER) != SOURCE_ORDER:
        raise ProjectionV4Error("v2 source order drift")
    return module


def validate_lineage() -> dict[str, Any]:
    read_exact(V3_PATH, V3_PIN, "historical v3 implementation")
    read_exact(V3_TEST_PATH, V3_TEST_PIN, "historical v3 independent test")
    read_exact(V3_MANIFEST_PATH, V3_MANIFEST_PIN, "historical structural manifest")
    receipt_raw = read_exact(
        V3_RECEIPT_PATH, V3_RECEIPT_PIN, "historical v3 validation receipt"
    )
    receipt = strict_json(receipt_raw, str(V3_RECEIPT_PATH))
    if not isinstance(receipt, dict):
        raise ProjectionV4Error("historical v3 receipt root drift")
    claimed = receipt.get("receipt_sha256_excluding_this_field")
    receipt_without = copy.deepcopy(receipt)
    receipt_without.pop("receipt_sha256_excluding_this_field", None)
    observed = sha256(canonical_json_bytes(receipt_without))
    if claimed != V3_RECEIPT_INTERNAL or observed != V3_RECEIPT_INTERNAL:
        raise ProjectionV4Error("historical v3 receipt internal hash drift")
    dependency = receipt.get("dependencies", {}).get("structural_identity_manifest", {})
    if (
        dependency.get("bytes"),
        dependency.get("sha256"),
        dependency.get("receipt_sha256_excluding_receipt_field"),
    ) != (V3_MANIFEST_PIN[0], V3_MANIFEST_PIN[1], V3_MANIFEST_INTERNAL):
        raise ProjectionV4Error("historical v3 manifest lineage drift")

    signature_raw = read_exact(SIGNATURE_PATH, SIGNATURE_PIN, "v4 structural signature")
    signature = strict_json(signature_raw, str(SIGNATURE_PATH))
    if not isinstance(signature, dict):
        raise ProjectionV4Error("v4 signature root drift")
    if signature.get("schema") != (
        "noether-isv-cyrillic-projection-v4-structural-signature-v1"
    ):
        raise ProjectionV4Error("v4 signature schema drift")
    if signature.get("status") != (
        "REVIEWED_MAXIMUM_MULTISET_FOR_CURRENT_AND_SUCCESSOR_LATIN_HEADS"
    ):
        raise ProjectionV4Error("v4 signature status drift")
    rows = signature.get("rows")
    if not isinstance(rows, list):
        raise ProjectionV4Error("v4 signature rows missing")
    rows_raw = canonical_json_bytes(rows)
    if describe(rows_raw) != SIGNATURE_ROWS_PIN:
        raise ProjectionV4Error("v4 signature rows transport drift")
    if (signature.get("rows_bytes"), signature.get("rows_sha256")) != (
        SIGNATURE_ROWS_PIN
    ):
        raise ProjectionV4Error("v4 signature declared rows pin drift")
    if sum(row.get("count", 0) for row in rows) != 722:
        raise ProjectionV4Error("v4 signature occurrence total drift")
    return signature


def state_canonical(state: dict[str, Any]) -> bytes:
    value = copy.deepcopy(state)
    head = value.get("authoritative_head")
    if not isinstance(head, dict):
        raise ProjectionV4Error("state authoritative head missing")
    verifier = head.get("verifier")
    expected_keys = {
        "path",
        "bytes",
        "sha256",
        "normalization",
        "normalized_sha256",
    }
    if not isinstance(verifier, dict) or set(verifier) != expected_keys:
        raise ProjectionV4Error("state verifier exclusion topology drift")
    del head["verifier"]
    return canonical_json_bytes(value, terminal_lf=False)


def receipt_path_and_pin(record: Any, label: str) -> tuple[Path, tuple[int, str]]:
    if not isinstance(record, dict):
        raise ProjectionV4Error(f"state {label} receipt missing")
    path = record.get("path")
    size = record.get("bytes")
    digest = record.get("sha256")
    if not isinstance(path, str) or not isinstance(size, int) or not isinstance(digest, str):
        raise ProjectionV4Error(f"state {label} receipt topology drift")
    candidate = ROOT / Path(path)
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except ValueError as error:
        raise ProjectionV4Error(f"state {label} path escapes lane root") from error
    return candidate, (size, digest)


def validate_state_object(
    state: dict[str, Any], state_raw: bytes, raws: Mapping[str, bytes]
) -> dict[str, Any]:
    if state.get("schema") != "noether-isv-session-independent-state-v1":
        raise ProjectionV4Error("state schema drift")
    head = state.get("authoritative_head")
    if not isinstance(head, dict):
        raise ProjectionV4Error("state authoritative head missing")
    decision_id = head.get("decision_id")
    if not isinstance(decision_id, str) or not re.fullmatch(r"ISV019-EDIT-\d{4}", decision_id):
        raise ProjectionV4Error("state decision id drift")

    for key in ("ledger", "sidecar", "worklog", "audit_companion", "verifier"):
        path, pin = receipt_path_and_pin(head.get(key), key)
        read_exact(path, pin, f"state-referenced {key}")

    verifier_record = head["verifier"]
    verifier_path = ROOT / verifier_record["path"]
    verifier_raw = read_regular(verifier_path, "state verifier")
    try:
        verifier_text = verifier_raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ProjectionV4Error("state verifier is not UTF-8") from error
    canonical_match = re.search(
        r"\$ExpectedStateCanonicalSha256 = '([0-9A-F]{64})'", verifier_text
    )
    audit_path_match = re.search(
        r"\$AuditPath = Join-Path \$Root '([^']+)'", verifier_text
    )
    audit_bytes_match = re.search(r"\$ExpectedAuditBytes = (\d+)", verifier_text)
    audit_hash_match = re.search(
        r"\$ExpectedAuditSha256 = '([0-9A-F]{64})'", verifier_text
    )
    if not all((canonical_match, audit_path_match, audit_bytes_match, audit_hash_match)):
        raise ProjectionV4Error("state verifier framing drift")
    canonical_digest = sha256(state_canonical(state))
    if canonical_digest != canonical_match.group(1):
        raise ProjectionV4Error("state canonical digest mismatch")
    audit = head["audit_companion"]
    if (
        audit.get("path"),
        audit.get("bytes"),
        audit.get("sha256"),
    ) != (
        audit_path_match.group(1),
        int(audit_bytes_match.group(1)),
        audit_hash_match.group(1),
    ):
        raise ProjectionV4Error("state verifier/audit-companion binding drift")

    source_pins = state.get("source_pins")
    if not isinstance(source_pins, dict):
        raise ProjectionV4Error("state source pins missing")
    expected_source_keys = {f"source_latin/{name}" for name in SOURCE_ORDER}
    if set(source_pins) != expected_source_keys or set(raws) != set(SOURCE_ORDER):
        raise ProjectionV4Error("state/source topology drift")
    source_manifest: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        record = source_pins[f"source_latin/{filename}"]
        observed = describe(raws[filename])
        if not isinstance(record, dict) or observed != (
            record.get("bytes"),
            record.get("sha256"),
        ):
            raise ProjectionV4Error(
                f"state source pin mismatch: {filename}; state={record}; observed={observed}"
            )
        source_manifest.append(
            {"file": filename, "bytes": observed[0], "sha256": observed[1]}
        )

    tooling = state.get("tooling_authorities", {})
    v2_package = tooling.get("cyrillic_projection_v2_scanner", {}).get("package", {})
    v3_package = tooling.get("cyrillic_projection_v3_scanner", {}).get("package", {})
    if (
        v2_package.get("implementation", {}).get("bytes"),
        v2_package.get("implementation", {}).get("sha256"),
    ) != V2_PIN:
        raise ProjectionV4Error("state v2 dependency pin drift")
    if (
        v3_package.get("implementation", {}).get("bytes"),
        v3_package.get("implementation", {}).get("sha256"),
    ) != V3_PIN:
        raise ProjectionV4Error("state historical v3 pin drift")
    if (
        v3_package.get("validation_receipt", {}).get("bytes"),
        v3_package.get("validation_receipt", {}).get("sha256"),
    ) != V3_RECEIPT_PIN:
        raise ProjectionV4Error("state historical v3 receipt pin drift")

    return {
        "status": "PASS_SEALED_HEAD_SOURCE_VECTOR",
        "decision_id": decision_id,
        "state": {"bytes": len(state_raw), "sha256": sha256(state_raw)},
        "state_canonical_sha256_excluding_only_verifier": canonical_digest,
        "verifier": {
            "path": verifier_record["path"],
            "bytes": verifier_record["bytes"],
            "sha256": verifier_record["sha256"],
        },
        "audit_companion": {
            "path": audit["path"],
            "bytes": audit["bytes"],
            "sha256": audit["sha256"],
        },
        "source_manifest": source_manifest,
    }


def validate_head_sources(
    raws: Mapping[str, bytes], state_path: Path = STATE_PATH
) -> dict[str, Any]:
    state_raw = read_regular(state_path, "session-independent state")
    state = strict_json(state_raw, str(state_path))
    if not isinstance(state, dict):
        raise ProjectionV4Error("state root must be an object")
    return validate_state_object(state, state_raw, raws)


def structural_issue(issue: dict[str, Any]) -> bool:
    return (
        "unlisted_structural_roman_identity" in issue["reasons"]
        or issue["token"] == "X"
    )


def signature_key(issue_or_row: dict[str, Any]) -> tuple[str, str, str, tuple[str, ...]]:
    return (
        issue_or_row["file"],
        issue_or_row["token"],
        issue_or_row["role"],
        tuple(issue_or_row["reasons"]),
    )


def structural_signature_rows(issues: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(signature_key(issue) for issue in issues)
    return [
        {
            "file": key[0],
            "token": key[1],
            "role": key[2],
            "reasons": list(key[3]),
            "count": count,
        }
        for key, count in sorted(counts.items())
    ]


def validate_structural_subset(
    structural: Sequence[dict[str, Any]],
    signature: dict[str, Any],
    source_texts: Mapping[str, str],
) -> dict[str, Any]:
    permitted = {signature_key(row): row["count"] for row in signature["rows"]}
    if len(permitted) != len(signature["rows"]):
        raise ProjectionV4Error("duplicate structural signature row")
    observed = Counter(signature_key(issue) for issue in structural)
    for key, count in observed.items():
        if key not in permitted:
            raise ProjectionV4Error(f"unreviewed structural semantic row: {key}")
        if count > permitted[key]:
            raise ProjectionV4Error(
                f"structural semantic count exceeds reviewed maximum: {key}; "
                f"maximum={permitted[key]}; observed={count}"
            )
    for issue in structural:
        if issue["token"] == "X":
            line = source_texts[issue["file"]].splitlines()[issue["line"] - 1]
            if "teorem" not in line.casefold():
                raise ProjectionV4Error("single-letter X outside reviewed theorem context")
    rows = structural_signature_rows(structural)
    rows_raw = canonical_json_bytes(rows)
    return {
        "status": "PASS_REVIEWED_SUBSET",
        "approved_occurrences": len(structural),
        "reviewed_maximum_occurrences": signature["approved_occurrences"],
        "rows": len(rows),
        "rows_bytes": len(rows_raw),
        "rows_sha256": sha256(rows_raw),
        "issue_inventory_sha256": None,
    }


def filter_file_report(v2: Any, file_report: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = copy.deepcopy(file_report)
    original = result["issues"]
    approved = [issue for issue in original if structural_issue(issue)]
    remaining = [issue for issue in original if not structural_issue(issue)]
    mapping = [issue for issue in remaining if v2.has_mapping_block(issue["reasons"])]
    roman = [
        issue
        for issue in remaining
        if "unlisted_structural_roman_identity" in issue["reasons"]
    ]
    issue_types: Counter[str] = Counter()
    for issue in remaining:
        issue_types.update(issue["reasons"])
    approved_stream = canonical_json_bytes(
        [
            [issue["file"], issue["scalar_offset"], issue["token"], issue["token_sha256"]]
            for issue in approved
        ]
    )
    result.update(
        {
            "issues": remaining,
            "issue_type_counts": dict(sorted(issue_types.items())),
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
                "bytes": len(approved_stream),
                "sha256": sha256(approved_stream),
            },
            "status": (
                "BLOCKED_FAIL_CLOSED"
                if remaining or result["unknown_argument_commands"]
                else "READY_IN_MEMORY_ONLY"
            ),
        }
    )
    return result, approved


def scan_raws(
    raws: Mapping[str, bytes], *, head_validation: dict[str, Any] | None = None
) -> dict[str, Any]:
    v2 = load_v2()
    signature = validate_lineage()
    if set(raws) != set(SOURCE_ORDER):
        raise ProjectionV4Error("in-memory source topology drift")
    source_texts: dict[str, str] = {}
    source_manifest: list[dict[str, Any]] = []
    v2_files: list[dict[str, Any]] = []
    all_v2_issues: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        raw = raws[filename]
        if not isinstance(raw, bytes):
            raise ProjectionV4Error(f"source raw must be bytes: {filename}")
        text = v2.strict_transport(raw, filename)
        source_texts[filename] = text
        scanned = v2.scan_text(text, filename)
        public = {key: value for key, value in scanned.items() if key != "projected_text"}
        v2_files.append(public)
        all_v2_issues.extend(public["issues"])
        source_manifest.append(
            {"file": filename, "bytes": len(raw), "sha256": sha256(raw)}
        )

    structural = [issue for issue in all_v2_issues if structural_issue(issue)]
    v2_mapping = [
        issue for issue in all_v2_issues if v2.has_mapping_block(issue["reasons"])
    ]
    v2_roman = [
        issue
        for issue in all_v2_issues
        if "unlisted_structural_roman_identity" in issue["reasons"]
    ]
    upstream_v2 = {
        "blocked_occurrences": len(all_v2_issues),
        "blocked_inventory_sha256": v2.issue_inventory_sha256(all_v2_issues),
        "unsupported_occurrences": len(v2_mapping),
        "unsupported_inventory_sha256": v2.issue_inventory_sha256(v2_mapping),
        "roman_identity_hold_occurrences": len(v2_roman),
        "roman_identity_inventory_sha256": v2.issue_inventory_sha256(v2_roman),
        "parse_errors": 0,
        "coverage_failures": sum(
            1 for file_report in v2_files if file_report["coverage"]["status"] != "PASS"
        ),
        "unknown_argument_commands": sum(
            len(file_report["unknown_argument_commands"]) for file_report in v2_files
        ),
    }
    signature_status = validate_structural_subset(structural, signature, source_texts)
    signature_status["issue_inventory_sha256"] = v2.issue_inventory_sha256(structural)

    files: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    approved: list[dict[str, Any]] = []
    for file_report in v2_files:
        filtered, file_approved = filter_file_report(v2, file_report)
        files.append(filtered)
        remaining.extend(filtered["issues"])
        approved.extend(file_approved)
    if len(approved) != len(structural):
        raise ProjectionV4Error("structural approval consumption drift")

    mapping = [issue for issue in remaining if v2.has_mapping_block(issue["reasons"])]
    roman = [
        issue
        for issue in remaining
        if "unlisted_structural_roman_identity" in issue["reasons"]
    ]
    parse_errors = 0
    coverage_failures = sum(
        1 for file_report in files if file_report["coverage"]["status"] != "PASS"
    )
    unknown = sum(len(file_report["unknown_argument_commands"]) for file_report in files)
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
        "reviewed_structural_identity_maximum": signature["approved_occurrences"],
        "parse_errors": parse_errors,
        "coverage_failures": coverage_failures,
        "unknown_argument_commands": unknown,
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
            if remaining or parse_errors or coverage_failures or unknown
            else "READY_IN_MEMORY_ONLY"
        ),
    }
    report: dict[str, Any] = {
        "schema": "noether-isv-cyrillic-projection-v4-preflight-v1",
        "classification": (
            "read-only deterministic current-head projection preflight with a "
            "reviewed structural maximum multiset; blocked output is not a release"
        ),
        "source_manifest": source_manifest,
        "source_order": list(SOURCE_ORDER),
        "head_validation": head_validation,
        "dependencies": {
            "v2_scanner": {
                "path": V2_PATH.name,
                "bytes": V2_PIN[0],
                "sha256": V2_PIN[1],
            },
            "historical_v3": {
                "path": V3_PATH.name,
                "bytes": V3_PIN[0],
                "sha256": V3_PIN[1],
                "executed": False,
            },
            "historical_v3_validation_receipt": {
                "path": V3_RECEIPT_PATH.name,
                "bytes": V3_RECEIPT_PIN[0],
                "sha256": V3_RECEIPT_PIN[1],
                "internal_receipt": V3_RECEIPT_INTERNAL,
            },
            "structural_maximum_signature": {
                "path": SIGNATURE_PATH.name,
                "bytes": SIGNATURE_PIN[0],
                "sha256": SIGNATURE_PIN[1],
                "rows_bytes": SIGNATURE_ROWS_PIN[0],
                "rows_sha256": SIGNATURE_ROWS_PIN[1],
            },
        },
        "structural_policy": signature_status,
        "upstream_v2": upstream_v2,
        "summary": summary,
        "files": files,
        "limitations": [
            "One-letter I/V/M tokens require a separate context review.",
            "Allowed-letter personal names and titles require a separate completeness review.",
            "READY_IN_MEMORY_ONLY does not freeze Latin sources or authorize publication.",
            "No projected file is written by this module.",
        ],
    }
    report["report_sha256_excluding_this_field"] = sha256(canonical_json_bytes(report))
    return report


def scan_corpus(
    source_dir: Path = SOURCE_DIR, state_path: Path = STATE_PATH
) -> dict[str, Any]:
    raws = {
        filename: read_regular(source_dir / filename, f"Latin source {filename}")
        for filename in SOURCE_ORDER
    }
    head_validation = validate_head_sources(raws, state_path)
    return scan_raws(raws, head_validation=head_validation)


def compact_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report["schema"],
        "classification": report["classification"],
        "source_manifest": report["source_manifest"],
        "head_validation": report["head_validation"],
        "dependencies": report["dependencies"],
        "structural_policy": report["structural_policy"],
        "upstream_v2": report["upstream_v2"],
        "summary": report["summary"],
        "limitations": report["limitations"],
        "report_sha256_excluding_this_field": report[
            "report_sha256_excluding_this_field"
        ],
    }


def expect_failure(label: str, action: Callable[[], Any]) -> dict[str, Any]:
    try:
        action()
    except Exception as error:  # adversarial test boundary
        return {"case": label, "rejected": True, "error_type": type(error).__name__}
    raise ProjectionV4Error(f"hostile case passed: {label}")


def run_self_test() -> dict[str, Any]:
    report = scan_corpus()
    raws = {
        filename: read_regular(SOURCE_DIR / filename, f"Latin source {filename}")
        for filename in SOURCE_ORDER
    }
    state_raw = read_regular(STATE_PATH, "session-independent state")
    state = strict_json(state_raw, str(STATE_PATH))
    signature = validate_lineage()
    v2 = load_v2()
    v2_files = [v2.scan_text(v2.strict_transport(raws[name], name), name) for name in SOURCE_ORDER]
    structural = [
        issue
        for file_report in v2_files
        for issue in file_report["issues"]
        if structural_issue(issue)
    ]
    source_texts = {
        name: v2.strict_transport(raws[name], name) for name in SOURCE_ORDER
    }
    hostiles: list[dict[str, Any]] = []

    unknown = copy.deepcopy(structural)
    unknown[0]["token"] = "XVIII"
    hostiles.append(
        expect_failure(
            "unreviewed_structural_semantic_row",
            lambda: validate_structural_subset(unknown, signature, source_texts),
        )
    )
    excess = copy.deepcopy(structural)
    excess.append(copy.deepcopy(excess[0]))
    hostiles.append(
        expect_failure(
            "structural_count_exceeds_reviewed_maximum",
            lambda: validate_structural_subset(excess, signature, source_texts),
        )
    )
    hostile_texts = dict(source_texts)
    first_x = next(issue for issue in structural if issue["token"] == "X")
    lines = hostile_texts[first_x["file"]].splitlines(keepends=True)
    lines[first_x["line"] - 1] = lines[first_x["line"] - 1].replace(
        "teorem", "tvrdba"
    ).replace("Teorem", "Tvrdba")
    hostile_texts[first_x["file"]] = "".join(lines)
    hostiles.append(
        expect_failure(
            "single_letter_X_outside_theorem_context",
            lambda: validate_structural_subset(structural, signature, hostile_texts),
        )
    )
    hostile_raws = dict(raws)
    hostile_raws["base-papers1-43-isv.tex"] += b" "
    hostiles.append(
        expect_failure(
            "sealed_state_source_mismatch",
            lambda: validate_state_object(state, state_raw, hostile_raws),
        )
    )
    hostile_state = copy.deepcopy(state)
    hostile_state["status"] = "DRIFT"
    hostiles.append(
        expect_failure(
            "state_canonical_digest_mismatch",
            lambda: validate_state_object(hostile_state, state_raw, raws),
        )
    )
    hostile_signature = copy.deepcopy(signature)
    hostile_signature["rows"][0]["count"] -= 1
    hostiles.append(
        expect_failure(
            "weakened_structural_maximum",
            lambda: validate_structural_subset(structural, hostile_signature, source_texts),
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
            "noncanonical_json_transport",
            lambda: strict_json(b'{"a":1}\r\n', "crlf-fixture"),
        )
    )

    if report["head_validation"]["decision_id"] == CURRENT_BASELINE["head"]:
        upstream = report["upstream_v2"]
        expected_upstream = {
            "blocked_occurrences": CURRENT_BASELINE["v2_blocked"],
            "blocked_inventory_sha256": CURRENT_BASELINE["v2_blocked_inventory"],
            "unsupported_occurrences": CURRENT_BASELINE["v2_unsupported"],
            "unsupported_inventory_sha256": CURRENT_BASELINE[
                "v2_unsupported_inventory"
            ],
            "roman_identity_hold_occurrences": CURRENT_BASELINE["v2_roman"],
            "roman_identity_inventory_sha256": CURRENT_BASELINE[
                "v2_roman_inventory"
            ],
            "parse_errors": 0,
            "coverage_failures": 0,
            "unknown_argument_commands": 0,
        }
        if upstream != expected_upstream:
            raise ProjectionV4Error("EDIT0158 upstream v2 census drift")
        if report["summary"]["blocked_occurrences"] != CURRENT_BASELINE["remaining"]:
            raise ProjectionV4Error("EDIT0158 baseline frontier cardinality drift")
        if (
            report["summary"]["blocked_inventory_sha256"]
            != CURRENT_BASELINE["remaining_inventory"]
        ):
            raise ProjectionV4Error("EDIT0158 baseline frontier inventory drift")
        if (
            report["summary"]["approved_structural_identities"]
            != CURRENT_BASELINE["approved_structural"]
        ):
            raise ProjectionV4Error("EDIT0158 structural approval cardinality drift")

    return {
        "schema": "noether-isv-cyrillic-projection-v4-self-test-v1",
        "status": "PASS",
        "hostile_cases": hostiles,
        "hostile_case_count": len(hostiles),
        "head_validation": report["head_validation"],
        "summary": report["summary"],
        "workspace_files_mutated": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only current-head v4 Interslavic Cyrillic preflight"
    )
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--state", type=Path, default=STATE_PATH)
    parser.add_argument("--full-report", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            payload = run_self_test()
            status = payload["status"]
        else:
            report = scan_corpus(args.source_dir, args.state)
            payload = report if args.full_report else compact_summary(report)
            status = report["summary"]["status"]
    except Exception as error:  # fail-closed CLI boundary
        payload = {
            "schema": "noether-isv-cyrillic-projection-v4-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json_bytes(payload))
        return 1
    sys.stdout.buffer.write(canonical_json_bytes(payload))
    if args.require_ready and status != "READY_IN_MEMORY_ONLY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
