#!/usr/bin/env python3
"""Seal the exact EDIT-0008 successor after transaction closure.

The frozen applicator completed its transaction but its presentation-only
successor report called a predecessor-only authority check.  This bounded
read-only sealer authenticates that applicator, reconstructs the predecessor,
replays both directions, and calls the same authority check on the state it
was designed to inspect.  It never writes source files.
"""

from __future__ import annotations

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
APP_PATH = ROOT / "apply_sumand_family_v021.py"
APP_PIN = (
    9_131,
    "F71627A306D817CEA6F60EDACDABE022BB382F0BBB6A7B2D225B2F1DD626FEA8",
)
RECEIPT_PATH = (
    ROOT / "decision_records" / "ISV021-EDIT-0008-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    6_701,
    "ECF461D81F9C81F84D905FB1EA631F11FA2EB544FC72B9FBAE8D7AEABB1B1E4F",
)
ACCEPT_PATH = ROOT / "decision_records" / "ISV021-EDIT-0008-ACCEPT-PREAPPLY.json"
ACCEPT_PIN = (
    9_063,
    "619B5424DCD056B5460D2DB0AA6C0A68DFC1CBD242748BB08778C019CC97AE5A",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": digest(data)}


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    observed = (len(data), digest(data))
    if observed != expected:
        raise RuntimeError(f"{label} pin drift: {observed}")
    return data


def load_app() -> Any:
    data = authenticate(APP_PATH, APP_PIN, "frozen applicator")
    module = types.ModuleType("isv021_edit0008_sealed_app")
    module.__file__ = str(APP_PATH)
    module.__package__ = ""
    exec(compile(data, str(APP_PATH), "exec"), module.__dict__)
    return module


def main() -> int:
    app = load_app()
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    accept_bytes = authenticate(ACCEPT_PATH, ACCEPT_PIN, "preapply acceptance")
    accept = json.loads(accept_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate status drift")
    if accept.get("status") != "ACCEPT_PREAPPLY" or accept.get("applied") is not False:
        raise RuntimeError("preapply acceptance status drift")
    manifest = receipt.get("locator_manifest", {}).get("value")
    if not isinstance(manifest, list) or len(manifest) != 8:
        raise RuntimeError("candidate manifest drift")
    payload = app.AUDIT.canonical_bytes(manifest)
    if (len(payload), digest(payload)) != (
        app.EXPECTED_LOCATOR_BYTES,
        app.EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("candidate locator pin drift")

    successor = app.read_cohort()
    if app.observed_pins(successor) != app.SUCCESSOR:
        raise RuntimeError("live cohort is not the exact successor")
    residue = app.successor_residue(successor)

    predecessor: dict[str, bytes] = {}
    for filename in app.SOURCE_ORDER:
        items = [item for item in manifest if item["file"] == filename]
        shifted = app.AUDIT.shifted_for_successor(items)
        predecessor[filename] = app.AUDIT.transform_one(
            successor[filename], shifted, False
        )
    if app.observed_pins(predecessor) != app.PREDECESSOR:
        raise RuntimeError("exact reverse did not restore predecessor pins")
    replay = app.AUDIT.project(predecessor, manifest)
    if replay != successor:
        raise RuntimeError("forward replay did not restore exact successor bytes")
    authorities = app.AUDIT.authenticate_authorities(predecessor)

    transaction_paths = [
        ROOT / f".{app.EDIT_ID}.lock",
        ROOT
        / "source_latin"
        / f".{app.EDIT_ID}.base-papers1-43-isv.tex.stage",
        ROOT
        / "source_latin"
        / f".{app.EDIT_ID}.base-papers1-43-isv.tex.rollback",
    ]
    remaining = [str(path) for path in transaction_paths if path.exists()]
    if remaining:
        raise RuntimeError(f"transaction residue remains: {remaining}")

    report = {
        "schema": "noether-isv-v021-edit0008-self-postapply-seal-v1",
        "edit_id": app.EDIT_ID,
        "status": "PASS_SUCCESSOR",
        "live_sources": {
            name: pin(successor[name]) for name in app.SOURCE_ORDER
        },
        "predecessor_reconstruction": {
            name: pin(predecessor[name]) for name in app.SOURCE_ORDER
        },
        "candidate_receipt": {"path": str(RECEIPT_PATH), **pin(receipt_bytes)},
        "preapply_acceptance": {"path": str(ACCEPT_PATH), **pin(accept_bytes)},
        "frozen_applicator": {"path": str(APP_PATH), **pin(APP_PATH.read_bytes())},
        "residue": residue,
        "authorities": authorities,
        "validation": {
            "exact_reverse": True,
            "exact_forward_replay": True,
            "successor_pin_gate": True,
            "transaction_residue": 0,
            "source_writes": 0,
        },
        "reporting_defect": {
            "source_mutation_affected": False,
            "description": "The frozen applicator's post-transaction presentation path passed the live successor to an authority helper that intentionally expects the predecessor sčestnikov control at line 10959. The transaction had already reached and cleaned the exact successor before that report-only exception."
        }
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
