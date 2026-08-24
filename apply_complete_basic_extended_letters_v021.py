#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0012."""

from __future__ import annotations

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
SOURCE_DIR = ROOT / "source_latin"
EDIT_ID = "ISV021-EDIT-0012"
REVISION = "R1"
CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_PIN = (
    29_146,
    "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87",
)
AUDIT_PATH = ROOT / "audit_complete_basic_extended_letters_v021.py"
AUDIT_PIN = (
    18_616,
    "3D7514BB1D2A736C045FCBDBE8665849DE80326CFB31BD9763B006229FE53E79",
)
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
PREDECESSOR = {
    "44-book-isv.tex": (
        168_456,
        "DAF592E5F9D92186B1B7E8E7D64288D04053CE3C1FE10A48C96082F6E52F8103",
    ),
    "45-isv.tex": (
        26_043,
        "FEF628A7947285FAE15C7F5724BD3C87F027911D2C36E16A546CCEB69AF5CC33",
    ),
    "base-papers1-43-isv.tex": (
        1_894_798,
        "03995C2AC0455516F370C9752903D9826B8B1CF6FA4981BEEF90B40AC34CD6FE",
    ),
    "bib-isv.tex": (
        10_020,
        "FFA7F9FD323A7C0B134986EDFE0E1484C04C61ECA576B60DB6E2C2B70B9778E3",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": (
        168_384,
        "FFEAE898972515A69D9BCD4930ECEEF2C91DD7114E0CA0B0F64E2157ED32E698",
    ),
    "45-isv.tex": (
        26_036,
        "E49033F3C3004F921CD234610425905FF1D46405107D8EB99BC431864BB4473D",
    ),
    "base-papers1-43-isv.tex": (
        1_893_083,
        "237FFE1460816EAF8CCD6E00F9500F816A285830CE62E28E49CECB94685B16E9",
    ),
    "bib-isv.tex": (
        10_016,
        "D14F600C71E911F49F0A81B85B2C476F7BED490D597E2045AC55744774D201B1",
    ),
}
EXPECTED_LOCATOR_BYTES = 291_190
EXPECTED_LOCATOR_SHA256 = (
    "D41F4B6588FA74D999DE749D46DC507F27600651CCC7B00E9E1DC86005A64994"
)
EXPECTED_SITES = 1_798
EXPECTED_PHYSICAL_LINES = 1_042


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
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


CORE = authenticate_module(CORE_PATH, CORE_PIN, "isv021_edit0012_transaction_core")
AUDIT = authenticate_module(AUDIT_PATH, AUDIT_PIN, "isv021_edit0012_read_only_audit")


def module_receipt(path: Path, expected: tuple[int, str]) -> dict[str, Any]:
    data = path.read_bytes()
    if (len(data), sha256(data)) != expected:
        raise RuntimeError(f"module drift: {path}")
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
    if not isinstance(manifest, list) or len(manifest) != EXPECTED_SITES:
        raise RuntimeError("frozen site count drift")
    physical_lines = len({(item["file"], item["line"]) for item in manifest})
    if physical_lines != EXPECTED_PHYSICAL_LINES:
        raise RuntimeError("frozen physical-line count drift")
    outputs = AUDIT.BASE.project(cohort, manifest)
    if observed_pins(outputs) != SUCCESSOR:
        raise RuntimeError("reconstructed successor pin drift")
    return outputs, {
        **report,
        "schema": "noether-isv-v021-complete-basic-extended-letters-candidate-v1",
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "applicator": {
            "path": str(Path(__file__).resolve()),
            **pin(Path(__file__).read_bytes()),
        },
        "audit_tool": module_receipt(AUDIT_PATH, AUDIT_PIN),
        "transaction_core": module_receipt(CORE_PATH, CORE_PIN),
    }


def successor_residue(cohort: dict[str, bytes]) -> dict[str, Any]:
    visible = AUDIT.visible_residue(cohort)
    if visible["tokens"] or visible["characters"]:
        raise RuntimeError(f"successor visible optional-letter residue: {visible}")
    global_characters = AUDIT.global_character_census(cohort)
    if global_characters != AUDIT.EXPECTED_NONVISIBLE_CHARACTERS:
        raise RuntimeError(
            f"successor protected optional-letter residue drift: {dict(global_characters)}"
        )
    return {
        "visible": visible,
        "protected_foreign": dict(sorted(global_characters.items())),
    }


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live successor cohort drifted")
    return {
        "schema": "noether-isv-v021-complete-basic-extended-letters-postapply-v1",
        "edit_id": EDIT_ID,
        "revision": REVISION,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": EXPECTED_SITES,
            "physical_lines": EXPECTED_PHYSICAL_LINES,
            "characters": dict(sorted(AUDIT.EXPECTED_VISIBLE_CHARACTERS.items())),
        },
        "locator_manifest": {
            "canonical_bytes": EXPECTED_LOCATOR_BYTES,
            "sha256": EXPECTED_LOCATOR_SHA256,
        },
        "residue": successor_residue(cohort),
        "authority": AUDIT.authenticate_authority(),
        "policy": {
            "surface": "standard/basic reader-facing Latin",
            "rule": "Every reader-visible optional extended vowel or soft-consonant diacritic is omitted; four protected French è spellings remain byte-identical.",
            "scope_boundary": "Foreign Liège, système, algèbre, and Cavaillès are protected source payloads and are not Interslavic normalization targets.",
        },
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
    print(json.dumps(report, ensure_ascii=False, sort_keys=args.compact, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
