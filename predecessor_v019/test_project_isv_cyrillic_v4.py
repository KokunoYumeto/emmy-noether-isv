#!/usr/bin/env python3
"""Independent bounded checks for the current-head Cyrillic v4 wrapper."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
V4_PATH = ROOT / "project_isv_cyrillic_v4.py"
V2_PATH = ROOT / "project_isv_cyrillic_v2.py"
V3_PATH = ROOT / "project_isv_cyrillic_v3.py"
SOURCE_DIR = ROOT / "source_latin"
V4_PIN = (
    34_849,
    "A63A6F697A99F5A8D64C0B69D24875C3031C8EFE7DE8A137DE8F844CD460E341",
)
V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
V3_PIN = (
    24_314,
    "84B845424CB2501289220727B1300280894512EDD137DC13B188A577049AF1B7",
)


class TestFailure(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TestFailure(message)


def load_exact(path: Path, pin: tuple[int, str], name: str) -> Any:
    raw = path.read_bytes()
    require((len(raw), sha256(raw)) == pin, f"{name} pin drift")
    spec = importlib.util.spec_from_file_location(f"independent_{name}", path)
    require(spec is not None and spec.loader is not None, f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_failure(label: str, action: Any) -> dict[str, Any]:
    try:
        action()
    except Exception as error:
        return {"case": label, "rejected": True, "error_type": type(error).__name__}
    raise TestFailure(f"hostile case passed: {label}")


def main() -> int:
    v4 = load_exact(V4_PATH, V4_PIN, "v4")
    v2 = load_exact(V2_PATH, V2_PIN, "v2")
    v3 = load_exact(V3_PATH, V3_PIN, "v3")
    raws = {name: (SOURCE_DIR / name).read_bytes() for name in v4.SOURCE_ORDER}

    first = v4.scan_corpus()
    require(first["head_validation"]["decision_id"] == "ISV019-EDIT-0158", "head drift")

    direct_v2 = v2.scan_corpus(SOURCE_DIR)
    direct_remaining: list[dict[str, Any]] = []
    direct_structural: list[dict[str, Any]] = []
    for file_report in direct_v2["files"]:
        for issue in file_report["issues"]:
            if (
                "unlisted_structural_roman_identity" in issue["reasons"]
                or issue["token"] == "X"
            ):
                direct_structural.append(issue)
            else:
                direct_remaining.append(issue)
    emitted_remaining = [
        issue for file_report in first["files"] for issue in file_report["issues"]
    ]
    require(emitted_remaining == direct_remaining, "independent remaining issue stream drift")
    require(len(direct_structural) == 722, "independent structural count drift")
    require(
        v2.issue_inventory_sha256(direct_structural)
        == first["structural_policy"]["issue_inventory_sha256"],
        "independent structural inventory drift",
    )
    require(
        v2.issue_inventory_sha256(direct_remaining)
        == first["summary"]["blocked_inventory_sha256"],
        "independent remaining inventory drift",
    )
    require(first["summary"]["blocked_occurrences"] == 307, "frontier count drift")
    require(first["summary"]["unsupported_occurrences"] == 307, "mapping count drift")
    require(first["summary"]["roman_identity_hold_occurrences"] == 0, "Roman hold drift")

    in_memory = v4.scan_raws(raws)
    require(in_memory["head_validation"] is None, "in-memory scan claims a sealed head")
    require(in_memory["summary"] == first["summary"], "in-memory summary drift")

    first_issue = direct_remaining[0]
    label = first_issue["file"]
    text = raws[label].decode("utf-8")
    start = first_issue["scalar_offset"]
    token = first_issue["token"]
    require(text[start : start + len(token)] == token, "projected test locator drift")
    protected_raws = dict(raws)
    protected_raws[label] = (
        text[:start] + "\\foreign{" + token + "}" + text[start + len(token) :]
    ).encode("utf-8")
    protected = v4.scan_raws(protected_raws)
    require(
        protected["summary"]["blocked_occurrences"] == 306,
        "projected protection did not reduce frontier by one",
    )

    hostile_raws = dict(raws)
    base = hostile_raws["base-papers1-43-isv.tex"].decode("utf-8")
    marker = "\\end{document}"
    require(marker in base, "end-document marker missing")
    hostile_raws["base-papers1-43-isv.tex"] = base.replace(
        marker, " XVIII\n" + marker, 1
    ).encode("utf-8")
    hostiles = [
        expect_failure(
            "new_unreviewed_structural_surface",
            lambda: v4.scan_raws(hostile_raws),
        ),
        expect_failure(
            "historical_v3_current_head_pin_failure",
            lambda: v3.scan_corpus(),
        ),
    ]

    self_first = v4.run_self_test()
    require(self_first["status"] == "PASS", "self-test did not pass")

    payload = {
        "schema": "noether-isv-cyrillic-projection-v4-independent-test-v1",
        "status": "PASS",
        "head": first["head_validation"]["decision_id"],
        "source_manifest": first["source_manifest"],
        "frontier": {
            "blocked": first["summary"]["blocked_occurrences"],
            "unsupported": first["summary"]["unsupported_occurrences"],
            "roman_holds": first["summary"]["roman_identity_hold_occurrences"],
            "inventory_sha256": first["summary"]["blocked_inventory_sha256"],
        },
        "structural": first["structural_policy"],
        "hostiles": hostiles,
        "self_test_hostiles": self_first["hostile_case_count"],
        "scan_pair_sha256": sha256(canonical(first)),
        "workspace_files_mutated": False,
    }
    sys.stdout.buffer.write(canonical(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
