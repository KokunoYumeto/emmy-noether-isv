#!/usr/bin/env python3
"""Disposable transaction tests for the hardened ISV021-EDIT-0002 applicator."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
APPLICATOR = ROOT / "apply_residual_orthography_semantics_v021.py"
EXPECTED_APPLICATOR_SHA256 = "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87"


def load_applicator():
    spec = importlib.util.spec_from_file_location("isv021_edit0002_applicator", APPLICATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load applicator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def residue(module) -> list[str]:
    return sorted(
        path.name
        for path in [
            module.ROOT / f".{module.EDIT_ID}.lock",
            *module.SOURCE_DIR.glob(f".{module.EDIT_ID}.*.stage"),
            *module.SOURCE_DIR.glob(f".{module.EDIT_ID}.*.rollback"),
        ]
        if path.exists()
    )


def install_predecessor(module, source: dict[str, bytes], temp_root: Path) -> None:
    module.ROOT = temp_root
    module.SOURCE_DIR = temp_root / "source_latin"
    module.SOURCE_DIR.mkdir()
    for name, data in source.items():
        (module.SOURCE_DIR / name).write_bytes(data)
    if module.cohort_state(module.read_cohort()) != "predecessor":
        raise RuntimeError("fixture predecessor does not authenticate")


def assert_state(module, state: str, expected_residue: list[str]) -> None:
    if module.cohort_state(module.read_cohort()) != state:
        raise RuntimeError(f"expected {state} cohort")
    if residue(module) != expected_residue:
        raise RuntimeError(
            f"residue mismatch: expected {expected_residue}, observed {residue(module)}"
        )


def main() -> int:
    module = load_applicator()
    applicator_bytes = APPLICATOR.read_bytes()
    applicator_sha256 = module.sha256(applicator_bytes)
    if (
        EXPECTED_APPLICATOR_SHA256 != "TO_BE_FROZEN"
        and applicator_sha256 != EXPECTED_APPLICATOR_SHA256
    ):
        raise RuntimeError("applicator pin drift")

    live = {
        name: (ROOT / "source_latin" / name).read_bytes()
        for name in module.SOURCE_ORDER
    }
    if module.observed_pins(live) != module.PREDECESSOR:
        raise RuntimeError("live source predecessor drift")
    outputs, candidate = module.audit_predecessor(live)
    if candidate["locator_manifest"]["sha256"] != module.EXPECTED_LOCATOR_SHA256:
        raise RuntimeError("candidate locator drift")

    cases: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="isv021-edit0002-success-") as td:
        install_predecessor(module, live, Path(td))
        module.apply_transaction(module.read_cohort(), outputs)
        assert_state(module, "successor", [])
        cases.append({"case": "success", "status": "PASS"})

    with tempfile.TemporaryDirectory(prefix="isv021-edit0002-first-replace-") as td:
        install_predecessor(module, live, Path(td))
        original_replace = module.os.replace
        calls = 0

        def fail_first(source, destination):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("injected first-install failure")
            return original_replace(source, destination)

        with mock.patch.object(module.os, "replace", new=fail_first):
            try:
                module.apply_transaction(module.read_cohort(), outputs)
            except OSError as error:
                if str(error) != "injected first-install failure":
                    raise
            else:
                raise RuntimeError("first-install failure was not propagated")
        assert_state(module, "predecessor", [])
        cases.append(
            {
                "case": "failure_before_first_install",
                "status": "PASS_RECOVERED_EXACT_PREDECESSOR_LOCK_REMOVED",
            }
        )

    with tempfile.TemporaryDirectory(prefix="isv021-edit0002-second-replace-") as td:
        install_predecessor(module, live, Path(td))
        original_replace = module.os.replace
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected second-install failure")
            return original_replace(source, destination)

        with mock.patch.object(module.os, "replace", new=fail_second):
            try:
                module.apply_transaction(module.read_cohort(), outputs)
            except OSError as error:
                if str(error) != "injected second-install failure":
                    raise
            else:
                raise RuntimeError("second-install failure was not propagated")
        assert_state(module, "predecessor", [])
        cases.append(
            {
                "case": "failure_after_one_install",
                "status": "PASS_REVERSED_EXACTLY_LOCK_REMOVED",
            }
        )

    with tempfile.TemporaryDirectory(prefix="isv021-edit0002-cleanup-") as td:
        install_predecessor(module, live, Path(td))
        original_unlink = module.Path.unlink
        injected = False

        def fail_rollback_cleanup(path, *args, **kwargs):
            nonlocal injected
            if not injected and path.name.endswith(".rollback"):
                injected = True
                raise OSError("injected rollback-cleanup failure")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(module.Path, "unlink", new=fail_rollback_cleanup):
            try:
                module.apply_transaction(module.read_cohort(), outputs)
            except RuntimeError as error:
                if "successor installed but transaction cleanup failed" not in str(error):
                    raise
            else:
                raise RuntimeError("rollback-cleanup failure was not propagated")
        expected = [
            f".{module.EDIT_ID}.lock",
            *sorted(
                f".{module.EDIT_ID}.{name}.rollback"
                for name in module.SOURCE_ORDER
                if live[name] != outputs[name]
            ),
        ]
        assert_state(module, "successor", sorted(expected))
        cases.append(
            {
                "case": "rollback_cleanup_failure",
                "status": "PASS_COHERENT_SUCCESSOR_LOCK_AND_EVIDENCE_RETAINED",
            }
        )

    with tempfile.TemporaryDirectory(prefix="isv021-edit0002-third-state-") as td:
        install_predecessor(module, live, Path(td))
        original_replace = module.os.replace
        calls = 0
        changed_names = [name for name in module.SOURCE_ORDER if live[name] != outputs[name]]
        drift_name = changed_names[1]
        drift_bytes = b"INJECTED-THIRD-STATE\n"

        def inject_pending_target_drift(source, destination):
            nonlocal calls
            calls += 1
            if calls == 1:
                (module.SOURCE_DIR / drift_name).write_bytes(drift_bytes)
            return original_replace(source, destination)

        with mock.patch.object(module.os, "replace", new=inject_pending_target_drift):
            try:
                module.apply_transaction(module.read_cohort(), outputs)
            except RuntimeError:
                pass
            else:
                raise RuntimeError("third-state drift was not rejected")
        if (module.SOURCE_DIR / drift_name).read_bytes() != drift_bytes:
            raise RuntimeError("third-state target was overwritten")
        if not (module.ROOT / f".{module.EDIT_ID}.lock").exists():
            raise RuntimeError("lock was removed despite third-state evidence")
        first_name = changed_names[0]
        if (module.SOURCE_DIR / first_name).read_bytes() != live[first_name]:
            raise RuntimeError("safe installed target was not restored")
        cases.append(
            {
                "case": "pending_target_third_state",
                "status": "PASS_THIRD_STATE_PRESERVED_SAFE_TARGET_RESTORED_LOCK_RETAINED",
            }
        )

    report = {
        "schema": "noether-isv-v021-edit0002-transaction-tests-v1",
        "status": "PASS",
        "applicator": {
            "bytes": len(applicator_bytes),
            "sha256": applicator_sha256,
        },
        "candidate_locator_sha256": module.EXPECTED_LOCATOR_SHA256,
        "cases": cases,
        "live_source_files_written": 0,
        "all_writes": "Disposable TemporaryDirectory fixtures only",
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
