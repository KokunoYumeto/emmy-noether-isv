#!/usr/bin/env python3
"""Disposable fault tests for the v021 Cyrillic output installer only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
PROJECTOR_PATH = ROOT / "project_isv_cyrillic_v8.py"
PROJECTOR_PIN = (
    34_267,
    "06CC1640E253513EFF64918E6CC3BCE583913D3E64B2F93F1B77C3734BABDC8C",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_projector():
    raw = PROJECTOR_PATH.read_bytes()
    require((len(raw), sha256(raw)) == PROJECTOR_PIN, "projector pin drift")
    spec = importlib.util.spec_from_file_location("isv021_v8_installer_test", PROJECTOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load projector")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fake_outputs(module) -> dict[str, bytes]:
    return {
        name: (f"% deterministic disposable {ordinal}: {name}\n").encode("utf-8")
        for ordinal, name in enumerate(module.SOURCE_ORDER, 1)
    }


def inventory(path: Path) -> list[str]:
    return sorted(item.name for item in path.iterdir())


def main() -> int:
    module = load_projector()
    projected = fake_outputs(module)
    results: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="isv021-v8-clean-") as temporary:
        output = Path(temporary)
        module.OUTPUT_DIR = output
        first = module.install_outputs(output, projected)
        require(
            all((output / module.OUTPUT_NAMES[name]).read_bytes() == projected[name] for name in module.SOURCE_ORDER),
            "clean install payload drift",
        )
        second = module.install_outputs(output, projected)
        require(first == second, "idempotent replay report drift")
        require(
            inventory(output) == sorted(module.OUTPUT_NAMES.values()),
            "clean install left transaction residue",
        )
        results["clean_and_idempotent"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="isv021-v8-third-state-") as temporary:
        output = Path(temporary)
        module.OUTPUT_DIR = output
        first_name = module.SOURCE_ORDER[0]
        (output / module.OUTPUT_NAMES[first_name]).write_bytes(b"different\n")
        try:
            module.install_outputs(output, projected)
        except Exception:
            pass
        else:
            raise RuntimeError("third-state output was accepted")
        require(
            inventory(output) == [module.OUTPUT_NAMES[first_name]],
            "third-state refusal wrote another target",
        )
        require(
            (output / module.OUTPUT_NAMES[first_name]).read_bytes() == b"different\n",
            "third-state evidence changed",
        )
        results["third_state_refusal"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="isv021-v8-fault-") as temporary:
        output = Path(temporary)
        module.OUTPUT_DIR = output
        original_replace = module.os.replace
        calls = 0

        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected second-install failure")
            return original_replace(source, target)

        module.os.replace = fail_second
        try:
            try:
                module.install_outputs(output, projected)
            except OSError as error:
                require("injected" in str(error), "unexpected fault error")
            else:
                raise RuntimeError("injected fault did not fire")
        finally:
            module.os.replace = original_replace
        require(inventory(output) == [], "fault rollback left output or stage residue")
        results["second_install_fault_cleanup"] = "PASS"

    try:
        module.main([
            "--write-output-dir",
            "source_cyrillic",
            "--write-receipt",
            "decision_records/forbidden-combined-transaction.json",
        ])
    except module.ProjectionV8Error as error:
        require("separate fail-closed transactions" in str(error), "unexpected combined-flag refusal")
    else:
        raise RuntimeError("combined output/receipt transaction was accepted")
    results["combined_output_and_receipt_refusal_before_projection"] = "PASS"

    payload = {
        "schema": "noether-isv-v021-cyrillic-v8-install-transaction-test-v1",
        "status": "PASS",
        "projector": {
            "bytes": PROJECTOR_PIN[0],
            "sha256": PROJECTOR_PIN[1],
        },
        "tests": results,
        "live_output_writes": 0,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
