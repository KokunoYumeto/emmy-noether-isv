#!/usr/bin/env python3
"""Seal the independently replayed EDIT0171 zero-blocker Latin successor."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


sys.dont_write_bytecode = True
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "seal_isv_edit0170_v019.py"
BASE_PIN = (24_102, "83CDA86F5C7695F92C206D9E147429CB677626BFC1F416A8CE1911DB146BFE1C")


def load_base() -> Any:
    raw = BASE.read_bytes()
    if (len(raw), __import__("hashlib").sha256(raw).hexdigest().upper()) != BASE_PIN:
        raise RuntimeError("sealed EDIT0170 sealer pin drift")
    spec = importlib.util.spec_from_file_location("isv0171_base_sealer", BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("sealed EDIT0170 sealer unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_base()
Q, B = M.Q, M.B
require, sha, describe = M.require, M.sha, M.describe
pin_record, state_canonical = M.pin_record, M.state_canonical
read_regular, pin, json_object = M.read_regular, M.pin, M.json_object

WORKSPACE = ROOT.parents[3]
SEALER = Path(__file__).resolve()
STATE = ROOT / "00_SESSION_INDEPENDENT_STATE_v019.json"
LEDGER = ROOT / "NORMALIZATION_DECISIONS_v019.jsonl"
WORKLOG = ROOT / "00_SESSION_INDEPENDENT_WORKLOG_v019.jsonl"
VERIFIER = ROOT / "verify_session_independent_state_v019.ps1"
SIDECAR = ROOT / "decision_records/ISV019-EDIT-0171.json"
HUMAN = ROOT / "decision_records/ISV019-EDIT-0171.md"
APPLICATOR = ROOT / "apply_complete_foreign_surface_tranche12_v019.py"
CANDIDATE = ROOT / "decision_records/ISV019-EDIT-0171-UNAPPLIED-CANDIDATE-RECEIPT.json"
POSTAPPLY_GUARD = ROOT / "decision_records/ISV019-EDIT-0171-INDEPENDENT-LIVE-POSTAPPLY-PRESEAL-GUARD.json"
FRONTIER_AUDIT, FRONTIER_RECEIPT, ROLE_MANIFEST = M.FRONTIER_AUDIT, M.FRONTIER_RECEIPT, M.ROLE_MANIFEST
V4, V4_TEST, V4_SIGNATURE, V4_RECEIPT = M.V4, M.V4_TEST, M.V4_SIGNATURE, M.V4_RECEIPT
SOURCE_DIR, PRODUCER_DIR = M.SOURCE_DIR, M.PRODUCER_DIR

HEAD = "ISV019-EDIT-0171"
PREDECESSOR = "ISV019-EDIT-0170"
STAMP = "2026-08-21T21:00:00+02:00"
ZERO_DIGEST, EMPTY_PIN = M.ZERO_DIGEST, M.EMPTY_PIN
OLD_STATE_PIN = (33_280, "88601718B9411FA4116552FF94F0CDC8DDA77863D808B30E1CF6DE5FE759BA85")
OLD_STATE_CANONICAL_SHA256 = "CF55D38E12A7403C8F7C6F5EFBEBD6D654A1ACFE0A04073F26EDF4345D5DE02B"
LEDGER_PREFIX_PIN = (768_255, "1DB24E3B4507D711EAEB7FB88E255CD3C307BDF6352CE34AAC861491D612B672")
WORKLOG_PREFIX_PIN = (196_252, "8C3E378CC4052D0CD188EAB9BD09CD828FF3726A1CB4202797A6A72FF30DC5D0")
OLD_VERIFIER_PIN = (2_171, "1D89DB80246C75FF7FA5A831E830D99F4497A4BEF6161E9C31D364B0D2B7CF6C")
OLD_NORMALIZED_VERIFIER_SHA256 = "0618D8105C9CC43A37C28BC474041AD4607834E044E923C4E1A7E5D1DAAF6DC4"
PREVIOUS_SIDECAR_PIN = (24_490, "FD462AEC2905BC6DF51CE3356B98004E9E542DAEE59A4D3F1BA895BA1E40EA2C")
PREVIOUS_HUMAN_PIN = (5_396, "99C2416E1DA56828CA77050B6504F9131276EFA17E3F01DAF405CD27C7DB1A7D")
HUMAN_PIN = (6_342, "75167EC3FF7BB348424593DA1003F8B50AA0EB4640B68BA8C174B3A114F9C428")
APPLICATOR_PIN = (53_937, "4590D1D965233FCCC28CA87AEDCD743E9C8A7DB310D2E6500371222094EFAED8")
CANDIDATE_PIN = (4_562, "60FD5B79922EB425CCFC5F9C81D3134C7B550BE2A5F404E61A05194FBC7467A6")
POSTAPPLY_GUARD_PIN = (2_463, "D83450D41A2106062707AD9A267B45CB422EFF0235E2819859B55AD84FF0067F")
FRONTIER_AUDIT_PIN, FRONTIER_RECEIPT_PIN, ROLE_MANIFEST_PIN = M.FRONTIER_AUDIT_PIN, M.FRONTIER_RECEIPT_PIN, M.ROLE_MANIFEST_PIN
V4_PIN, V4_TEST_PIN, V4_SIGNATURE_PIN, V4_RECEIPT_PIN = M.V4_PIN, M.V4_TEST_PIN, M.V4_SIGNATURE_PIN, M.V4_RECEIPT_PIN

SOURCE_PINS = {
    "base-papers1-43-isv.tex": (1_894_721, "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A"),
    "44-book-isv.tex": (168_422, "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F"),
    "45-isv.tex": (26_053, "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91"),
    "bib-isv.tex": (10_019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}
PREDECESSOR_SOURCE_PINS = dict(SOURCE_PINS)
PREDECESSOR_SOURCE_PINS["base-papers1-43-isv.tex"] = (1_894_581, "7A4BF1ED5CDDA4C34DEDC3D1A11AACCE5067B845C0D03142EB8EB92E412AA8BB")
PREDECESSOR_BASE_PIN = PREDECESSOR_SOURCE_PINS["base-papers1-43-isv.tex"]

PRODUCER_PINS = {
    "Noether_Paper02_Section01_Interslavic_v001.tex": (7_674, "594F093A49D5FF186EA9126E0757B635F45EA2ED8391FAC1AD117D3308033998"),
    "Noether_Paper02_Section11_Interslavic_v001.tex": (14_964, "780FB348B52249F810F176B8B7015B83EE48CBB719D8EE4204D34A1AF8FA8DBD"),
    "Noether_Paper08_Interslavic_v001.tex": (24_007, "70102A6B3AE0B1001B2099A9D4E79D11E4516F60D1B794FA06D00101D0A3A2D3"),
    "Noether_Paper22_Interslavic_v001.tex": (78_415, "16E9A31B48E2ADE6D5046A889718D2DF8DFB9F7094D9A09BE9EED9F466CCC29D"),
    "Noether_Paper24_Through_Section07_Interslavic_p24_source_fidelity.tex": (95_721, "BCCFE51D0D1F905CEC29B9ED3B39466BCAB7DE60BD7E1CB598D840F7A0ADA5A1"),
    "Noether_Paper24_Through_Section07_Interslavic_working.tex": (95_451, "871CD6E83833631A63986D8801E1A122B433FE5AECF37AE3641CF407EE8A5C03"),
    "Noether_Paper34_Section23_SourceFidelity_Interslavic_v001.tex": (4_752, "E60C00BD715913C21F6DB35DE68F5677F2FC6B5D486756C565905B1EA7774DC1"),
}
PREDECESSOR_PRODUCER_PINS = dict(PRODUCER_PINS)
PREDECESSOR_PRODUCER_PINS.update(
    {
        "Noether_Paper02_Section01_Interslavic_v001.tex": (7_664, "746C1B8CFB6A524C0348B388F373BE1A433DC6D6ABCEE0BAFEE79E56A214D47E"),
        "Noether_Paper08_Interslavic_v001.tex": (23_977, "611FF5D4933FCA1D99D07235DE81866248F66FAE53D245C2C047C0F8795F6A74"),
        "Noether_Paper22_Interslavic_v001.tex": (78_375, "5D1212B2E8EAD24CA130346E43B19ABFEE3095883EEEE6D1F2BFA7F29F0EF01E"),
        "Noether_Paper24_Through_Section07_Interslavic_p24_source_fidelity.tex": (95_661, "3C343513CC303C7B9875C114DF143232ED10B3D45B3052DEFE159BF27EE14578"),
    }
)

V4_COUNTS = {"blocked": 0, "unsupported": 0, "roman_identity_holds": 0}
V4_INVENTORY = "37517E5F3DC66819F61F5A7BB8ACE1921282415F10551D2DEFA5C3EB0985B570"
V4_REPORT = "3688952352A218DF495CDC748E3DA34833E1A8AF7D8E8F5C8BAE5885856FE494"
UPSTREAM_V2 = {"blocked_occurrences": 722, "blocked_inventory_sha256": "6D913E86A5041C7019A0506E022ED536D643AAAE1688B0302E96F3E3FEA488A2", "unsupported_occurrences": 116, "unsupported_inventory_sha256": "310EAF55040A16CD5384F8A88F0194FEA0EE26C7A1B9EDB904ADA010419549DC", "roman_identity_hold_occurrences": 704, "roman_identity_inventory_sha256": "145F0B8FD82DDF6275B266EC494A742D670204250DBEE97BCDA456CD7FFFB48E", "parse_errors": 0, "coverage_failures": 0, "unknown_argument_commands": 0}
LINE_MANIFEST_PIN = (14_551, "E765FBA94834DA7D7DE4FE6958EC6A4445E47C91FB23BC6BACF5F88E3C9F1E57")
IDENTITY_MANIFEST_PIN = (2_370, "64661F9359767B0043879E07C9BA7B62593FAEF54307829D63A6A5FE13DE7C59")
REVERSE_MANIFEST_PIN = (1_397, "EF5762C797027F8673AE71E48662DA6C1347FC2478C0797BE59A0BBAD8575322")
INPUT_COHORT_PIN = (1_360, "A1E2EA1B41077A991F1C1E63B8B5DC31E336A07CD61BD27AAF89B4CB840D4C34")
OUTPUT_COHORT_PIN = (1_360, "FA2BD52043563A1C3220EF84AE4A31C5E59EB5C966886A5BFAEFA3B14DEAB3F5")
PRODUCTION_STDOUT_PIN = (19_087, "A346F8EEFB24E0F8CC49FF95579B78DBDD7433DC2F556C4CAA793642FF90C4B3")
PREDECESSOR_LEDGER_ROWS, SUCCESSOR_LEDGER_ROWS = 170, 171
PREDECESSOR_WORKLOG_ROWS, SUCCESSOR_WORKLOG_ROWS = 63, 64


def transaction_layouts():
    return {"seal": (SIDECAR, LEDGER, STATE, VERIFIER), "worklog": (WORKLOG,)}


def bounded_guard_paths(_app=None):
    values = {STATE, LEDGER, WORKLOG, VERIFIER, SIDECAR, HUMAN, APPLICATOR, CANDIDATE, POSTAPPLY_GUARD, FRONTIER_AUDIT, FRONTIER_RECEIPT, ROLE_MANIFEST, BASE, V4, V4_TEST, V4_SIGNATURE, V4_RECEIPT, ROOT / "decision_records/ISV019-EDIT-0170.json", ROOT / "decision_records/ISV019-EDIT-0170.md", SEALER}
    values.update(SOURCE_DIR / name for name in SOURCE_PINS)
    values.update(PRODUCER_DIR / name for name in PRODUCER_PINS)
    return tuple(sorted(values, key=lambda path: str(path).casefold()))


def source_receipts():
    return {f"source_latin/{name}": pin_record(value) for name, value in SOURCE_PINS.items()}


def predecessor_source_receipts():
    return {f"source_latin/{name}": pin_record(value) for name, value in PREDECESSOR_SOURCE_PINS.items()}


def producer_receipts():
    return {f"producer_units/{name}": pin_record(value) for name, value in PRODUCER_PINS.items()}


def predecessor_producer_receipts():
    return {f"producer_units/{name}": pin_record(value) for name, value in PREDECESSOR_PRODUCER_PINS.items()}


def previous_barrier():
    return {"decision_id": PREDECESSOR, "complete": True, "state": {**pin_record(OLD_STATE_PIN), "canonical_sha256_excluding_only_verifier": OLD_STATE_CANONICAL_SHA256}, "ledger": {"rows": PREDECESSOR_LEDGER_ROWS, **pin_record(LEDGER_PREFIX_PIN)}, "worklog": {"rows": PREDECESSOR_WORKLOG_ROWS, **pin_record(WORKLOG_PREFIX_PIN)}, "verifier": {**pin_record(OLD_VERIFIER_PIN), "normalized_sha256": OLD_NORMALIZED_VERIFIER_SHA256}, "sidecar": pin_record(PREVIOUS_SIDECAR_PIN), "human": pin_record(PREVIOUS_HUMAN_PIN)}


def scan_projection(raws):
    pin(V4, V4_PIN, "pinned EDIT0171 projection v4")
    spec = importlib.util.spec_from_file_location("isv0171_pinned_projection_v4", V4)
    require(spec is not None and spec.loader is not None, "pinned projection v4 unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    source_raws = {name: raws[SOURCE_DIR / name] for name in module.SOURCE_ORDER}
    report = module.scan_raws(source_raws)
    summary = report["summary"]
    require(summary["blocked_occurrences"] == summary["unsupported_occurrences"] == summary["roman_identity_hold_occurrences"] == 0, "v4 zero frontier drift")
    require(summary["blocked_inventory_sha256"] == summary["unsupported_inventory_sha256"] == summary["roman_identity_inventory_sha256"] == V4_INVENTORY, "v4 empty inventory drift")
    require(summary["approved_structural_identities"] == 722 and summary["status"] == "READY_IN_MEMORY_ONLY", "v4 structural/status drift")
    require(summary["parse_errors"] == summary["coverage_failures"] == summary["unknown_argument_commands"] == 0, "v4 structural failure")
    require(report["upstream_v2"] == UPSTREAM_V2 and report["report_sha256_excluding_this_field"] == V4_REPORT, "projection receipt drift")
    return {"summary": summary, "upstream_v2": report["upstream_v2"], "report_sha256_excluding_this_field": V4_REPORT}


def dependency_evidence(*, require_predecessor: bool):
    raws = {}
    stable = {HUMAN: HUMAN_PIN, APPLICATOR: APPLICATOR_PIN, CANDIDATE: CANDIDATE_PIN, POSTAPPLY_GUARD: POSTAPPLY_GUARD_PIN, FRONTIER_AUDIT: FRONTIER_AUDIT_PIN, FRONTIER_RECEIPT: FRONTIER_RECEIPT_PIN, ROLE_MANIFEST: ROLE_MANIFEST_PIN, BASE: BASE_PIN, V4: V4_PIN, V4_TEST: V4_TEST_PIN, V4_SIGNATURE: V4_SIGNATURE_PIN, V4_RECEIPT: V4_RECEIPT_PIN}
    for path, expected in stable.items():
        raws[path] = pin(path, expected, f"stable evidence {path.name}")
    for name, expected in SOURCE_PINS.items():
        path = SOURCE_DIR / name
        raws[path] = pin(path, expected, f"live EDIT0171 source {name}")
    for name, expected in PRODUCER_PINS.items():
        path = PRODUCER_DIR / name
        raws[path] = pin(path, expected, f"live EDIT0171 producer {name}")
    candidate = json_object(raws[CANDIDATE], "EDIT0171 candidate")
    guard = json_object(raws[POSTAPPLY_GUARD], "EDIT0171 postapply guard")
    require(candidate.get("status") == "FROZEN_UNAPPLIED_CANDIDATE" and candidate.get("canonical_sha256_excluding_this_field") == "B2F6B9784911846CE4A0C68DFBCDABA8750245C0AFDB51DCC6922C787D2CEE9F", "candidate identity drift")
    require(candidate.get("scope", {}).get("projection_blockers_removed") == 20 and candidate.get("scope", {}).get("complete_foreign_islands") == 14 and candidate.get("scope", {}).get("reader_identity_receipts_refreshed") == 4, "candidate scope drift")
    require(candidate.get("outputs", {}).get("source_latin/base-papers1-43-isv.tex") == pin_record(SOURCE_PINS["base-papers1-43-isv.tex"]), "candidate base successor drift")
    require(guard.get("status") == "PASS_SOURCE_AHEAD_OF_METADATA" and guard.get("scanner", {}).get("blocked") == guard.get("scanner", {}).get("unsupported") == guard.get("scanner", {}).get("roman") == 0, "postapply guard frontier drift")
    require(guard.get("producer_body_and_identity_exact") is True and guard.get("transaction_residue") == 0 and guard.get("metadata_head") == PREDECESSOR, "postapply guard topology/custody drift")
    require(guard.get("apply", {}).get("stdout") == pin_record(PRODUCTION_STDOUT_PIN) and guard.get("apply", {}).get("exit_code") == 0, "production apply receipt drift")
    projection, barrier = scan_projection(raws), previous_barrier()
    if require_predecessor:
        require(not SIDECAR.exists() and not SIDECAR.is_symlink(), "EDIT0171 sidecar must be absent")
        raws[SIDECAR] = None
        files = {STATE: OLD_STATE_PIN, LEDGER: LEDGER_PREFIX_PIN, WORKLOG: WORKLOG_PREFIX_PIN, VERIFIER: OLD_VERIFIER_PIN, ROOT / "decision_records/ISV019-EDIT-0170.json": PREVIOUS_SIDECAR_PIN, ROOT / "decision_records/ISV019-EDIT-0170.md": PREVIOUS_HUMAN_PIN}
        for path, expected in files.items():
            raws[path] = pin(path, expected, f"EDIT0170 predecessor {path.name}")
        state = json_object(raws[STATE], "EDIT0170 state")
        require(state.get("status") == "EDIT-0170_APPLIED_AND_INDEPENDENTLY_VERIFIED" and state.get("authoritative_head", {}).get("decision_id") == PREDECESSOR and sha(state_canonical(state)) == OLD_STATE_CANONICAL_SHA256, "predecessor state drift")
        require(state.get("source_pins") == predecessor_source_receipts() and state.get("source_pins") != source_receipts(), "predecessor/source-ahead phase drift")
        require(len(raws[LEDGER].splitlines()) == 170 and len(raws[WORKLOG].splitlines()) == 63, "predecessor row prefix drift")
    return {"raws": raws, "barrier": barrier, "projection": projection}


OVT, OBS, OBL, OBW = M.verifier_template, M.build_sidecar, M.build_ledger_row, M.build_worklog_row
OTS, OVG, OSO, OPP = M.transformed_state, M.validate_graph, M.success_object, M.public_plan
OAW, OSS, OST = M.append_worklog, M.semantic_shadow, M.full_self_test


def verifier_template(sealer_receipt):
    raw = OVT(sealer_receipt)
    old, new = b"seal_isv_edit0170_v019.py", b"seal_isv_edit0171_v019.py"
    require(raw.count(old) == 1 and len(old) == len(new), "verifier path drift")
    return raw.replace(old, new)


def build_sidecar(evidence, verifier_id, sealer_receipt, predecessor_state_raw):
    obj = OBS(evidence, verifier_id, sealer_receipt, predecessor_state_raw)
    obj["schema"] = "noether-isv-edit0171-final-complete-foreign-surface-tranche12-v1"
    obj["classification"] = "final active v4 blocker closure through complete foreign surfaces mirrored across four active producers and cumulative reader"
    obj["source_transaction"] = {
        "applicator": {"path": APPLICATOR.name, **pin_record(APPLICATOR_PIN)},
        "candidate_receipt": {"path": f"decision_records/{CANDIDATE.name}", **pin_record(CANDIDATE_PIN)},
        "postapply_guard": {"path": f"decision_records/{POSTAPPLY_GUARD.name}", **pin_record(POSTAPPLY_GUARD_PIN)},
        "production_apply": {"argv": ["python", "-B", APPLICATOR.name, "--apply", "--compact"], "invocations": 1, "exit_code": 0, "stdout": pin_record(PRODUCTION_STDOUT_PIN), "stderr": pin_record((0, ZERO_DIGEST)), "receipt_custody": "direct capture corroborated by independent live reverse/replay guard"},
        "targets_in_install_order": ["producer_units/Noether_Paper02_Section01_Interslavic_v001.tex", "producer_units/Noether_Paper08_Interslavic_v001.tex", "producer_units/Noether_Paper22_Interslavic_v001.tex", "producer_units/Noether_Paper24_Through_Section07_Interslavic_p24_source_fidelity.tex", "source_latin/base-papers1-43-isv.tex"],
        "complete_foreign_islands": 14,
        "projection_blockers_removed": 20,
        "active_producer_changes": 4,
        "identity_receipt_changes": 4,
        "reader_prose_lines": 11,
        "reader_total_changed_lines": 15,
        "line_manifest": pin_record(LINE_MANIFEST_PIN),
        "identity_manifest": pin_record(IDENTITY_MANIFEST_PIN),
        "reverse_manifest": pin_record(REVERSE_MANIFEST_PIN),
        "input_cohort_manifest": pin_record(INPUT_COHORT_PIN),
        "output_cohort_manifest": pin_record(OUTPUT_COHORT_PIN),
        "exact_reverse_and_forward_replay": True,
        "producer_before_reader_identity": True,
        "source_locator_changes": 0,
        "math_changes": 0,
    }
    obj["source_and_producer_pins"] = {"sources": source_receipts(), "producers": producer_receipts()}
    obj["frontier_evidence"].update({"sealed_predecessor_frontier": 20, "exact_subtraction": 20, "successor_frontier": 0})
    package = obj["projection_authority"]["package"]
    obj["projection_authority"] = {
        "authority_id": "ISV019-TOOL-CYR4-0001",
        "package": package,
        "v4": {"blocked": 0, "unsupported": 0, "roman_identity_holds": 0, "blocked_inventory_sha256": V4_INVENTORY, "report_sha256_excluding_this_field": V4_REPORT, "approved_structural_identities": 722, "role_partition": "0+0+0+0=0"},
        "upstream_v2": UPSTREAM_V2,
        "status": "ZERO_BLOCKERS_ADDITIONAL_COMPLETENESS_GATES_OPEN",
        "derived_output": None,
        "new_complete_foreign_islands": 14,
        "changed_active_producers": 4,
        "protected_streams_exact": True,
        "math_payloads_exact": True,
        "nested_foreign_islands": 0,
    }
    obj["next_action"] = "close one-letter I/V/M and allowed-letter name/title completeness gates, then freeze Latin and derive Cyrillic twice"
    return obj


def build_ledger_row(sidecar_receipt, sealer_receipt):
    obj = OBL(sidecar_receipt, sealer_receipt)
    obj["source_change"] = {"targets": 5, "reader_prose_lines": 11, "reader_identity_lines": 4, "complete_foreign_islands": 14, "active_producer_changes": 4, "blockers_removed": 20, "source_locator_changes": 0, "math_changes": 0}
    obj["projection_authority"] = {"blocked": 0, "unsupported": 0, "roman_identity_holds": 0, "inventory_sha256": V4_INVENTORY, "report_sha256_excluding_this_field": V4_REPORT, "approved_structural_identities": 722, "status": "ZERO_BLOCKERS_ADDITIONAL_COMPLETENESS_GATES_OPEN"}
    obj["remaining_frontier"] = "active v4 blocker frontier is zero; separate one-letter I/V/M and allowed-letter name/title completeness gates remain before Latin freeze"
    return obj


def build_worklog_row(sidecar_receipt, ledger_receipt, sealer_receipt):
    obj = OBW(sidecar_receipt, ledger_receipt, sealer_receipt)
    obj["event_id"] = "ISV019-EXTERNAL-0064"
    obj["event_type"] = "final_complete_foreign_surface_tranche12_applied_and_independently_verified"
    obj["results"] = {"source_targets": 5, "reader_changed_lines": 15, "complete_foreign_islands": 14, "producer_changes": 4, "identity_receipt_changes": 4, "blockers_removed": 20, "blocked_occurrences": 0, "unsupported_occurrences": 0, "roman_identity_holds": 0, "approved_structural_identities": 722, "transaction_residue": 0, "latin_frozen": False}
    return obj


def transformed_state(predecessor, *, sidecar_receipt, ledger_receipt, worklog_receipt, verifier_receipt, sealer_receipt):
    state = OTS(predecessor, sidecar_receipt=sidecar_receipt, ledger_receipt=ledger_receipt, worklog_receipt=worklog_receipt, verifier_receipt=verifier_receipt, sealer_receipt=sealer_receipt)
    state["status"] = "EDIT-0171_APPLIED_AND_INDEPENDENTLY_VERIFIED"
    state["recovery_authority"][-1] = "pinned EDIT0171 five-target applicator, frozen candidate, independent live reverse/replay guard, historical role manifest, v4 scanner package, and local metadata sealer"
    state["source_pins"] = source_receipts()
    state["producer_successors"] = producer_receipts()
    state["cyrillic_projection_v2_design"]["status"] = "historical v2 diagnostic is 722/116/704 on EDIT0171; active v4 is zero-blocker but separate completeness gates remain before Latin freeze"
    current = state["tooling_authorities"]["cyrillic_projection_v4_scanner"]
    current["activation_head"] = current["classification_head"] = HEAD
    current["latest_validation"] = {
        "status": "READY_IN_MEMORY_ONLY",
        "blocked_occurrences": 0,
        "unsupported_occurrences": 0,
        "roman_identity_hold_occurrences": 0,
        "approved_structural_identities": 722,
        "blocked_inventory_sha256": V4_INVENTORY,
        "report_sha256_excluding_this_field": V4_REPORT,
        "parse_errors": 0,
        "coverage_failures": 0,
        "unknown_argument_commands": 0,
        "role_partition": {"lexical": 0, "foreign_or_citation_identities": 0, "integrated_name_or_eponym": 0, "structural_roman_identities": 0},
        "by_file": {"44-book-isv.tex": 0, "45-isv.tex": 0, "base-papers1-43-isv.tex": 0, "bib-isv.tex": 0},
        "source_manifest": [{"file": name, **pin_record(SOURCE_PINS[name])} for name in ("44-book-isv.tex", "45-isv.tex", "base-papers1-43-isv.tex", "bib-isv.tex")],
        "upstream_v2": UPSTREAM_V2,
    }
    current["remaining_gates"]["complete_foreign_title_venue_citation_identities"] = 0
    current["remaining_gates"]["derived_output"] = None
    current["boundary"] = "validated zero-blocker current-head authority; one-letter I/V/M and allowed-letter name/title completeness gates remain; no derived output yet"
    current["status"] = "ACTIVE_PRE_FREEZE_SCANNER_AUTHORITY_ZERO_BLOCKERS_ADDITIONAL_COMPLETENESS_GATES_OPEN"
    state["next_work"] = [
        {"priority": 1, "stage": "remaining_projection_gates", "task": "Close the separate 692 one-letter I/V/M context review and allowed-letter name/title completeness gate."},
        {"priority": 2, "stage": "latin_freeze", "task": "Create a final four-source immutable Latin freeze and independent replay receipt."},
        {"priority": 3, "stage": "cyrillic_projection_v4", "task": "After Latin freeze and zero blockers twice, derive Cyrillic deterministically twice."},
        {"priority": 4, "stage": "build_and_qa", "task": "Serially build Latin and Cyrillic readers and complete text, math, TeX, script, link, structural, font, and visual QA."},
        {"priority": 5, "stage": "package_handoff_publish", "task": "Create the four-file successor package and synchronize the standalone GitHub and Zenodo lineage at the sealed package checkpoint."},
    ]
    return state


def validate_state(state, plan):
    expected = {"decision_id": HEAD, "ledger_rows": 171, "ledger": plan["ledger_receipt"], "sidecar": plan["sidecar_receipt"], "verifier": plan["verifier_receipt"], "audit_companion": plan["sealer_receipt"], "worklog": plan["worklog_receipt"]}
    require(state.get("status") == "EDIT-0171_APPLIED_AND_INDEPENDENTLY_VERIFIED" and state.get("authoritative_head") == expected, "successor state head drift")
    require(state.get("source_pins") == source_receipts() and state.get("producer_successors") == producer_receipts(), "successor source/producer cohort drift")
    latest = state["tooling_authorities"]["cyrillic_projection_v4_scanner"]["latest_validation"]
    require(latest.get("blocked_occurrences") == latest.get("unsupported_occurrences") == latest.get("roman_identity_hold_occurrences") == 0 and latest.get("blocked_inventory_sha256") == V4_INVENTORY and latest.get("report_sha256_excluding_this_field") == V4_REPORT, "zero-frontier state drift")
    require(latest.get("role_partition") == {"lexical": 0, "foreign_or_citation_identities": 0, "integrated_name_or_eponym": 0, "structural_roman_identities": 0}, "zero role partition drift")


def validate_graph(plan, *, actual_worklog_raw, allow_pending):
    obj = OVG(plan, actual_worklog_raw=actual_worklog_raw, allow_pending=allow_pending)
    obj["status"] = "EXACT_COMPLETE_EDIT0171_LOCAL_GRAPH_VALIDATED"
    return obj


def success_object(plan, *, pending):
    obj = OSO(plan, pending=pending)
    obj["schema"] = "noether-isv-edit0171-local-audit-success-v1"
    obj["projection"].update({"blocked": 0, "unsupported": 0, "roman_identity_holds": 0, "inventory_sha256": V4_INVENTORY, "additional_completeness_gates_open": True})
    return obj


def public_plan(plan):
    obj = OPP(plan)
    obj["schema"] = "noether-isv-edit0171-strict-no-write-plan-v1"
    obj["source_transaction"] = {"targets": 5, "complete_foreign_islands": 14, "active_producer_changes": 4, "identity_receipt_changes": 4, "blockers_removed": 20}
    obj["projection"] = {"blocked": 0, "unsupported": 0, "roman_identity_holds": 0, "approved_structural_identities": 722, "role_partition": "0+0+0+0=0", "latin_frozen": False}
    return obj


def append_worklog():
    obj = OAW()
    obj["schema"] = "noether-isv-edit0171-worklog-append-success-v1"
    return obj


def semantic_shadow(plan):
    obj = OSS(plan)
    obj["schema"] = "noether-isv-edit0171-semantic-shadow-v1"
    state = json.loads(plan["state_raw"].decode("utf-8"))
    require(state["tooling_authorities"]["cyrillic_projection_v4_scanner"]["latest_validation"]["blocked_occurrences"] == 0, "semantic shadow zero-frontier drift")
    return obj


def full_self_test(plan):
    obj = OST(plan)
    obj["schema"] = "noether-isv-edit0171-self-test-v1"
    state = json.loads(plan["state_raw"].decode("utf-8"))
    require(state["source_pins"] == source_receipts() and state["producer_successors"] == producer_receipts(), "self-test cohort drift")
    return obj


def configure():
    patch = {"ROOT": ROOT, "WORKSPACE": WORKSPACE, "SEALER": SEALER, "BASE": BASE, "BASE_PIN": BASE_PIN, "BASE_SEALER": BASE, "BASE_SEALER_PIN": BASE_PIN, "STATE": STATE, "LEDGER": LEDGER, "WORKLOG": WORKLOG, "VERIFIER": VERIFIER, "SIDECAR": SIDECAR, "HUMAN": HUMAN, "APPLICATOR": APPLICATOR, "CANDIDATE": CANDIDATE, "POSTAPPLY_GUARD": POSTAPPLY_GUARD, "HEAD": HEAD, "PREDECESSOR": PREDECESSOR, "STAMP": STAMP, "OLD_STATE_PIN": OLD_STATE_PIN, "OLD_STATE_CANONICAL_SHA256": OLD_STATE_CANONICAL_SHA256, "LEDGER_PREFIX_PIN": LEDGER_PREFIX_PIN, "WORKLOG_PREFIX_PIN": WORKLOG_PREFIX_PIN, "OLD_VERIFIER_PIN": OLD_VERIFIER_PIN, "OLD_NORMALIZED_VERIFIER_SHA256": OLD_NORMALIZED_VERIFIER_SHA256, "PREVIOUS_SIDECAR_PIN": PREVIOUS_SIDECAR_PIN, "PREVIOUS_HUMAN_PIN": PREVIOUS_HUMAN_PIN, "HUMAN_PIN": HUMAN_PIN, "APPLICATOR_PIN": APPLICATOR_PIN, "CANDIDATE_PIN": CANDIDATE_PIN, "POSTAPPLY_GUARD_PIN": POSTAPPLY_GUARD_PIN, "SOURCE_PINS": SOURCE_PINS, "PRODUCER_PINS": PRODUCER_PINS, "PREDECESSOR_BASE_PIN": PREDECESSOR_BASE_PIN, "V4_COUNTS": V4_COUNTS, "V4_INVENTORY": V4_INVENTORY, "V4_REPORT": V4_REPORT, "UPSTREAM_V2": UPSTREAM_V2, "LINE_MANIFEST_PIN": LINE_MANIFEST_PIN, "IDENTITY_MANIFEST_PIN": IDENTITY_MANIFEST_PIN, "REVERSE_MANIFEST_PIN": REVERSE_MANIFEST_PIN, "INPUT_COHORT_PIN": INPUT_COHORT_PIN, "OUTPUT_COHORT_PIN": OUTPUT_COHORT_PIN, "PRODUCTION_STDOUT_PIN": PRODUCTION_STDOUT_PIN, "PREDECESSOR_LEDGER_ROWS": 170, "SUCCESSOR_LEDGER_ROWS": 171, "PREDECESSOR_WORKLOG_ROWS": 63, "SUCCESSOR_WORKLOG_ROWS": 64, "transaction_layouts": transaction_layouts, "bounded_guard_paths": bounded_guard_paths, "source_receipts": source_receipts, "producer_receipts": producer_receipts, "previous_barrier": previous_barrier, "scan_projection": scan_projection, "dependency_evidence": dependency_evidence, "verifier_template": verifier_template, "build_sidecar": build_sidecar, "build_ledger_row": build_ledger_row, "build_worklog_row": build_worklog_row, "transformed_state": transformed_state, "validate_state": validate_state, "validate_graph": validate_graph, "success_object": success_object, "public_plan": public_plan, "append_worklog": append_worklog, "semantic_shadow": semantic_shadow, "full_self_test": full_self_test}
    for key, value in patch.items():
        setattr(M, key, value)
    M.configure()
    lineage = []
    module = M
    while module not in lineage:
        lineage.append(module)
        if not hasattr(module, "M"):
            break
        module = module.M
    for module in lineage:
        for key, value in patch.items():
            setattr(module, key, value)
    for key, value in patch.items():
        setattr(Q, key, value)
    Q._patch_transaction_globals()


configure()


def deepest_builder():
    module = M
    seen = set()
    while not hasattr(module, "build_plan"):
        require(id(module) not in seen and hasattr(module, "M"), "inherited build-plan module unavailable")
        seen.add(id(module))
        module = module.M
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--append-worklog", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--semantic-shadow", action="store_true")
    mode.add_argument("--audit", action="store_true")
    parser.add_argument("--state-digest", default="")
    parser.add_argument("--allow-pending-worklog", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    production = "apply" if args.apply else "append" if args.append_worklog else None
    try:
        require(not args.state_digest or args.audit, "--state-digest is audit-only")
        require(not args.allow_pending_worklog or args.audit, "--allow-pending-worklog is audit-only")
        before, pycache = B.guard_snapshot(), B.pycache_snapshot()
        B.residue_gate()
        if args.audit:
            require(args.state_digest, "audit digest required")
            result = Q.audit_live(args.state_digest, args.allow_pending_worklog)
        elif args.append_worklog:
            result = append_worklog()
        else:
            plan = deepest_builder().build_plan()
            if args.apply:
                result = Q.install_metadata(plan)
            elif args.self_test:
                result = full_self_test(plan)
            elif args.semantic_shadow:
                result = semantic_shadow(plan)
            else:
                result = public_plan(plan)
        after = B.guard_snapshot()
        require(production is not None or before == after, "read-only mutation")
        require(pycache == B.pycache_snapshot(), "pycache drift")
        B.residue_gate()
        sys.stdout.buffer.write(Q.render(result, args.compact))
        return 0
    except Exception as error:
        payload = {"schema": "noether-isv-edit0171-failure-v1", "status": "FAILED_CLOSED", "mode": production or "read_only", "error_type": type(error).__name__, "error": str(error)}
        sys.stderr.buffer.write(Q.render(payload, True))
        return 4 if production else 2


if __name__ == "__main__":
    raise SystemExit(main())
