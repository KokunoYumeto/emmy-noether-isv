#!/usr/bin/env python3
"""Seal the authenticated v021 Cyrillic projection and advance durable state."""

from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
DECISIONS = ROOT / "decision_records"
STATE_PATH = ROOT / "00_SESSION_INDEPENDENT_STATE_v021.json"
WORKLOG_PATH = ROOT / "00_SESSION_INDEPENDENT_WORKLOG_v021.jsonl"
POSTSEAL_PATH = DECISIONS / "ISV021-CYRILLIC-V8-POSTSEAL.json"

STATE_PIN = (28_319, "C81839CC67CF11E0D3EBAE27682909E88BF9004F4EAB1AF0571C72542A1681D1")
WORKLOG_PIN = (45_118, "D374961657B024E5355C22DB9DBF965012A239A86969188383878FDCB559924B")
PROJECTOR_PIN = (34_267, "06CC1640E253513EFF64918E6CC3BCE583913D3E64B2F93F1B77C3734BABDC8C")
TRANSACTION_TEST_PIN = (5_007, "3ABFB11FA1D31D4319C2408199DE37AB726CE58C442AE95CB491A6EE72948E39")
INDEPENDENT_VERIFIER_PIN = (11_928, "CEABC1CF22F029DE23C3C7464F515CFB918AA500E89AAB6020FD3312E6614B07")
ROLE_MANIFEST_PIN = (4_177_431, "BE0A9902DAC546350227C048777A78AC300647D5FB514895F7CB91EC3D900970")
ROLE_REBASE_RECEIPT_PIN = (2_327, "CF62CC2EE021FF831C48BDA715A55C88E2774C0699549F9ACDBE2AA174A80AC9")
PREINSTALL_PIN = (2_308, "848070A1D83F7810BD6D1DE90C701D0494667854C65388185FC1656BC4019718")
PRODUCER_POSTINSTALL_PIN = (7_409, "96E43014737AB5DAC36E76A3F55C9BAFAF45CCDEA411D83CE5B204607D6440EE")
INDEPENDENT_POSTINSTALL_PIN = (2_715, "043D5BE79F5AD7D90DAB510DF16B61C413696F679AE242AB13A1CDD4F85017CB")
REJECTED_NULL_RECEIPT_PIN = (5, "38E0B9DE817F645C4BEC37C0D4A3E58BAECCCB040F5718DC069A72C7385A0BED")
OUTPUT_MANIFEST_SHA = "6F15F488C3AE010E19F7C9EE53026683E972ED1E38DEF867D15D5CD1B641B6F7"
PROJECTOR_REPORT_SHA = "66D84893A2C6E56A26D0CDABC14057135FFD1BA2FFC820FE26DE13BBB9CFB4E0"
OUTPUT_PINS = {
    "44-book-isv-cyrl.tex": (230_381, "0DD9907518035924993A0041B14BCAEA10D7C213DAB8DF422F6B25E7DDED9D63"),
    "45-isv-cyrl.tex": (35_874, "40870377323594B3153A1F25D6BC2FB34899B6E6FDD388837388E9D12D147140"),
    "base-papers1-43-isv-cyrl.tex": (2_706_234, "E9C7AEC849C4B2D2B6E528AFB1B62236B9CFFBAD686FA4923749C9359EB2824C"),
    "bib-isv-cyrl.tex": (13_206, "37FFF904BB16B2B460923AE2BF801BF783803FD0B78B94AF83D21FF43B81AB47"),
}


class SealError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SealError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def describe(raw: bytes) -> dict[str, Any]:
    return {"bytes": len(raw), "sha256": sha256(raw)}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(raw: bytes, label: str) -> Any:
    require(raw.endswith(b"\n") and b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), f"transport drift: {label}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)


def read_exact(path: Path, pin: tuple[int, str], label: str) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe {label}: {path}")
    raw = path.read_bytes()
    require((len(raw), sha256(raw)) == pin, f"pin drift: {label}: {describe(raw)}")
    return raw


def stage(path: Path, raw: bytes, ordinal: int) -> Path:
    staged = path.parent / f".{path.name}.seal-stage-{os.getpid()}-{ordinal}"
    require(not staged.exists(), f"stage collision: {staged}")
    with staged.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    require(staged.read_bytes() == raw, f"stage readback mismatch: {staged}")
    return staged


