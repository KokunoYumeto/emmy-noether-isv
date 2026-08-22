#!/usr/bin/env python3
"""Independent bounded regression audit for the v3 Cyrillic preflight."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
V2 = ROOT / "project_isv_cyrillic_v2.py"
V3 = ROOT / "project_isv_cyrillic_v3.py"
BUILDER = ROOT / "build_edit0153_structural_identity_manifest_v019.py"
MANIFEST = (
    ROOT
    / "decision_records"
    / "ISV019-CYR2-EDIT0153-STRUCTURAL-IDENTITY-MANIFEST.json"
)
PINS = {
    V2: (
        74_914,
        "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
    ),
    V3: (
        24_314,
        "84B845424CB2501289220727B1300280894512EDD137DC13B188A577049AF1B7",
    ),
    BUILDER: (
        11_477,
        "EAE12F1B7617F6E47F2F8E8439C2F8D11C9B2ED855229992BE28C245644F42DA",
    ),
    MANIFEST: (
        692_764,
        "E6249BDEFEA6713EADAE5AF23C313D38E3DB3EB0DAAC3107A161BC0A0BC3E6E9",
    ),
    ROOT / "source_latin" / "44-book-isv.tex": (
        168_422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    ROOT / "source_latin" / "45-isv.tex": (
        26_053,
        "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91",
    ),
    ROOT / "source_latin" / "base-papers1-43-isv.tex": (
        1_892_324,
        "9490F4C09573ABC4FFC97AE80F2DF08330488B7EA2148AD6CC1C8B39756B02E9",
    ),
    ROOT / "source_latin" / "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
    ROOT / "00_SESSION_INDEPENDENT_STATE_v019.json": (
        19_818,
        "BFA86C58C8D165F02064D02C280D3A8AC24D2C7CE243EC166DCF90EAB8CC00FD",
    ),
    ROOT / "NORMALIZATION_DECISIONS_v019.jsonl": (
        710_982,
        "3A9820DD917B8F77C2E8AFFCC8E9F6EAC86E015691EA9FF49C65F5C520B49580",
    ),
    ROOT / "00_SESSION_INDEPENDENT_WORKLOG_v019.jsonl": (
        169_415,
        "1664975401C40DF4D354DA48CE6BD1D3F5712E795AEA3DD929873FD11DD6F36E",
    ),
    ROOT / "verify_session_independent_state_v019.ps1": (
        2_171,
        "C53B64141FF99A11F3DB1BBB2D536A59BFE564FAC57D05DACDAB453F20826140",
    ),
}
MANIFEST_INTERNAL = (
    "D5D33712D70B9541E2D5A05ED134291F87C141B2CE6A29212EB657C1F940D683"
)
EMPTY_SHA = "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
EXPECTED_RUNS = {
    "default": (
        [],
        0,
        4_207,
        "51E116B32A7842D46638AA3AF614EC887597C83AC1126EF2F54C1578EB9598E4",
    ),
    "self_test": (
        ["--self-test"],
        0,
        3_455,
        "F8BFE9E0DC9114981904F62A2E18CCFA52D444401E1FF5DCA9833866DE324DC6",
    ),
    "require_ready": (
        ["--require-ready"],
        2,
        4_207,
        "51E116B32A7842D46638AA3AF614EC887597C83AC1126EF2F54C1578EB9598E4",
    ),
    "full_report": (
        ["--full-report"],
        0,
        3_419_523,
        "897A94C436FB50A5BF500ED0F31DFC9E6E959414313C390F823C7F33245689C6",
    ),
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha256(data)


def duplicate_rejector(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"duplicate key: {key}")
        result[key] = value
    return result


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


def load_v2() -> Any:
    spec = importlib.util.spec_from_file_location("isv_cyr2_cleanroom_v3_test", V2)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v2")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def direct_oracle() -> dict[str, Any]:
    raw = MANIFEST.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise RuntimeError("manifest transport drift")
    manifest = json.loads(
        raw.decode("utf-8", errors="strict"), object_pairs_hook=duplicate_rejector
    )
    without = dict(manifest)
    claimed = without.pop("receipt_sha256_excluding_this_field")
    observed = sha256(canonical_json_bytes(without))
    if claimed != MANIFEST_INTERNAL or observed != MANIFEST_INTERNAL:
        raise RuntimeError("manifest self-receipt drift")

    v2 = load_v2()
    report = v2.scan_corpus(ROOT / "source_latin")
    direct = [
        issue
        for file_report in report["files"]
        for issue in file_report["issues"]
        if "unlisted_structural_roman_identity" in issue["reasons"]
        or issue["token"] == "X"
    ]
    records = manifest["records"]
    if len(direct) != 722 or len(records) != 722:
        raise RuntimeError("structural identity cardinality drift")
    direct_rows = [
        {field: issue[field] for field in ISSUE_FIELDS}
        for issue in direct
    ]
    manifest_rows = [
        {field: record[field] for field in ISSUE_FIELDS}
        for record in records
    ]
    if direct_rows != manifest_rows:
        raise RuntimeError("manifest is not the exact ordered direct issue subset")

    approved = {
        (record["file"], record["scalar_offset"], record["token"])
        for record in records
    }
    all_issues = [issue for file_report in report["files"] for issue in file_report["issues"]]
    remaining = [
        issue
        for issue in all_issues
        if (issue["file"], issue["scalar_offset"], issue["token"]) not in approved
    ]
    mapping = [issue for issue in remaining if v2.has_mapping_block(issue["reasons"])]
    roman = [
        issue
        for issue in remaining
        if "unlisted_structural_roman_identity" in issue["reasons"]
    ]
    if (len(remaining), len(mapping), len(roman)) != (373, 373, 0):
        raise RuntimeError("clean-room remaining census drift")
    inventory = v2.issue_inventory_sha256(remaining)
    if inventory != "257F1118DC0D31C708180F1AC29E2CDEFD5F257712C3E52EB9146B86ACBC0236":
        raise RuntimeError("clean-room remaining inventory drift")
    return {
        "approved": len(approved),
        "remaining_blocked": len(remaining),
        "remaining_unsupported": len(mapping),
        "remaining_roman": len(roman),
        "remaining_inventory_sha256": inventory,
    }


def run_mode(args: list[str]) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    completed = subprocess.run(
        [sys.executable, "-B", str(V3), *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if (
        not completed.stdout.endswith(b"\n")
        or completed.stdout.endswith(b"\n\n")
        or b"\r" in completed.stdout
    ):
        raise RuntimeError("subprocess stdout framing drift")
    payload = json.loads(completed.stdout.decode("utf-8", errors="strict"))
    return completed, payload


def main() -> int:
    if (ROOT / "__pycache__").exists():
        raise RuntimeError("pre-existing lane bytecode residue")
    for path, expected in PINS.items():
        if pin(path) != expected:
            raise RuntimeError(f"input pin drift: {path}")
    before = {str(path): pin(path) for path in PINS}
    oracle = direct_oracle()
    receipts: dict[str, Any] = {}

    for name, (args, expected_exit, expected_bytes, expected_hash) in EXPECTED_RUNS.items():
        repetitions = 2 if name in {"default", "self_test"} else 1
        observed: list[dict[str, Any]] = []
        raw_hashes: list[str] = []
        for _ in range(repetitions):
            completed, payload = run_mode(args)
            row = {
                "exit_code": completed.returncode,
                "stdout_bytes": len(completed.stdout),
                "stdout_sha256": sha256(completed.stdout),
                "stderr_bytes": len(completed.stderr),
                "stderr_sha256": sha256(completed.stderr),
            }
            if (
                row["exit_code"],
                row["stdout_bytes"],
                row["stdout_sha256"],
                row["stderr_bytes"],
                row["stderr_sha256"],
            ) != (expected_exit, expected_bytes, expected_hash, 0, EMPTY_SHA):
                raise RuntimeError(f"mode receipt drift: {name}: {row}")
            if name == "self_test":
                if payload["status"] != "PASS" or payload["hostile_case_count"] != 9:
                    raise RuntimeError("embedded self-test payload drift")
            else:
                summary = payload["summary"]
                if (
                    summary["blocked_occurrences"],
                    summary["unsupported_occurrences"],
                    summary["roman_identity_hold_occurrences"],
                ) != (373, 373, 0):
                    raise RuntimeError(f"mode semantic drift: {name}")
            observed.append(row)
            raw_hashes.append(row["stdout_sha256"])
        if len(set(raw_hashes)) != 1:
            raise RuntimeError(f"mode nondeterminism: {name}")
        receipts[name] = observed

    after = {str(path): pin(path) for path in PINS}
    if before != after:
        raise RuntimeError("bounded no-write guard drift")
    if (ROOT / "__pycache__").exists():
        raise RuntimeError("lane bytecode residue created")

    result = {
        "schema": "noether-isv-cyrillic-v3-independent-test-receipt-v1",
        "status": "PASS",
        "direct_oracle": oracle,
        "mode_receipts": receipts,
        "bounded_files": len(PINS),
        "bounded_no_write_guard": True,
        "lane_pycache_absent": True,
    }
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
