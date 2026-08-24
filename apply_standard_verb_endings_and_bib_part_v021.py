#!/usr/bin/env python3
"""Freeze, report, and transactionally apply ISV021-EDIT-0006.

This applicator authenticates both the read-only linguistic audit and the
hardened EDIT-0002 transaction engine before loading either from bytes.  It is
bounded to the frozen 53-site manifest: 51 second-conjugation 3pl ``-ęt`` to
official ``-et`` repairs and two Part-IV wrapper ``Čest`` to ``Čęst`` repairs.
Exactly three past-participle ``vzęt`` tokens are explicitly retained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
EDIT_ID = "ISV021-EDIT-0006"

CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_PIN = (
    29_146,
    "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87",
)
AUDIT_PATH = ROOT / "audit_standard_verb_endings_v021.py"
AUDIT_PIN = (
    18_792,
    "DC78093DE25CDC9CF411B6C1A691BDEC7573C206B1004B6DEC16508D2BD97DD7",
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
        "D3029CFFB856ACF30E55DEA6086AE3E63F90AA733BBD1B2F0E4DC19D9CB05F88",
    ),
    "45-isv.tex": (
        26_043,
        "403E22F8770C9180ED2A54430CDE0E09F6E3DDF919115413E11A05CFA16B8C11",
    ),
    "base-papers1-43-isv.tex": (
        1_894_621,
        "2EA6BC47DDFFB8190B2865A5DD2138628922A517FF1158EE23A2884725E68CD9",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
SUCCESSOR = {
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
EXPECTED_LOCATOR_BYTES = 6_900
EXPECTED_LOCATOR_SHA256 = (
    "EFC90C292CEEE0DB9148BFA7EE53ED7DBB631A6378960BF23B73EBB7275D9E51"
)
EXPECTED_SITE_COUNT = 53
EXPECTED_PHYSICAL_LINES = 49


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
AUDIT = authenticate_module(AUDIT_PATH, AUDIT_PIN, "isv021_edit0006_read_only_audit")


def module_receipt(path: Path, expected: tuple[int, str]) -> dict[str, Any]:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"module drift: {path}: {observed}")
    return {"path": str(path), **pin(data)}


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    for name, data in cohort.items():
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
    coverage = report.get("coverage", {})
    if coverage.get("total_sites") != EXPECTED_SITE_COUNT:
        raise RuntimeError("frozen site count drift")
    if coverage.get("physical_lines") != EXPECTED_PHYSICAL_LINES:
        raise RuntimeError("frozen physical-line count drift")
    manifest = report.get("locator_manifest", {})
    if manifest.get("canonical_bytes") != EXPECTED_LOCATOR_BYTES:
        raise RuntimeError("canonical locator-manifest byte count drift")
    if manifest.get("sha256") != EXPECTED_LOCATOR_SHA256:
        raise RuntimeError("canonical locator-manifest hash drift")

    by_file: dict[str, list[dict[str, Any]]] = {name: [] for name in SOURCE_ORDER}
    for filename in SOURCE_ORDER:
        replacements, retained = AUDIT.scan_ending_tokens(filename, cohort[filename])
        if any(item["before"] != "vzęt" for item in retained):
            raise RuntimeError("retained-token identity drift")
        by_file[filename].extend(replacements)
    by_file["bib-isv.tex"].extend(
        AUDIT.locate_bibliography(
            cohort["bib-isv.tex"].decode("utf-8", errors="strict")
        )
    )

    outputs: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        outputs[filename], _ = AUDIT.project_one(
            filename, cohort[filename], by_file[filename]
        )
    if observed_pins(outputs) != SUCCESSOR:
        raise RuntimeError("independently reconstructed successor pin drift")

    return outputs, {
        **report,
        "schema": "noether-isv-v021-standard-verb-endings-candidate-v1",
        "status": "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE",
        "applicator": {
            "path": str(Path(__file__).resolve()),
            **pin(Path(__file__).read_bytes()),
        },
        "audit_tool": module_receipt(AUDIT_PATH, AUDIT_PIN),
        "transaction_core": module_receipt(CORE_PATH, CORE_PIN),
        "claims": {
            "applied": False,
            "source_write": False,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
            "native_or_community_certification": False,
        },
    }


def successor_residue_audit(cohort: dict[str, bytes]) -> dict[str, Any]:
    ending_tokens: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in AUDIT.ENDING_ET_NASAL_RE.finditer(line):
                ending_tokens.append(
                    {
                        "file": filename,
                        "line": line_no,
                        "column": match.start(1) + 1,
                        "token": match.group(1),
                    }
                )
    if [item["token"] for item in ending_tokens] != ["vzęt", "vzęt", "vzęt"]:
        raise RuntimeError(f"successor word-final -ęt residue drift: {ending_tokens}")
    bib_text = cohort["bib-isv.tex"].decode("utf-8", errors="strict")
    if bib_text.count("Čest IV") != 0 or bib_text.count("Čęst IV") != 2:
        raise RuntimeError("successor Part-IV wrapper census drift")
    return {
        "nonparticiple_word_final_et_nasal": 0,
        "retained_vzet_participles": ending_tokens,
        "old_bibliography_wrapper": 0,
        "new_bibliography_wrapper": 2,
    }


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live successor cohort drifted")
    return {
        "schema": "noether-isv-v021-standard-verb-endings-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": EXPECTED_SITE_COUNT,
            "physical_lines": EXPECTED_PHYSICAL_LINES,
            "second_conjugation_3pl_repairs": 51,
            "bibliography_wrapper_repairs": 2,
            "retained_participles": 3,
        },
        "locator_manifest": {
            "canonical_bytes": EXPECTED_LOCATOR_BYTES,
            "sha256": EXPECTED_LOCATOR_SHA256,
        },
        "residue": successor_residue_audit(cohort),
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