def restore(path: Path, predecessor: bytes, successor: bytes) -> None:
    if path.is_file() and not path.is_symlink() and path.read_bytes() == successor:
        rollback = path.parent / f".{path.name}.seal-rollback-{os.getpid()}"
        require(not rollback.exists(), f"rollback collision: {rollback}")
        with rollback.open("xb") as handle:
            handle.write(predecessor)
            handle.flush()
            os.fsync(handle.fileno())
        require(rollback.read_bytes() == predecessor, f"rollback readback mismatch: {rollback}")
        os.replace(rollback, path)
        require(path.read_bytes() == predecessor, f"rollback install mismatch: {path}")


def main() -> int:
    state_raw = read_exact(STATE_PATH, STATE_PIN, "predecessor state")
    worklog_raw = read_exact(WORKLOG_PATH, WORKLOG_PIN, "predecessor worklog")
    state = strict_json(state_raw, str(STATE_PATH))
    require(state.get("status") == "ISV021_LATIN_FROZEN_ZERO_NON_ROMAN_BLOCKS_CYRILLIC_REBASE_ACTIVE", "state status drift")
    require(state.get("current_head", {}).get("decision_id") == "ISV021-LATIN-FREEZE", "Latin head drift")
    require(not POSTSEAL_PATH.exists(), f"postseal already exists: {POSTSEAL_PATH}")

    projector_raw = read_exact(ROOT / "project_isv_cyrillic_v8.py", PROJECTOR_PIN, "v8 projector")
    test_raw = read_exact(ROOT / "test_cyrillic_v8_install_transaction.py", TRANSACTION_TEST_PIN, "v8 transaction test")
    verifier_raw = read_exact(ROOT / "verify_cyrillic_v8_independent.py", INDEPENDENT_VERIFIER_PIN, "independent verifier")
    role_manifest_raw = read_exact(DECISIONS / "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json", ROLE_MANIFEST_PIN, "rebased role manifest")
    role_rebase_raw = read_exact(DECISIONS / "ISV021-PROJECTION-ROLE-MANIFEST-REBASE-RECEIPT.json", ROLE_REBASE_RECEIPT_PIN, "role rebase receipt")
    preinstall_raw = read_exact(DECISIONS / "ISV021-CYRILLIC-V8-INDEPENDENT-PREINSTALL-R2.json", PREINSTALL_PIN, "independent preinstall receipt")
    producer_raw = read_exact(DECISIONS / "ISV021-CYRILLIC-V8-POSTINSTALL-RECEIPT.json", PRODUCER_POSTINSTALL_PIN, "producer postinstall receipt")
    independent_raw = read_exact(DECISIONS / "ISV021-CYRILLIC-V8-INDEPENDENT-POSTINSTALL.json", INDEPENDENT_POSTINSTALL_PIN, "independent postinstall receipt")
    rejected_raw = read_exact(DECISIONS / "ISV021-CYRILLIC-V8-INDEPENDENT-PREINSTALL.json", REJECTED_NULL_RECEIPT_PIN, "rejected null receipt")
    require(rejected_raw == b"null\n", "rejected receipt bytes drift")

    producer = strict_json(producer_raw, "producer postinstall receipt")
    independent = strict_json(independent_raw, "independent postinstall receipt")
    preinstall = strict_json(preinstall_raw, "independent preinstall receipt")
    require(producer.get("status") == "READY_DETERMINISTIC_V021_DERIVATION_IN_MEMORY", "producer status drift")
    require(producer.get("report_sha256_excluding_this_field") == PROJECTOR_REPORT_SHA, "producer report digest drift")
    require(producer.get("output_manifest_sha256") == OUTPUT_MANIFEST_SHA, "producer output manifest drift")
    require(producer.get("projection_issues") == 0, "producer projection issues")
    require(preinstall.get("status") == "PASS_INDEPENDENT_RECONSTRUCTION_IN_MEMORY", "preinstall status drift")
    require(independent.get("status") == "PASS_INDEPENDENT_RECONSTRUCTION_AND_LIVE_IDENTITY", "independent postinstall status drift")
    require(independent.get("output_manifest_sha256") == OUTPUT_MANIFEST_SHA, "independent output manifest drift")

    output_rows: list[dict[str, Any]] = []
    for name, pin in OUTPUT_PINS.items():
        raw = read_exact(ROOT / "source_cyrillic" / name, pin, f"live Cyrillic {name}")
        output_rows.append({"file": name, **describe(raw)})
    residues = list((ROOT / "source_cyrillic").glob("*.v8-stage-*"))
    require(not residues, f"v8 transaction residue: {residues}")

    timestamp = datetime.now(ZoneInfo("Europe/Berlin")).isoformat()
    postseal = {
        "schema": "noether-isv-v021-cyrillic-v8-postseal-v1",
        "status": "SEALED_DETERMINISTIC_CYRILLIC_SUCCESSOR",
        "recorded_at": timestamp,
        "release": "NOETHER-ISV-v021",
        "latin_head": "ISV021-EDIT-0012",
        "latin_freeze": "ISV021-LATIN-FREEZE",
        "classification": "deterministic Cyrillic representation of the frozen Latin Interslavic canon; not an independent translation witness",
        "projector": {"path": "project_isv_cyrillic_v8.py", **describe(projector_raw), "report_sha256": PROJECTOR_REPORT_SHA},
        "role_manifest": {"path": "decision_records/ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json", **describe(role_manifest_raw), "internal_sha256": "D3D2732B162B1033FED1F9AA4932540112085206AA257D4B19BEB26CCA8F1BC8"},
        "outputs": output_rows,
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA,
        "verification": {
            "projection_issues": 0,
            "inherited_role_effects": 372,
            "roman_identity_sites": 722,
            "changed_input_blocks": 2049,
            "unchanged_input_blocks_with_identical_output": 2053,
            "unlicensed_output_changes": 0,
            "transaction_test": {"path": "test_cyrillic_v8_install_transaction.py", **describe(test_raw), "identical_passes": 3},
            "independent_verifier": {"path": "verify_cyrillic_v8_independent.py", **describe(verifier_raw)},
            "role_rebase_receipt": {"path": "decision_records/ISV021-PROJECTION-ROLE-MANIFEST-REBASE-RECEIPT.json", **describe(role_rebase_raw)},
            "independent_preinstall": {"path": "decision_records/ISV021-CYRILLIC-V8-INDEPENDENT-PREINSTALL-R2.json", **describe(preinstall_raw)},
            "producer_postinstall": {"path": "decision_records/ISV021-CYRILLIC-V8-POSTINSTALL-RECEIPT.json", **describe(producer_raw)},
            "independent_postinstall": {"path": "decision_records/ISV021-CYRILLIC-V8-INDEPENDENT-POSTINSTALL.json", **describe(independent_raw)},
            "transaction_residue": 0,
        },
        "independent_review": {
            "identity": "/root/projector_rebase_review",
            "verdict": "ACCEPT_PREINSTALL",
            "scope": "exact freeze authentication, truthful dependency inventory, separated install/receipt transaction, one full read-only replay, and zero output/stage mutation",
        },
        "adverse_history": {
            "rejected_preinstall_receipt": {"path": "decision_records/ISV021-CYRILLIC-V8-INDEPENDENT-PREINSTALL.json", **describe(rejected_raw), "reason": "a transient verifier indentation defect emitted null; never accepted"},
            "first_install_invocation": "Failed closed because the shell used an unsupported New-Item parameter and therefore did not create source_cyrillic; projector returned unsafe output directory with zero output writes.",
        },
        "claims": {"source_latin_writes": 0, "git": False, "network": False, "build": False, "render": False, "publication": False, "native_or_community_certification": False},
    }
    postseal_raw = canonical_json(postseal)

    successor_state = copy.deepcopy(state)
    successor_state["status"] = "ISV021_CYRILLIC_V8_SEALED_BUILD_PIPELINE_ACTIVE"
    successor_state["updated_at"] = timestamp
    successor_state["cyrillic_v8_evidence"] = {
        "postseal": {"path": "decision_records/ISV021-CYRILLIC-V8-POSTSEAL.json", **describe(postseal_raw)},
        "projector": postseal["projector"],
        "role_manifest": postseal["role_manifest"],
        "outputs": output_rows,
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA,
        "producer_postinstall": postseal["verification"]["producer_postinstall"],
        "independent_postinstall": postseal["verification"]["independent_postinstall"],
        "review": postseal["independent_review"],
    }
    successor_state["derived_and_build_state"]["cyrillic"] = "SEALED_DETERMINISTIC_V8_SUCCESSOR; four live files exactly match independent reconstruction; projection issues and transaction residue zero"
    successor_state["derived_and_build_state"]["structural_qa"] = "LATIN FREEZE PASS; V8 inherited-role/Roman/delta gates PASS; independent live Cyrillic reconstruction PASS"
    successor_state["next_work"] = [
        "Reserve the v021 DOI in the existing Zenodo concept lineage and use it coherently in the Interslavic-first, English-parallel reader, methods paper, metadata, and machine index.",
        "Build cumulative Latin, Cyrillic, linked-reader, and methods outputs serially; perform exact structural, text, font, link, render, and proportional visual QA.",
        "Package reproducibly, update the established GitHub repository and Pages reader, publish the existing Zenodo lineage, and anonymously read back every public byte and identifier.",
    ]
    state_successor_raw = pretty_json(successor_state)
    event = {
        "event_id": "ISV021-EXTERNAL-0019",
        "recorded_at": timestamp,
        "event": "The v021 Cyrillic representation was generated once from the frozen EDIT0012 Latin quartet and sealed after producer and independent live-byte verification. All 372 inherited role effects, all 722 Roman identity sites, 2049 Latin-changed blocks, and 2053 unchanged controls pass with zero projection issue, unlicensed output change, or transaction residue.",
        "classification": postseal["classification"],
        "outputs": {row["file"]: f"{row['bytes']}/{row['sha256']}" for row in output_rows},
        "evidence": {
            "projector": f"{PROJECTOR_PIN[0]}/{PROJECTOR_PIN[1]}",
            "role_manifest": f"{ROLE_MANIFEST_PIN[0]}/{ROLE_MANIFEST_PIN[1]}",
            "postseal": f"{len(postseal_raw)}/{sha256(postseal_raw)}",
            "producer_postinstall": f"{PRODUCER_POSTINSTALL_PIN[0]}/{PRODUCER_POSTINSTALL_PIN[1]}",
            "independent_postinstall": f"{INDEPENDENT_POSTINSTALL_PIN[0]}/{INDEPENDENT_POSTINSTALL_PIN[1]}",
            "output_manifest_sha256": OUTPUT_MANIFEST_SHA,
            "projector_report_sha256": PROJECTOR_REPORT_SHA,
        },
        "agent": postseal["independent_review"],
        "adverse_history": postseal["adverse_history"],
        "next": "Reserve the existing-lineage v021 DOI, build and visually QA the bilingual readers/methods publication, refresh machine metadata, package, publish GitHub/Pages and Zenodo, and perform anonymous readback.",
        "claims": postseal["claims"],
    }
    worklog_successor_raw = worklog_raw + canonical_json(event)

    staged = {
        POSTSEAL_PATH: stage(POSTSEAL_PATH, postseal_raw, 1),
        STATE_PATH: stage(STATE_PATH, state_successor_raw, 2),
        WORKLOG_PATH: stage(WORKLOG_PATH, worklog_successor_raw, 3),
    }
    installed: list[Path] = []
    try:
        for target in (POSTSEAL_PATH, STATE_PATH, WORKLOG_PATH):
            os.replace(staged[target], target)
            installed.append(target)
        require(POSTSEAL_PATH.read_bytes() == postseal_raw, "postseal install mismatch")
        require(STATE_PATH.read_bytes() == state_successor_raw, "state install mismatch")
        require(WORKLOG_PATH.read_bytes() == worklog_successor_raw, "worklog install mismatch")
    except Exception:
        if POSTSEAL_PATH in installed and POSTSEAL_PATH.is_file() and POSTSEAL_PATH.read_bytes() == postseal_raw:
            POSTSEAL_PATH.unlink()
        if STATE_PATH in installed:
            restore(STATE_PATH, state_raw, state_successor_raw)
        if WORKLOG_PATH in installed:
            restore(WORKLOG_PATH, worklog_raw, worklog_successor_raw)
        raise
    finally:
        for staged_path in staged.values():
            if staged_path.exists():
                staged_path.unlink()

    print(json.dumps({
        "status": postseal["status"],
        "postseal": {"path": str(POSTSEAL_PATH), **describe(postseal_raw)},
        "state": describe(state_successor_raw),
        "worklog": describe(worklog_successor_raw),
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "ERROR_FAIL_CLOSED", "error_type": type(error).__name__, "error": str(error)}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1)
