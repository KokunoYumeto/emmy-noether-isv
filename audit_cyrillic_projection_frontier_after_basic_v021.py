#!/usr/bin/env python3
"""Read-only Cyrillic projection-frontier audit of the sealed EDIT0012 head."""

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
AUDIT_PATH = ROOT / "audit_complete_basic_extended_letters_v021.py"
AUDIT_PIN = (
    18_616,
    "3D7514BB1D2A736C045FCBDBE8665849DE80326CFB31BD9763B006229FE53E79",
)
SCANNER_PATH = ROOT.parent / "noether_isv_v019_working" / "project_isv_cyrillic_v2.py"
SCANNER_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
ROMAN_IDENTITY_CASEFOLDS = frozenset(
    {
        "ii",
        "iii",
        "iv",
        "vi",
        "vii",
        "viii",
        "ix",
        "x",
        "xi",
        "xii",
        "xiii",
        "xiv",
        "xv",
        "xvi",
        "xvii",
        "xix",
        "xxii",
    }
)
POSTSEAL_PATH = ROOT / "decision_records" / "ISV021-EDIT-0012-POSTSEAL.json"
POSTSEAL_PIN = (
    3_213,
    "857525B4890306E7FBC4CF090F22AEBC191E6C15A8570D0FB0080566ADD57B4A",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate_module(path: Path, expected: tuple[int, str], name: str) -> Any:
    data = path.read_bytes()
    if (len(data), sha256(data)) != expected:
        raise RuntimeError(f"{name} pin drift")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


AUDIT = authenticate_module(AUDIT_PATH, AUDIT_PIN, "isv021_post_basic_latin_audit")
SCANNER = authenticate_module(SCANNER_PATH, SCANNER_PIN, "isv021_post_basic_projection_scanner")


def build_report() -> dict[str, Any]:
    postseal_bytes = POSTSEAL_PATH.read_bytes()
    if (len(postseal_bytes), sha256(postseal_bytes)) != POSTSEAL_PIN:
        raise RuntimeError("EDIT0012 postseal pin drift")
    postseal = json.loads(postseal_bytes.decode("utf-8"))
    if postseal.get("status") != "SEALED_SUCCESSOR":
        raise RuntimeError("EDIT0012 is not sealed")
    # Read the live files directly.  The imported historical helper deliberately
    # pins the EDIT0011 predecessor and therefore cannot authenticate its
    # already-installed EDIT0012 successor through read_cohort().
    cohort = {
        name: (AUDIT.BASE.SOURCE_DIR / name).read_bytes()
        for name in AUDIT.BASE.SOURCE_ORDER
    }
    if {
        name: (len(cohort[name]), sha256(cohort[name]))
        for name in AUDIT.BASE.SOURCE_ORDER
    } != AUDIT.EXPECTED_SUCCESSOR_PINS:
        raise RuntimeError("live EDIT0012 source pins drift")
    all_issues: list[dict[str, Any]] = []
    per_file: dict[str, Any] = {}
    parse_errors = 0
    coverage_failures = 0
    unknown_argument_commands = 0
    for filename in AUDIT.BASE.SOURCE_ORDER:
        result = SCANNER.scan_text(cohort[filename].decode("utf-8"), filename)
        issues = result["issues"]
        all_issues.extend(issues)
        unknown_argument_commands += len(result["unknown_argument_commands"])
        if result["coverage"]["status"] != "PASS":
            coverage_failures += 1
        # scan_text returns only after validate_structure has completed without
        # raising; reaching this point is the exact structural parse pass.
        per_file[filename] = {
            key: result[key]
            for key in (
                "input_bytes",
                "input_sha256",
                "blocked_occurrences",
                "blocked_inventory_sha256",
                "unique_blocked_surfaces",
                "unique_blocked_casefolds",
                "unsupported_occurrences",
                "unsupported_inventory_sha256",
                "unique_unsupported_surfaces",
                "unique_unsupported_casefolds",
                "roman_identity_hold_occurrences",
                "roman_identity_inventory_sha256",
                "unique_roman_identity_hold_surfaces",
                "unique_roman_identity_hold_casefolds",
                "diagnostic_projection_bytes",
                "diagnostic_projection_sha256",
                "status",
            )
        }
    unsupported = [item for item in all_issues if SCANNER.has_mapping_block(item["reasons"])]
    scanner_roman = [
        item
        for item in all_issues
        if "unlisted_structural_roman_identity" in item["reasons"]
    ]
    roman = [
        item for item in all_issues if item["token_casefold"] in ROMAN_IDENTITY_CASEFOLDS
    ]
    non_roman = [
        item
        for item in all_issues
        if item["token_casefold"] not in ROMAN_IDENTITY_CASEFOLDS
    ]
    form_counts: Counter[tuple[str, tuple[str, ...]]] = Counter(
        (item["token_casefold"], tuple(item["reasons"])) for item in all_issues
    )
    ranked = [
        {"token_casefold": token, "reasons": list(reasons), "occurrences": count}
        for (token, reasons), count in sorted(
            form_counts.items(), key=lambda pair: (-pair[1], pair[0][0], pair[0][1])
        )
    ]
    clean_frontier = (
        parse_errors == 0
        and coverage_failures == 0
        and unknown_argument_commands == 0
        and len(non_roman) == 0
    )
    return {
        "schema": "noether-isv-v021-sealed-latin-cyrillic-frontier-audit-v3",
        "status": (
            "PASS_LIVE_SEALED_LATIN_ZERO_NON_ROMAN_PROJECTION_BLOCKS"
            if clean_frontier
            else "REVIEW_LIVE_SEALED_LATIN_PROJECTION_FRONTIER"
        ),
        "sealed_head": {
            "edit_id": postseal["edit_id"],
            "postseal": {"path": str(POSTSEAL_PATH), **pin(postseal_bytes)},
        },
        "live_source_pins": {
            name: pin(cohort[name]) for name in AUDIT.BASE.SOURCE_ORDER
        },
        "projection_frontier": {
            "blocked_occurrences": len(all_issues),
            "blocked_inventory_sha256": SCANNER.issue_inventory_sha256(all_issues),
            "unique_blocked_surfaces": len({item["token"] for item in all_issues}),
            "unique_blocked_casefolds": len({item["token_casefold"] for item in all_issues}),
            "unsupported_occurrences": len(unsupported),
            "unsupported_inventory_sha256": SCANNER.issue_inventory_sha256(unsupported),
            "unique_unsupported_surfaces": len({item["token"] for item in unsupported}),
            "unique_unsupported_casefolds": len({item["token_casefold"] for item in unsupported}),
            "roman_identity_hold_occurrences": len(roman),
            "roman_identity_inventory_sha256": SCANNER.issue_inventory_sha256(roman),
            "unique_roman_identity_hold_surfaces": len({item["token"] for item in roman}),
            "unique_roman_identity_hold_casefolds": len({item["token_casefold"] for item in roman}),
            "scanner_native_roman_hold_occurrences": len(scanner_roman),
            "scanner_native_roman_hold_inventory_sha256": SCANNER.issue_inventory_sha256(scanner_roman),
            "non_roman_block_occurrences": len(non_roman),
            "non_roman_block_inventory_sha256": SCANNER.issue_inventory_sha256(non_roman),
            "unique_non_roman_block_surfaces": len({item["token"] for item in non_roman}),
            "unique_non_roman_block_casefolds": len({item["token_casefold"] for item in non_roman}),
            "parse_errors": parse_errors,
            "coverage_failures": coverage_failures,
            "unknown_argument_commands": unknown_argument_commands,
        },
        "per_file": per_file,
        "ranked_blocked_forms": ranked,
        "roman_identity_policy": {
            "casefold_allowlist": sorted(ROMAN_IDENTITY_CASEFOLDS),
            "rule": "Preserve the finite observed Roman theorem/section numeral inventory byte-identically in the Cyrillic projection; do not treat it as Interslavic lexical text.",
            "standalone_x_evidence": "All 18 standalone X sites are theorem-number labels or exact theorem-number cross-references in base-papers1-43-isv.tex.",
        },
        "issues": all_issues,
        "tools": {
            "extended_letter_audit": {"path": str(AUDIT_PATH), **pin(AUDIT_PATH.read_bytes())},
            "projection_scanner": {"path": str(SCANNER_PATH), **pin(SCANNER_PATH.read_bytes())},
        },
        "claims": {
            "source_writes": 0,
            "projection_writes": 0,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--write-receipt", type=Path)
    args = parser.parse_args()
    report = build_report()
    if args.top >= 0:
        report = dict(report)
        report["ranked_blocked_forms"] = report["ranked_blocked_forms"][: args.top]
        if args.top == 0:
            report.pop("issues", None)
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=args.compact,
        indent=None if args.compact else 2,
    )
    if args.write_receipt is not None:
        if args.write_receipt.exists():
            raise RuntimeError(f"refusing to overwrite receipt: {args.write_receipt}")
        args.write_receipt.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
