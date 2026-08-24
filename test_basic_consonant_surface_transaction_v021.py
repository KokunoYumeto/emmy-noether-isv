#!/usr/bin/env python3
"""Bounded TemporaryDirectory transaction tests for ISV021-EDIT-0010-R2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
from typing import Any


LIVE_ROOT = Path(__file__).resolve().parent
APP_PATH = LIVE_ROOT / "apply_basic_consonant_surface_v021.py"
APP_PIN = (
    9_521,
    "1EBEC3C973900CBCF6D32FA39AFB6D94804173AE44C837901210008CBA5CF1F8",
)
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_app() -> Any:
    data = APP_PATH.read_bytes()
    if (len(data), digest(data)) != APP_PIN:
        raise RuntimeError("EDIT-0010-R2 applicator pin drift")
    module = types.ModuleType("isv021_edit0010_r2_test_target")
    module.__file__ = str(APP_PATH)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    exec(compile(data, str(APP_PATH), "exec"), module.__dict__)
    return module


APP = load_app()
LIVE_COHORT = {
    name: (LIVE_ROOT / "source_latin" / name).read_bytes() for name in SOURCE_ORDER
}
if APP.observed_pins(LIVE_COHORT) != APP.PREDECESSOR:
    raise RuntimeError("live cohort is not the frozen EDIT-0010-R2 predecessor")


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temp = tempfile.TemporaryDirectory(prefix="isv021-edit0010-r2-test-")
    root = Path(temp.name)
    source = root / "source_latin"
    source.mkdir()
    for name, data in LIVE_COHORT.items():
        (source / name).write_bytes(data)
    return temp, root


def configure(root: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    APP.ROOT = root
    APP.SOURCE_DIR = root / "source_latin"
    cohort = APP.read_cohort()
    live_report = APP.AUDIT.build_report()
    manifest = live_report["locator_manifest"]["value"]
    outputs = APP.AUDIT.BASE.project(cohort, manifest)
    if APP.observed_pins(outputs) != APP.SUCCESSOR:
        raise RuntimeError("fixture projection mismatch")
    APP.configure_transaction_core()
    return cohort, outputs


def residue(root: Path) -> list[str]:
    names: list[str] = []
    for directory in (root, root / "source_latin"):
        names.extend(
            str(path.relative_to(root))
            for path in directory.iterdir()
            if APP.EDIT_ID in path.name
        )
    return sorted(names)


def case_success() -> dict[str, Any]:
    temp, root = fixture()
    try:
        cohort, outputs = configure(root)
        APP.CORE.apply_transaction(cohort, outputs)
        observed = APP.read_cohort()
        if APP.observed_pins(observed) != APP.SUCCESSOR or residue(root):
            raise RuntimeError("success case did not close coherently")
        return {"case": "success", "state": "successor", "residue": 0}
    finally:
        temp.cleanup()


def case_fail_during_install() -> dict[str, Any]:
    temp, root = fixture()
    original_assert_owned = APP.CORE.assert_owned
    injected = False
    try:
        cohort, outputs = configure(root)

        def failing_assert_owned(
            path: Path,
            expected_identity: Any,
            expected_pin: Any,
            label: str,
        ) -> None:
            nonlocal injected
            if not injected and label == "installed target base-papers1-43-isv.tex":
                injected = True
                raise OSError("injected post-install audit failure")
            original_assert_owned(path, expected_identity, expected_pin, label)

        APP.CORE.assert_owned = failing_assert_owned
        try:
            APP.CORE.apply_transaction(cohort, outputs)
        except OSError as error:
            if "injected post-install audit failure" not in str(error):
                raise
        else:
            raise RuntimeError("mid-install failure was not raised")
        observed = APP.read_cohort()
        if APP.observed_pins(observed) != APP.PREDECESSOR or residue(root):
            raise RuntimeError("mid-install failure did not restore predecessor")
        return {
            "case": "failure_after_install_before_coherence",
            "state": "predecessor",
            "reinstalled_predecessor": True,
            "residue": 0,
        }
    finally:
        APP.CORE.assert_owned = original_assert_owned
        temp.cleanup()


def case_cleanup_failure_after_coherent_install() -> dict[str, Any]:
    temp, root = fixture()
    original_unlink = APP.CORE.Path.unlink
    injected = False
    try:
        cohort, outputs = configure(root)

        def failing_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
            nonlocal injected
            if not injected and path.name.endswith(".rollback"):
                injected = True
                raise OSError("injected rollback-cleanup failure")
            original_unlink(path, *args, **kwargs)

        APP.CORE.Path.unlink = failing_unlink
        try:
            APP.CORE.apply_transaction(cohort, outputs)
        except RuntimeError as error:
            if "successor installed but transaction cleanup failed" not in str(error):
                raise
        else:
            raise RuntimeError("cleanup failure was not raised")
        observed = APP.read_cohort()
        remaining = residue(root)
        if APP.observed_pins(observed) != APP.SUCCESSOR:
            raise RuntimeError("cleanup failure disturbed coherent successor")
        if not any(name.endswith(".lock") for name in remaining):
            raise RuntimeError("cleanup failure did not retain transaction lock")
        if not any(name.endswith(".rollback") for name in remaining):
            raise RuntimeError("cleanup failure did not retain rollback evidence")
        return {
            "case": "cleanup_failure_after_coherent_install",
            "state": "successor",
            "lock_retained": True,
            "rollback_retained": True,
        }
    finally:
        APP.CORE.Path.unlink = original_unlink
        temp.cleanup()


def main() -> int:
    report = {
        "schema": "noether-isv-v021-edit0010-r2-transaction-test-v1",
        "status": "PASS",
        "applicator": {"bytes": APP_PIN[0], "sha256": APP_PIN[1]},
        "cases": [
            case_success(),
            case_fail_during_install(),
            case_cleanup_failure_after_coherent_install(),
        ],
        "live_source_writes": 0,
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
