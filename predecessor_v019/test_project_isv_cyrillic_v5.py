#!/usr/bin/env python3
"""Independent read-only regression and hostile harness for Cyrillic v5."""

from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
IMPLEMENTATION = ROOT / "project_isv_cyrillic_v5.py"
IMPLEMENTATION_PIN = (
    26_612,
    "723BD60F6CFE7C2E1192610215591C8D59BDECEAC778423FDEB4E105C831CFCB",
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
        2_707_554,
        "A9B016AA323C656063467393A3F0949D5CAAA611B8FDCE23172AF2D189D4B930",
    ),
    "bib-isv.tex": (
        13_255,
        "5A6AE75FF94360BC104CE240E0EC18A2329C5229F68B198F763EDF7E786B816B",
    ),
}
EXPECTED_REPORT_INTERNAL = (
    "429CC104F715E4A8A4CDACFE7B56A6F12011F738354D8EB422594E7406296363"
)


class V5TestError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise V5TestError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def load_implementation() -> Any:
    raw = IMPLEMENTATION.read_bytes()
    require((len(raw), sha256(raw)) == IMPLEMENTATION_PIN, "v5 implementation pin drift")
    spec = importlib.util.spec_from_file_location("isv019_cyr_v5_under_test", IMPLEMENTATION)
    require(spec is not None and spec.loader is not None, "cannot load v5 implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_reject(label: str, action: Callable[[], Any]) -> dict[str, Any]:
    try:
        action()
    except Exception as error:
        return {"case": label, "rejected": True, "error_type": type(error).__name__}
    raise V5TestError(f"hostile case passed: {label}")


def run() -> dict[str, Any]:
    v5 = load_implementation()
    report_a, output_a = v5.project_corpus()
    report_b, output_b = v5.project_corpus()
    require(canonical_json(report_a) == canonical_json(report_b), "duplicate report drift")
    require(output_a == output_b, "duplicate output drift")
    require(
        report_a["report_sha256_excluding_this_field"] == EXPECTED_REPORT_INTERNAL,
        "report internal hash drift",
    )
    for filename, expected in EXPECTED_OUTPUTS.items():
        raw = output_a[filename]
        require((len(raw), sha256(raw)) == expected, f"output pin drift: {filename}")
    require(report_a["projection_issues"] == 0, "projection issues remain")
    require(
        report_a["conversion_classes"]
        == {
            "converted_after_explicit_etymological_simplification": 3_355,
            "converted_standard_isv": 161_655,
        },
        "conversion census drift",
    )
    residuals: Counter[str] = Counter()
    for file_report in report_a["files"]:
        residual = file_report["visible_latin_residuals"]
        require(residual["all_covered_by_reviewed_output_ranges"] is True, "uncovered Latin residual")
        residuals.update(residual["by_surface"])
    require(
        {key: residuals[key] for key in ("I", "V", "M")}
        == {"I": 148, "V": 48, "M": 45},
        "one-letter preservation census drift",
    )
    require(sum(residuals[key] for key in ("I", "V", "M")) == 241, "one-letter union drift")
    require(
        report_a["selection"]["all_dispositions"]["PROJECT_LEXICAL_INTERSLAVIC_WORD"]
        == 449,
        "lexical I/V projection count drift",
    )

    v4 = v5.load_v4()
    v2 = v4.load_v2()
    source = v5.source_raws()
    for filename in v5.SOURCE_ORDER:
        before = source[filename].decode("utf-8")
        after = output_a[filename].decode("utf-8")
        require(before.count(r"\foreign{") == after.count(r"\foreign{"), f"foreign macro drift: {filename}")
        v2.validate_structure(after)

    manifest = v5.validate_manifest()
    texts = {
        name: v2.strict_transport(source[name], name) for name in v5.SOURCE_ORDER
    }
    first = copy.deepcopy(manifest["unprotected_style_payloads"][0])
    first["surface"] += "x"
    hostiles = [
        expect_reject(
            "source_payload_mutation",
            lambda: v5.project_raws(
                {
                    **source,
                    v5.SOURCE_ORDER[0]: source[v5.SOURCE_ORDER[0]].replace(
                        b"Noether", b"Noethes", 1
                    ),
                }
            ),
        ),
        expect_reject(
            "source_topology_omission",
            lambda: v5.project_raws(
                {key: value for key, value in source.items() if key != v5.SOURCE_ORDER[-1]}
            ),
        ),
        expect_reject(
            "manifest_surface_tamper",
            lambda: v5.validate_row(
                v2,
                texts[first["file"]],
                first,
                first["file"],
            ),
        ),
        expect_reject(
            "unmanifested_output_latin",
            lambda: v5.latin_visible_residuals(
                v2,
                output_a["45-isv.tex"].decode("utf-8").replace("И", "I", 1),
                [],
                "hostile-output.tex",
            ),
        ),
        expect_reject(
            "unsafe_output_directory",
            lambda: v5.write_outputs(IMPLEMENTATION, output_a),
        ),
    ]
    require(all(row["rejected"] for row in hostiles), "hostile rejection drift")
    output_manifest = [
        {"file": v5.OUTPUT_NAMES[name], "bytes": len(output_a[name]), "sha256": sha256(output_a[name])}
        for name in v5.SOURCE_ORDER
    ]
    return {
        "schema": "noether-isv-cyrillic-projection-v5-independent-test-v1",
        "status": "PASS",
        "implementation": {
            "path": IMPLEMENTATION.name,
            "bytes": IMPLEMENTATION_PIN[0],
            "sha256": IMPLEMENTATION_PIN[1],
        },
        "duplicate_runs_byte_identical": True,
        "report_sha256_excluding_this_field": EXPECTED_REPORT_INTERNAL,
        "output_manifest": output_manifest,
        "output_manifest_sha256": sha256(canonical_json(output_manifest)),
        "conversion_classes": report_a["conversion_classes"],
        "one_letter_preserved": {key: residuals[key] for key in ("I", "V", "M")},
        "one_letter_lexical_projected": 449,
        "hostile_cases": hostiles,
        "hostile_case_count": len(hostiles),
        "workspace_files_mutated": False,
    }


def main() -> int:
    try:
        payload = run()
    except Exception as error:
        payload = {
            "schema": "noether-isv-cyrillic-projection-v5-independent-test-failure-v1",
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
