#!/usr/bin/env python3
"""Deterministic no-write validation for project_isv_cyrillic_v2.py."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

import project_isv_cyrillic_v2 as scanner


ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "project_isv_cyrillic_v2.py"
FIXTURES = ROOT / "cyrillic_projection_v2_fixtures.json"
SOURCE_DIR = ROOT / "source_latin"

EXPECTED_SOURCE_MANIFEST = [
    {
        "file": "44-book-isv.tex",
        "bytes": 168_422,
        "sha256": "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    },
    {
        "file": "45-isv.tex",
        "bytes": 26_014,
        "sha256": "20B9123DFD81C0A3B3445A6CCAE8F711843F79C8D1DF75DF02406AF3A66A480F",
    },
    {
        "file": "base-papers1-43-isv.tex",
        "bytes": 1_892_315,
        "sha256": "2A35A7530685CF1A32AFDF92807D9FCFDD090FF2767211ABBE8B0D8DF0E29AA3",
    },
    {
        "file": "bib-isv.tex",
        "bytes": 9_939,
        "sha256": "71E4746C77776B1E504EF79EA9C097644219BFDF482004F1D4AAE45DA1C490C5",
    },
]

EXPECTED_UNSUPPORTED_BY_FILE = {
    "44-book-isv.tex": (0, 0),
    "45-isv.tex": (5, 5),
    "base-papers1-43-isv.tex": (512, 139),
    "bib-isv.tex": (8, 6),
}


def exact_source_manifest() -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for filename in scanner.SOURCE_ORDER:
        data = (SOURCE_DIR / filename).read_bytes()
        manifest.append(
            {
                "file": filename,
                "bytes": len(data),
                "sha256": scanner.sha256_bytes(data),
            }
        )
    return manifest


def fixture_by_name(name: str) -> dict[str, Any]:
    payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return next(item for item in payload["fixtures"] if item["name"] == name)


class V2ScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_manifest_before = exact_source_manifest()
        cls.fixture_run_1 = scanner.run_fixtures(FIXTURES)
        cls.fixture_run_2 = scanner.run_fixtures(FIXTURES)
        cls.corpus_run_1 = scanner.scan_corpus(SOURCE_DIR)
        cls.corpus_run_2 = scanner.scan_corpus(SOURCE_DIR)
        command = [sys.executable, "-B", str(MODULE)]
        cls.process_run_1 = subprocess.run(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
        cls.process_run_2 = subprocess.run(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
        cls.source_manifest_after = exact_source_manifest()

    def test_01_exact_edit0149_source_pins(self) -> None:
        self.assertEqual(self.source_manifest_before, EXPECTED_SOURCE_MANIFEST)
        self.assertEqual(self.source_manifest_after, EXPECTED_SOURCE_MANIFEST)

    def test_02_fixture_receipt_is_exact_and_repeatable(self) -> None:
        self.assertEqual(
            scanner.canonical_json_bytes(self.fixture_run_1),
            scanner.canonical_json_bytes(self.fixture_run_2),
        )
        self.assertEqual(self.fixture_run_1["fixture_count"], 19)
        self.assertEqual(self.fixture_run_1["passed"], 19)
        self.assertEqual(self.fixture_run_1["failed"], 0)
        self.assertEqual(
            self.fixture_run_1["fixture_file_sha256"],
            "B0CAA4B4F018F28376CD8EE75375FFD5F999B3E0086BD030B1F796CEDE5CD87A",
        )
        self.assertEqual(
            self.fixture_run_1["receipt_sha256_excluding_this_field"],
            "C21766C80B2603B4FF24D379E7219C99363ACC8E74959B10F1F6D36EB841CBD4",
        )

    def test_03_rowbreak_then_real_inline_math_is_command_aware(self) -> None:
        fixture = fixture_by_name("rowbreak_then_literal_paren_then_real_inline_math")
        result = scanner.scan_text(fixture["input"], "rowbreak-hostile.tex")
        self.assertEqual([item["token"] for item in result["issues"]], ["q"])
        self.assertEqual(result["structural"]["unmatched_math_delimiters"], 0)
        self.assertEqual(result["coverage"]["status"], "PASS")

    def test_04_mismatched_exact_environment_names_fail_closed(self) -> None:
        fixture = fixture_by_name("mismatched_align_equation_is_rejected")
        with self.assertRaises(scanner.ProjectionError) as caught:
            scanner.scan_text(fixture["input"], "mismatch-hostile.tex")
        self.assertEqual(caught.exception.code, "mismatched_environment_end")

    def test_05_cross_pass_masking_hostile_keeps_visible_q(self) -> None:
        fixture = fixture_by_name("two_align_star_environments_do_not_cross_mask")
        result = scanner.scan_text(fixture["input"], "cross-pass-hostile.tex")
        self.assertEqual([item["token"] for item in result["issues"]], ["q"])
        self.assertFalse(self.corpus_run_1["parser_policy"]["placeholder_masking"])
        self.assertFalse(
            self.corpus_run_1["parser_policy"]["parity_escape_heuristic"]
        )

    def test_06_current_head_census_is_independently_reproduced(self) -> None:
        summary = self.corpus_run_1["summary"]
        self.assertEqual(summary["unsupported_occurrences"], 525)
        self.assertEqual(summary["unique_unsupported_surfaces"], 143)
        self.assertEqual(summary["unique_unsupported_casefolds"], 142)
        observed = {
            filename: (
                values["unsupported_occurrences"],
                values["unique_unsupported_casefolds"],
            )
            for filename, values in summary["by_file"].items()
        }
        self.assertEqual(observed, EXPECTED_UNSUPPORTED_BY_FILE)
        self.assertEqual(summary["unknown_argument_commands"], 0)
        self.assertEqual(summary["parse_errors"], 0)
        self.assertEqual(summary["coverage_failures"], 0)
        self.assertEqual(summary["roman_identity_hold_occurrences"], 704)
        reconciliation = self.corpus_run_1["edit0149_legacy_census_reconciliation"]
        self.assertEqual(reconciliation["legacy"]["unsupported_occurrences"], 519)
        self.assertEqual(reconciliation["legacy"]["unique_surface_tokens"], 139)
        self.assertEqual(reconciliation["legacy"]["unique_casefold_tokens"], 135)
        self.assertEqual(
            reconciliation["legacy"]["auditor_inventory_receipts"][
                "aggregate_exact_surface"
            ],
            {
                "bytes": 2230,
                "sha256": "98BC5C7A3DFC708063E89A739C3322D2600791A6087E329C93D73FE80655BC68",
            },
        )
        self.assertEqual(reconciliation["delta"]["unsupported_occurrences"], 6)
        swap = reconciliation["role_policy_swap"]
        self.assertEqual(swap["exact_surface_multiset_delta"]["added_total"], 135)
        self.assertEqual(swap["exact_surface_multiset_delta"]["removed_total"], 129)
        self.assertEqual(swap["newly_visible_mapping_blocks"]["total"], 130)
        self.assertEqual(swap["legacy_false_positives_now_protected"]["total"], 124)
        self.assertEqual(519 + 130 - 124, summary["unsupported_occurrences"])

    def test_07_every_source_has_gap_free_roles_and_zero_unmatched_state(self) -> None:
        for result in self.corpus_run_1["files"]:
            with self.subTest(file=result["label"]):
                self.assertEqual(result["coverage"]["start"], 0)
                self.assertEqual(result["coverage"]["end"], result["input_scalars"])
                self.assertEqual(result["coverage"]["gaps"], 0)
                self.assertEqual(result["coverage"]["overlaps"], 0)
                self.assertEqual(result["coverage"]["status"], "PASS")
                self.assertEqual(
                    sum(result["role_scalars"].values()), result["input_scalars"]
                )
                self.assertEqual(result["structural"]["unmatched_braces"], 0)
                self.assertEqual(result["structural"]["unmatched_environments"], 0)
                self.assertEqual(
                    result["structural"]["unmatched_math_delimiters"], 0
                )
                self.assertEqual(result["protected_stream"]["status"], "PASS")
                self.assertEqual(result["unknown_argument_commands"], [])

    def test_08_in_process_report_is_byte_deterministic(self) -> None:
        self.assertEqual(
            scanner.canonical_json_bytes(self.corpus_run_1),
            scanner.canonical_json_bytes(self.corpus_run_2),
        )
        self.assertEqual(self.corpus_run_1["source_manifest"], EXPECTED_SOURCE_MANIFEST)

    def test_09_two_fresh_default_processes_are_byte_deterministic_and_read_only(self) -> None:
        for process in (self.process_run_1, self.process_run_2):
            self.assertEqual(process.returncode, 0)
            self.assertEqual(process.stderr, b"")
        self.assertEqual(self.process_run_1.stdout, self.process_run_2.stdout)
        observed = json.loads(self.process_run_1.stdout.decode("utf-8"))
        self.assertEqual(observed, scanner.compact_summary(self.corpus_run_1))
        self.assertEqual(self.source_manifest_before, self.source_manifest_after)

    def test_10_transport_failures_are_explicit(self) -> None:
        cases = {
            "bom": b"\xef\xbb\xbf\\begin{document}\n\\end{document}\n",
            "crlf": b"\\begin{document}\r\n\\end{document}\r\n",
            "terminal_lf": b"\\begin{document}\n\\end{document}",
        }
        expected = {
            "bom": "utf8_bom",
            "crlf": "non_lf_newline",
            "terminal_lf": "missing_terminal_lf",
        }
        for label, data in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(scanner.ProjectionError) as caught:
                    scanner.strict_transport(data, label)
                self.assertEqual(caught.exception.code, expected[label])

    def test_11_foreign_span_sequence_is_byte_exact_in_diagnostic_projection(self) -> None:
        expected_counts = {
            "44-book-isv.tex": 16,
            "45-isv.tex": 19,
            "base-papers1-43-isv.tex": 196,
            "bib-isv.tex": 47,
        }
        for filename in scanner.SOURCE_ORDER:
            text = scanner.strict_transport((SOURCE_DIR / filename).read_bytes(), filename)
            result = scanner.scan_text(text, filename)
            spans = result["foreign_spans"]
            self.assertEqual(len(spans), expected_counts[filename])
            projected = result["projected_text"]
            projected_cursor = 0
            for span in spans:
                raw = text[span["start"] : span["end"]]
                self.assertEqual(scanner.sha256_bytes(raw.encode("utf-8")), span["sha256"])
                projected_start = projected.find(raw, projected_cursor)
                self.assertGreaterEqual(projected_start, projected_cursor)
                projected_cursor = projected_start + len(raw)


def validation_receipt(result: unittest.TestResult) -> dict[str, Any]:
    failures = [test.id() for test, _ in result.failures]
    errors = [test.id() for test, _ in result.errors]
    receipt: dict[str, Any] = {
        "schema": "noether-isv-cyrillic-v2-test-run-1",
        "module": {
            "path": MODULE.name,
            "bytes": len(MODULE.read_bytes()),
            "sha256": scanner.sha256_bytes(MODULE.read_bytes()),
        },
        "test_file": {
            "path": Path(__file__).name,
            "bytes": len(Path(__file__).read_bytes()),
            "sha256": scanner.sha256_bytes(Path(__file__).read_bytes()),
        },
        "fixture_file": {
            "path": FIXTURES.name,
            "bytes": len(FIXTURES.read_bytes()),
            "sha256": scanner.sha256_bytes(FIXTURES.read_bytes()),
        },
        "source_manifest": V2ScannerTests.source_manifest_after,
        "tests_run": result.testsRun,
        "passed": result.testsRun - len(failures) - len(errors),
        "failures": failures,
        "errors": errors,
        "fixture_receipt_sha256": V2ScannerTests.fixture_run_1[
            "receipt_sha256_excluding_this_field"
        ],
        "corpus_report_sha256": V2ScannerTests.corpus_run_1[
            "report_sha256_excluding_this_field"
        ],
        "census": {
            "unsupported_occurrences": V2ScannerTests.corpus_run_1["summary"][
                "unsupported_occurrences"
            ],
            "unique_unsupported_surfaces": V2ScannerTests.corpus_run_1["summary"][
                "unique_unsupported_surfaces"
            ],
            "unique_unsupported_casefolds": V2ScannerTests.corpus_run_1[
                "summary"
            ]["unique_unsupported_casefolds"],
            "unsupported_inventory_sha256": V2ScannerTests.corpus_run_1[
                "summary"
            ]["unsupported_inventory_sha256"],
            "roman_identity_hold_occurrences": V2ScannerTests.corpus_run_1[
                "summary"
            ]["roman_identity_hold_occurrences"],
        },
        "fresh_process_stdout": {
            "bytes": len(V2ScannerTests.process_run_1.stdout),
            "sha256": scanner.sha256_bytes(V2ScannerTests.process_run_1.stdout),
            "byte_identical_runs": 2,
        },
        "writes_performed": False,
        "build_performed": False,
        "git_used": False,
        "network_used": False,
        "status": "PASS" if result.wasSuccessful() else "FAIL",
    }
    receipt["receipt_sha256_excluding_this_field"] = scanner.sha256_bytes(
        scanner.canonical_json_bytes(receipt)
    )
    return receipt


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(V2ScannerTests)
    sink = io.StringIO()
    result = unittest.TextTestRunner(stream=sink, verbosity=0).run(suite)
    sys.stdout.buffer.write(scanner.canonical_json_bytes(validation_receipt(result)))
    if not result.wasSuccessful():
        sys.stderr.write(sink.getvalue())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
