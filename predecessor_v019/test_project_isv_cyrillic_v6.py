#!/usr/bin/env python3
"""Independent read-only regression and hostile harness for Cyrillic v6."""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
IMPLEMENTATION = ROOT / "project_isv_cyrillic_v6.py"
IMPLEMENTATION_PIN = (
    13_333,
    "C7AE344B1E01DC0A8B655067173B66550D93E4D357CEB4FDB9713E80F9B9C0D6",
)
EXPECTED_OUTPUTS = {
    "44-book-isv.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "45-isv.tex": (
        35_902,
        "E1568BAB1E389E07816178A2FBDEE3833508C79BF0C7C19DD5120812E24646FE",
    ),
    "base-papers1-43-isv.tex": (
        2_706_660,
        "23C242AABD938C605A4B2293ED6E68B723F94DBD23279FD8E75CB50CAEF099F1",
    ),
    "bib-isv.tex": (
        13_255,
        "5A6AE75FF94360BC104CE240E0EC18A2329C5229F68B198F763EDF7E786B816B",
    ),
}
EXPECTED_REPORT_INTERNAL = (
    "E99B7E482A302EEAFF82056F5E53B5FF810EC8AC9DBC8F26BB747BE01259093A"
)


class V6TestError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise V6TestError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def load_implementation() -> Any:
    raw = IMPLEMENTATION.read_bytes()
    require((len(raw), sha256(raw)) == IMPLEMENTATION_PIN, "v6 implementation pin drift")
    spec = importlib.util.spec_from_file_location("isv019_cyr_v6_under_test", IMPLEMENTATION)
    require(spec is not None and spec.loader is not None, "cannot load v6 implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_reject(label: str, action: Callable[[], Any]) -> dict[str, Any]:
    try:
        action()
    except Exception as error:
        return {"case": label, "rejected": True, "error_type": type(error).__name__}
    raise V6TestError(f"hostile case passed: {label}")


def run() -> dict[str, Any]:
    v6 = load_implementation()
    v5 = v6.load_v5()
    source = v5.source_raws()
    tracked = [ROOT / "source_latin" / name for name in v5.SOURCE_ORDER]
    tracked.extend(ROOT / "source_cyrillic" / v5.OUTPUT_NAMES[name] for name in v5.SOURCE_ORDER)
    before = {str(path): sha256(path.read_bytes()) for path in tracked}

    report_a, output_a = v6.project_raws(source)
    report_b, output_b = v6.project_raws(source)
    require(canonical_json(report_a) == canonical_json(report_b), "duplicate report drift")
    require(output_a == output_b, "duplicate output drift")
    require(report_a["report_sha256_excluding_this_field"] == EXPECTED_REPORT_INTERNAL, "report hash drift")
    require(report_a["projection_issues"] == 0, "projection issue remains")
    require(report_a["tex_dimension_policy"]["cyrillic_dimension_residuals"] == 0, "Cyrillic dimension residual")
    require(report_a["tex_dimension_policy"]["occurrences"] == 447, "dimension occurrence drift")
    require(report_a["tex_dimension_policy"]["by_surface"] == {"em": 219, "pt": 228}, "dimension surface drift")
    require(
        report_a["conversion_classes"]
        == {
            "converted_after_explicit_etymological_simplification": 3_355,
            "converted_standard_isv": 161_208,
        },
        "conversion census drift",
    )
    for filename, pin in EXPECTED_OUTPUTS.items():
        raw = output_a[filename]
        require((len(raw), sha256(raw)) == pin, f"output pin drift: {filename}")
        require(not v6.CYRILLIC_DIMENSION_RE.search(raw.decode("utf-8")), f"Cyrillic TeX unit remains: {filename}")

    residuals: Counter[str] = Counter()
    for file_report in report_a["files"]:
        row = file_report["visible_latin_residuals"]
        require(row["all_covered_by_reviewed_output_ranges"] is True, "uncovered Latin residual")
        residuals.update(row["by_surface"])
    require({key: residuals[key] for key in ("I", "V", "M")} == {"I": 148, "V": 48, "M": 45}, "one-letter census drift")
    require(residuals["em"] == 219 and residuals["pt"] == 228, "protected TeX unit trace drift")

    hostiles = [
        expect_reject(
            "source_payload_mutation",
            lambda: v6.project_raws(
                {
                    **source,
                    v5.SOURCE_ORDER[0]: source[v5.SOURCE_ORDER[0]].replace(b"Noether", b"Noethes", 1),
                }
            ),
        ),
        expect_reject(
            "source_topology_omission",
            lambda: v6.project_raws({key: raw for key, raw in source.items() if key != v5.SOURCE_ORDER[-1]}),
        ),
        expect_reject(
            "unsafe_replacement_target",
            lambda: v6.replace_v5_outputs(ROOT / "source_latin", output_a),
        ),
        expect_reject(
            "dimension_census_mutation",
            lambda: v6.dimension_inventory(
                v5,
                v5.load_v4().load_v2(),
                {
                    name: raw.decode("utf-8").replace(
                        r"\emergencystretch=4em",
                        r"\emergencystretch=4zz",
                        1,
                    )
                    if name == "base-papers1-43-isv.tex"
                    else raw.decode("utf-8")
                    for name, raw in source.items()
                },
            ),
        ),
    ]
    after = {str(path): sha256(path.read_bytes()) for path in tracked}
    require(before == after, "read-only test mutated workspace files")
    output_manifest = [
        {"file": v5.OUTPUT_NAMES[name], "bytes": len(output_a[name]), "sha256": sha256(output_a[name])}
        for name in v5.SOURCE_ORDER
    ]
    return {
        "schema": "noether-isv-cyrillic-projection-v6-independent-test-v1",
        "status": "PASS",
        "implementation": {"path": IMPLEMENTATION.name, "bytes": IMPLEMENTATION_PIN[0], "sha256": IMPLEMENTATION_PIN[1]},
        "duplicate_runs_byte_identical": True,
        "report_sha256_excluding_this_field": EXPECTED_REPORT_INTERNAL,
        "output_manifest": output_manifest,
        "output_manifest_sha256": sha256(canonical_json(output_manifest)),
        "conversion_classes": report_a["conversion_classes"],
        "tex_dimension_occurrences_preserved": 447,
        "cyrillic_tex_dimension_residuals": 0,
        "hostile_cases": hostiles,
        "hostile_case_count": len(hostiles),
        "workspace_files_mutated": False,
    }


def main() -> int:
    try:
        payload = run()
    except Exception as error:
        payload = {
            "schema": "noether-isv-cyrillic-projection-v6-independent-test-failure-v1",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(payload))
        return 1
    sys.stdout.buffer.write(canonical_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
