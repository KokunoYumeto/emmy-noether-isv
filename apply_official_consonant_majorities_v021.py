#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0010."""

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
EDIT_ID = "ISV021-EDIT-0010"
CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_PIN = (
    29_146,
    "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87",
)
AUDIT_PATH = ROOT / "audit_official_consonant_majorities_v021.py"
AUDIT_PIN = (
    11_858,
    "E2F803BD8E836E643FFDFB7DE362DD68FF37E7095930C45BB24E594CC28CF9D9",
)
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
PREDECESSOR = {
    "44-book-isv.tex": (
        168_427,
        "39FC522BFABDCA4F61A08ED5654224122AC0C64299F078FB16D31A90F3662415",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_613,
        "C1B9BAC6DC890F8544A8661712B0B87FFC854871BFB52792FD11FAFA82358719",
    ),
    "bib-isv.tex": (
        10_020,
        "7A45365DC7C9408CF3D50FDAA4C35081E032CC6F07D73A9954D3B1DDF18C9EC7",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": (
        168_427,
        "233A76BFBC11C21C0A8EEDCB74D6C6208D7A37B1085BFD7ED3D817A17B4C5793",
    ),
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_613,
        "71D7297364CFC43BD45DAE6D61E252A6351EAE116C076C8F7A58649B0E5BB4E2",
    ),
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}
EXPECTED_LOCATOR_BYTES = 17_641
EXPECTED_LOCATOR_SHA256 = (
    "451BA8C7A605A7BA06C9C5F0749014099933DB57AE5AAF0294E1D3B1F902F715"
)
EXPECTED_SUCCESSOR_CENSUS = Counter(
    {
        "dopušća": 81,
        "dopušćaje": 2,
        "dopušćajut": 27,
        "dopušćanju": 1,
        "skraćajuče": 1,
        "skraćene": 1,
        "skraćenja": 2,
        "skraćeno": 7,
        "skraćenom": 1,
        "skraćivati": 1,
        "skraćujuče": 1,
        "vozvraća": 2,
        "vozvraćanje": 1,
        "vozvraćenje": 1,
        "vozvraćenju": 1,
        "vraća": 1,
        "vraćajuči": 3,
        "vraćanja": 1,
    }
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
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


CORE = authenticate_module(CORE_PATH, CORE_PIN, "isv021_edit0010_transaction_core")
AUDIT = authenticate_module(AUDIT_PATH, AUDIT_PIN, "isv021_edit0010_read_only_audit")


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
    if not isinstance(manifest, list) or len(manifest) != 99:
        raise RuntimeError("frozen site count drift")
    outputs = AUDIT.BASE.project(cohort, manifest)
    if observed_pins(outputs) != SUCCESSOR:
        raise RuntimeError("reconstructed successor pin drift")
    return outputs, {
        **report,
        "schema": "noether-isv-v021-official-consonant-majorities-candidate-v1",
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "applicator": {
            "path": str(Path(__file__).resolve()),
            **pin(Path(__file__).read_bytes()),
        },
        "audit_tool": module_receipt(AUDIT_PATH, AUDIT_PIN),
        "transaction_core": module_receipt(CORE_PATH, CORE_PIN),
    }


def successor_residue(cohort: dict[str, bytes]) -> dict[str, Any]:
    census = AUDIT.relevant_census(cohort)
    if census != EXPECTED_SUCCESSOR_CENSUS:
        raise RuntimeError(f"successor relevant census drift: {dict(census)}")
    protected = AUDIT.excluded_variant_census(cohort)
    if sum(protected.values()) != 58:
        raise RuntimeError(f"protected variant census drift: {dict(protected)}")
    return {
        "old_target_tokens": 0,
        "relevant_token_census": dict(sorted(census.items())),
        "protected_sucstven_variant_census": dict(sorted(protected.items())),
    }


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live successor cohort drifted")
    return {
        "schema": "noether-isv-v021-official-consonant-majorities-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "coverage": {"sites": 99, "physical_lines": 96, "families": 3},
        "locator_manifest": {
            "canonical_bytes": EXPECTED_LOCATOR_BYTES,
            "sha256": EXPECTED_LOCATOR_SHA256,
        },
        "residue": successor_residue(cohort),
        "authority": {"official_dictionary": AUDIT.authenticate_authority()},
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
