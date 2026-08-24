#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0007."""

from __future__ import annotations

import argparse
from collections import Counter
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
SOURCE_DIR = ROOT / "source_latin"
EDIT_ID = "ISV021-EDIT-0007"
CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_PIN = (
    29_146,
    "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87",
)
AUDIT_PATH = ROOT / "audit_cest_family_basic_orthography_v021.py"
AUDIT_PIN = (
    19_428,
    "7C3A0550A610394513E4CC3344AAA63DA6B89930A9B2FA4EC2FAC8C4282E451D",
)
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
PREDECESSOR = {
    "44-book-isv.tex": (
        168_410,
        "77A0DA8AE3385520C12D91795CE645944AE7CE60F7F7831D3A7CE47BC76A27F5",
    ),
    "45-isv.tex": (
        26_041,
        "90825271429A2D3156FE752E8925D8D43DC34B5B962234DFA2EFD5D425A23FE8",
    ),
    "base-papers1-43-isv.tex": (
        1_894_589,
        "F84470C69F8D54103F7BB0DB38CCBA43D632F3113BBA17FA9E66D450A9384FC2",
    ),
    "bib-isv.tex": (
        10_021,
        "01DDAB0D12E697DDE422B8871CC5587E5AC5A69B66AB8B9E868A998E16CC982C",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": (
        168_410,
        "77A0DA8AE3385520C12D91795CE645944AE7CE60F7F7831D3A7CE47BC76A27F5",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_581,
        "C33CF08D12E98E198C6BCAB122567930DD2466F2A5115E450A4C16274CED44C8",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
EXPECTED_LOCATOR_BYTES = 1_844
EXPECTED_LOCATOR_SHA256 = (
    "CEB7980DC06728F6CBD423FBB2B5AC735A37D0997C062DE47E27549E6CA47379"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate_module(path: Path, expected: tuple[int, str], name: str) -> Any:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"{name} pin drift: {observed}")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


CORE = authenticate_module(CORE_PATH, CORE_PIN, "isv021_edit0002_transaction_core")
AUDIT = authenticate_module(AUDIT_PATH, AUDIT_PIN, "isv021_edit0007_read_only_audit")


def module_receipt(path: Path, expected: tuple[int, str]) -> dict[str, Any]:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"module drift: {path}: {observed}")
    return {"path": str(path), **pin(data)}


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    for data in cohort.values():
        data.decode("utf-8", errors="strict")
    return cohort


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def cohort_state(cohort: dict[str, bytes]) -> str:
    pins = observed_pins(cohort)
    if pins == PREDECESSOR:
        return "predecessor"
    if pins == SUCCESSOR:
        return "successor"
    raise RuntimeError(f"live source cohort pin drift: {pins}")


def reconstruct_candidate(
    cohort: dict[str, bytes]
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if observed_pins(cohort) != PREDECESSOR:
        raise RuntimeError("candidate reconstruction requires exact predecessor")
    report = AUDIT.build_report()
    if report.get("status") != "PASS_READ_ONLY_PROJECTED_CANDIDATE":
        raise RuntimeError("authenticated audit did not pass")
    block = report.get("locator_manifest", {})
    if (block.get("canonical_bytes"), block.get("sha256")) != (
        EXPECTED_LOCATOR_BYTES,
        EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("locator manifest pin drift")
    manifest = block.get("value")
    if not isinstance(manifest, list) or len(manifest) != 12:
        raise RuntimeError("frozen site count drift")
    outputs = AUDIT.project(cohort, manifest)
    if observed_pins(outputs) != SUCCESSOR:
        raise RuntimeError("reconstructed successor pin drift")
    report = {
        **report,
        "schema": "noether-isv-v021-cest-family-basic-orthography-candidate-v1",
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "applicator": {
            "path": str(Path(__file__).resolve()),
            **pin(Path(__file__).read_bytes()),
        },
        "audit_tool": module_receipt(AUDIT_PATH, AUDIT_PIN),
        "transaction_core": module_receipt(CORE_PATH, CORE_PIN),
    }
    return outputs, report


def successor_residue(cohort: dict[str, bytes]) -> dict[str, Any]:
    residue, census = AUDIT.scan_projected(cohort)
    if residue:
        raise RuntimeError(f"nasalized target residue: {residue}")
    expected = AUDIT.EXPECTED_TOKEN_COUNTS.copy()
    for before, count in AUDIT.EXPECTED_REPLACEMENT_COUNTS.items():
        expected[before] -= count
        if not expected[before]:
            del expected[before]
        expected[AUDIT.REPLACEMENTS[before]] += count
    if census != expected:
        raise RuntimeError(f"successor family census drift: {dict(census)}")
    return {
        "nasalized_target_tokens": 0,
        "family_tokens": sum(census.values()),
        "token_census": dict(sorted(census.items())),
        "retained_separate_lexemes": {
            "sčestnikov": census["sčestnikov"],
            "učestjem": census["učestjem"],
        },
    }


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live successor cohort drifted")
    return {
        "schema": "noether-isv-v021-cest-family-basic-orthography-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": 12,
            "physical_lines": 8,
            "forms": {"Čęst": 4, "čęst": 2, "čęsti": 1, "čęstično": 5},
        },
        "locator_manifest": {
            "canonical_bytes": EXPECTED_LOCATOR_BYTES,
            "sha256": EXPECTED_LOCATOR_SHA256,
        },
        "residue": successor_residue(cohort),
        "authorities": AUDIT.authenticate_authorities(),
        "applicator": {
            "path": str(Path(__file__).resolve()),
            **pin(Path(__file__).read_bytes()),
        },
        "audit_tool": module_receipt(AUDIT_PATH, AUDIT_PIN),
        "transaction_core": module_receipt(CORE_PATH, CORE_PIN),
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
    module_receipt(CORE_PATH, CORE_PIN)
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
        outputs, report = reconstruct_candidate(cohort)
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
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=args.compact,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
