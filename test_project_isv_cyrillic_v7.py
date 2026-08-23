#!/usr/bin/env python3
"""Read-only hostile/regression harness for project_isv_cyrillic_v7.py.

The harness independently loads the pinned projector twice, keeps every
projection in memory, checks the frozen report/effect/delta/output identities,
replays the licensed-line boundary, and proves fail-closed rejection of several
tampered inputs without altering any canonical file.  Default execution writes
nothing and emits one canonical JSON receipt on stdout.
"""

from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
PROJECTOR_PATH = ROOT / "project_isv_cyrillic_v7.py"
MANIFEST_PATH = ROOT / "decision_records/ISV020-REVIEWED-PROJECTION-ROLE-MANIFEST.json"
SOURCE_DIR = ROOT / "source_latin"
PRED = ROOT / "predecessor_v019"
OLD_OUTPUT_DIR = PRED / "source_cyrillic"
OUTPUT_DIR = ROOT / "source_cyrillic"
V6_PATH = PRED / "project_isv_cyrillic_v6.py"

PROJECTOR_PIN = (
    27_666,
    "51E467EDD8F0B8F44F62D60C4F5D35EAB5BA80EEFA1B0BFCBC1A2EF0B3538915",
)
V6_PIN = (
    13_333,
    "C7AE344B1E01DC0A8B655067173B66550D93E4D357CEB4FDB9713E80F9B9C0D6",
)
MANIFEST_PIN = (
    3_577_349,
    "192BAE284EDC9BBA4A458EEBA9F7541CE16CA377A68668A70F5CFD0A2E182462",
)
MANIFEST_INTERNAL = "90EAFFEA8C2B8C17E301CCA94F80029CD1A3454E514EA3B3390376C300FDBCDE"

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
SOURCE_PINS = {
    "44-book-isv.tex": (
        168_422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    "45-isv.tex": (
        26_053,
        "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91",
    ),
    "base-papers1-43-isv.tex": (
        1_894_721,
        "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
OUTPUT_NAMES = {
    "44-book-isv.tex": "44-book-isv-cyrl.tex",
    "45-isv.tex": "45-isv-cyrl.tex",
    "base-papers1-43-isv.tex": "base-papers1-43-isv-cyrl.tex",
    "bib-isv.tex": "bib-isv-cyrl.tex",
}
OUTPUT_PINS = {
    "44-book-isv.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "45-isv.tex": (
        35_895,
        "F94F731110DA94B30B9243C67587CB6A1B6E6478A046F08C617271A0B188CCFB",
    ),
    "base-papers1-43-isv.tex": (
        2_706_558,
        "8BB578C1B2D7B48E52A425D40039FE5A6B79FF1ED26E825A6BDA7EE736341277",
    ),
    "bib-isv.tex": (
        13_206,
        "4E74B8EA52C9B37209345B7E9A0B6BD7330D8EA0570E6D0C164FEA113511613D",
    ),
}
OLD_OUTPUT_PINS = {
    "44-book-isv-cyrl.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "45-isv-cyrl.tex": (
        35_902,
        "E1568BAB1E389E07816178A2FBDEE3833508C79BF0C7C19DD5120812E24646FE",
    ),
    "base-papers1-43-isv-cyrl.tex": (
        2_706_660,
        "23C242AABD938C605A4B2293ED6E68B723F94DBD23279FD8E75CB50CAEF099F1",
    ),
    "bib-isv-cyrl.tex": (
        13_255,
        "5A6AE75FF94360BC104CE240E0EC18A2329C5229F68B198F763EDF7E786B816B",
    ),
}

FULL_REPORT_PIN = (
    18_467,
    "A8A3BD388D563ACBAFA952BFFE538A845D619B4E320C5D9EE566247B2D481E65",
)
COMPACT_REPORT_PIN = (
    4_641,
    "97C7DECB84D93E6D08ED96131D0780C2381F1771FE336BCFC45D709A91F639E6",
)
REPORT_INTERNAL = "95AA80566CCF69FC6766048E68235DC5544DE2CEF7024A37F3964BC19EDBA992"
OUTPUT_MANIFEST_SHA256 = "01F03EA43817E53B2D80D9F10CFCE2E82EE3D60945D373825A2164EB3C8E6886"
DELTA_INVENTORY_PIN = (
    31_070,
    "0B74E725E13DFA0004510BE65BE1B1CB4395E55D2FB032CA5D41ECC400D12812",
)
EFFECT_INVENTORY_PIN = (
    116_313,
    "C075649CA3F5D0BDC9CFEF0B1D593E67F7F3561403FE65941968C423D738D7F3",
)
DIMENSION_INVENTORY_PIN = (
    178_677,
    "A0C59C238840A60910A797E35374F37620EE5B7EDF669E06A1A02190D08C4235",
)
EXPECTED_ACTUAL_CHANGED_LINES = {
    "44-book-isv.tex": 0,
    "45-isv.tex": 6,
    "base-papers1-43-isv.tex": 115,
    "bib-isv.tex": 4,
}
EXPECTED_ALLOWED_CHANGED_LINES = {
    "44-book-isv.tex": 4,
    "45-isv.tex": 16,
    "base-papers1-43-isv.tex": 272,
    "bib-isv.tex": 17,
}
EXPECTED_DIMENSION_CENSUS = {
    "44-book-isv.tex": {"cm": 1, "em": 7, "pt": 6},
    "45-isv.tex": {"cm": 1, "em": 20, "pt": 9},
    "base-papers1-43-isv.tex": {"cm": 2, "em": 575, "mm": 5, "pt": 470},
    "bib-isv.tex": {"cm": 1, "em": 16, "pt": 6},
}


class HarnessError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def describe(raw: bytes) -> dict[str, Any]:
    return {"bytes": len(raw), "sha256": sha256(raw)}


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_regular(path: Path, label: str) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe {label}: {path}")
    return path.read_bytes()


def read_pin(path: Path, pin: tuple[int, str], label: str) -> bytes:
    raw = read_regular(path, label)
    require((len(raw), sha256(raw)) == pin, f"pin drift: {label}")
    return raw


def strict_json(raw: bytes, label: str) -> Any:
    require(raw.endswith(b"\n") and b"\r" not in raw, f"transport drift: {label}")
    require(not raw.startswith(b"\xef\xbb\xbf"), f"BOM not allowed: {label}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def path_identity(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        return {"kind": "symlink", "target": str(path.readlink())}
    if path.is_file():
        return {"kind": "file", **describe(path.read_bytes())}
    if path.is_dir():
        entries = []
        for entry in sorted(path.iterdir(), key=lambda item: item.name):
            if entry.is_symlink():
                kind = "symlink"
            elif entry.is_file():
                kind = "file"
            elif entry.is_dir():
                kind = "directory"
            else:
                kind = "other"
            entries.append({"name": entry.name, "kind": kind})
        return {"kind": "directory", "entries": entries}
    return {"kind": "missing"}


def watched_snapshot() -> dict[str, Any]:
    paths = [
        Path(__file__).resolve(),
        PROJECTOR_PATH,
        MANIFEST_PATH,
        V6_PATH,
        SOURCE_DIR,
        OLD_OUTPUT_DIR,
        OUTPUT_DIR,
        ROOT / "__pycache__",
        PRED / "__pycache__",
    ]
    paths.extend(SOURCE_DIR / name for name in SOURCE_ORDER)
    paths.extend(OLD_OUTPUT_DIR / OUTPUT_NAMES[name] for name in SOURCE_ORDER)
    paths.extend(OUTPUT_DIR / OUTPUT_NAMES[name] for name in SOURCE_ORDER)
    unique = sorted(set(paths), key=lambda item: relative(item))
    return {relative(path): path_identity(path) for path in unique}


def load_v7(module_name: str) -> Any:
    read_pin(PROJECTOR_PATH, PROJECTOR_PIN, "v020 v7 projector")
    spec = importlib.util.spec_from_file_location(module_name, PROJECTOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v7 projector")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    require(module.V6_PIN == V6_PIN, "v7 embedded v6 pin drift")
    require(module.MANIFEST_PIN == MANIFEST_PIN, "v7 embedded manifest pin drift")
    require(module.MANIFEST_INTERNAL == MANIFEST_INTERNAL, "v7 embedded manifest internal pin drift")
    require(module.SOURCE_PINS == SOURCE_PINS, "v7 embedded source pins drift")
    require(module.OLD_OUTPUT_PINS == OLD_OUTPUT_PINS, "v7 embedded old-output pins drift")
    require(tuple(module.SOURCE_ORDER) == SOURCE_ORDER, "v7 source order drift")
    require(module.OUTPUT_NAMES == OUTPUT_NAMES, "v7 output-name mapping drift")
    return module


def source_raws() -> dict[str, bytes]:
    return {
        filename: read_pin(SOURCE_DIR / filename, SOURCE_PINS[filename], filename)
        for filename in SOURCE_ORDER
    }


def independent_manifest_review() -> tuple[dict[str, Any], dict[str, set[int]], dict[str, int]]:
    raw = read_pin(MANIFEST_PATH, MANIFEST_PIN, "reviewed role manifest")
    value = strict_json(raw, relative(MANIFEST_PATH))
    require(isinstance(value, dict), "manifest root is not an object")
    claimed = value.get("inventory_sha256_excluding_this_field")
    without = copy.deepcopy(value)
    without.pop("inventory_sha256_excluding_this_field", None)
    require(claimed == MANIFEST_INTERNAL, "manifest internal claim drift")
    require(sha256(canonical_json(without)) == MANIFEST_INTERNAL, "manifest internal digest mismatch")
    require(value.get("scope", {}).get("latin_source_bytes_changed") == 0, "manifest permits Latin drift")
    require(value.get("review", {}).get("ambiguities") == 0, "manifest retains ambiguity")

    categories = (
        "unprotected_style_payloads",
        "unprotected_name_candidates",
        "unprotected_foreign_lexicon_hits",
        "visible_one_letter_tokens",
    )
    rows: list[dict[str, Any]] = []
    for category in categories:
        category_rows = value.get(category)
        require(isinstance(category_rows, list), f"missing manifest category: {category}")
        for index, row in enumerate(category_rows):
            if row.get("review_correction") is not None:
                require(
                    row["review_correction"].get("category_index0") == index,
                    f"review correction index drift: {category}:{index}",
                )
                rows.append({"category": category, "category_index0": index, **row})
    additions = value.get("additional_protected_spans")
    require(isinstance(additions, list), "missing additional protected spans")
    rows.extend(
        {"category": "additional_protected_spans", "category_index0": index, **row}
        for index, row in enumerate(additions)
    )
    require(len(rows) == 372, f"reviewed-effect census drift: {len(rows)}")

    allowed = {filename: set() for filename in SOURCE_ORDER}
    modes: Counter[str] = Counter()
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        filename = row.get("file")
        require(filename in allowed, f"effect names unknown source: {filename}")
        line = row.get("line")
        require(isinstance(line, int) and line > 0, f"invalid effect line: {filename}:{line}")
        span = row.get("scalar_span")
        require(
            isinstance(span, list)
            and len(span) == 2
            and all(isinstance(item, int) for item in span)
            and 0 <= span[0] < span[1],
            f"invalid effect span: {filename}:{span}",
        )
        key = (row["category"], row["category_index0"], filename, *span)
        require(key not in seen, f"duplicate effect row: {key}")
        seen.add(key)
        allowed[filename].add(line)
        disposition = row.get("disposition", "")
        modes["preserve" if disposition.startswith(("PROTECT", "PRESERVE")) else "project"] += 1
    require(dict(sorted(modes.items())) == {"preserve": 346, "project": 26}, f"effect-mode drift: {modes}")
    require(
        {filename: len(lines) for filename, lines in allowed.items()} == EXPECTED_ALLOWED_CHANGED_LINES,
        "licensed-line census drift",
    )
    return value, allowed, dict(sorted(modes.items()))


def expected_output_manifest() -> list[dict[str, Any]]:
    return [
        {
            "file": OUTPUT_NAMES[filename],
            "bytes": OUTPUT_PINS[filename][0],
            "sha256": OUTPUT_PINS[filename][1],
        }
        for filename in SOURCE_ORDER
    ]


def independent_delta_audit(
    projected: Mapping[str, bytes], allowed: Mapping[str, set[int]]
) -> dict[str, Any]:
    changed_rows: list[dict[str, Any]] = []
    by_file: dict[str, int] = {}
    for filename in SOURCE_ORDER:
        output_name = OUTPUT_NAMES[filename]
        old_raw = read_pin(
            OLD_OUTPUT_DIR / output_name,
            OLD_OUTPUT_PINS[output_name],
            f"frozen v019 output {output_name}",
        )
        new_raw = projected[filename]
        old_lines = old_raw.splitlines(keepends=True)
        new_lines = new_raw.splitlines(keepends=True)
        require(len(old_lines) == len(new_lines), f"line topology drift: {filename}")
        count = 0
        for line_number, (old_line, new_line) in enumerate(zip(old_lines, new_lines), 1):
            if old_line == new_line:
                continue
            require(line_number in allowed[filename], f"unlicensed changed line: {filename}:{line_number}")
            count += 1
            changed_rows.append(
                {
                    "file": filename,
                    "line": line_number,
                    "old_line": describe(old_line),
                    "new_line": describe(new_line),
                }
            )
        by_file[filename] = count
    require(by_file == EXPECTED_ACTUAL_CHANGED_LINES, f"changed-line census drift: {by_file}")
    inventory = describe(canonical_json(changed_rows))
    require(
        (inventory["bytes"], inventory["sha256"]) == DELTA_INVENTORY_PIN,
        "changed-line inventory pin drift",
    )
    return {
        "actual_changed_lines": len(changed_rows),
        "allowed_changed_lines": sum(len(lines) for lines in allowed.values()),
        "by_file": by_file,
        "inventory": inventory,
        "unlicensed_changed_lines": 0,
    }


def expect_rejection(
    module: Any,
    case: str,
    expected_fragment: str,
    operation: Callable[[], Any],
) -> dict[str, str]:
    try:
        operation()
    except Exception as error:
        require(
            isinstance(error, module.ProjectionV7Error),
            f"{case} raised wrong exception: {type(error).__name__}",
        )
        require(expected_fragment in str(error), f"{case} wrong rejection: {error}")
        return {
            "case": case,
            "error_type": type(error).__name__,
            "matched": expected_fragment,
            "status": "REJECTED_FAIL_CLOSED",
        }
    raise HarnessError(f"hostile case was accepted: {case}")


def assert_report(report: Mapping[str, Any], full_raw: bytes, compact_raw: bytes) -> None:
    require((len(full_raw), sha256(full_raw)) == FULL_REPORT_PIN, "full report pin drift")
    require((len(compact_raw), sha256(compact_raw)) == COMPACT_REPORT_PIN, "compact report pin drift")
    require(report.get("report_sha256_excluding_this_field") == REPORT_INTERNAL, "report internal claim drift")
    without = copy.deepcopy(report)
    without.pop("report_sha256_excluding_this_field", None)
    require(sha256(canonical_json(without)) == REPORT_INTERNAL, "report internal digest mismatch")
    require(report.get("output_manifest") == expected_output_manifest(), "output manifest drift")
    require(report.get("output_manifest_sha256") == OUTPUT_MANIFEST_SHA256, "output-manifest digest drift")

    effects = report.get("review_effect_audit", {})
    require(effects.get("status") == "PASS_ALL_REVIEWED_CORRECTIONS_CONSUMED", "effect audit status drift")
    require(effects.get("effects_verified") == 372, "effect count drift")
    require(effects.get("classification_corrections") == 364, "classification-effect count drift")
    require(effects.get("coverage_spans") == 8, "coverage-effect count drift")
    require(effects.get("by_mode") == {"preserve": 346, "project": 26}, "effect-mode report drift")
    require(effects.get("unverified_corrections") == 0, "unverified effects remain")
    require(effects.get("projectable_corrections_swallowed_by_protection") == 0, "project effect swallowed")
    effect_inventory = effects.get("effect_inventory", {})
    require(
        (effect_inventory.get("bytes"), effect_inventory.get("sha256")) == EFFECT_INVENTORY_PIN,
        "effect inventory pin drift",
    )

    delta = report.get("predecessor_delta_audit", {})
    require(delta.get("status") == "PASS_ALL_CHANGES_WITHIN_REVIEWED_LOCATORS", "delta audit status drift")
    require(delta.get("actual_changed_lines") == 125, "actual changed-line count drift")
    require(delta.get("allowed_changed_lines") == 309, "allowed changed-line count drift")
    require(delta.get("unlicensed_changed_lines") == 0, "unlicensed changes reported")
    delta_inventory = delta.get("changed_line_inventory", {})
    require(
        (delta_inventory.get("bytes"), delta_inventory.get("sha256")) == DELTA_INVENTORY_PIN,
        "delta inventory pin drift",
    )

    dimension = report.get("tex_dimension_policy", {})
    require(dimension.get("occurrences") == 447, "v6 dimension occurrence drift")
    require(dimension.get("by_surface") == {"em": 219, "pt": 228}, "v6 visible-dimension census drift")
    require(dimension.get("source_census") == EXPECTED_DIMENSION_CENSUS, "v6 source dimension census drift")
    require(dimension.get("output_census") == EXPECTED_DIMENSION_CENSUS, "v6 output dimension census drift")
    require(dimension.get("cyrillic_dimension_residuals") == 0, "Cyrillic TeX dimension residual")
    dimension_inventory = dimension.get("inventory", {})
    require(
        (dimension_inventory.get("bytes"), dimension_inventory.get("sha256")) == DIMENSION_INVENTORY_PIN,
        "v6 dimension inventory pin drift",
    )
    require(effects.get("tex_dimension_occurrences") == 447, "effect audit dimension count drift")


def main() -> int:
    before_watch = watched_snapshot()
    before_watch_digest = describe(canonical_json(before_watch))
    before_sources = source_raws()
    manifest, allowed_lines, independent_modes = independent_manifest_review()

    first = load_v7("isv020_v7_hostile_run_a")
    report_a, outputs_a = first.project_corpus()
    full_a = canonical_json(report_a)
    compact_a = canonical_json(first.compact(report_a))
    assert_report(report_a, full_a, compact_a)

    second = load_v7("isv020_v7_hostile_run_b")
    report_b, outputs_b = second.project_corpus()
    full_b = canonical_json(report_b)
    compact_b = canonical_json(second.compact(report_b))
    assert_report(report_b, full_b, compact_b)
    require(full_a == full_b, "independent full reports are not byte-identical")
    require(compact_a == compact_b, "independent compact reports are not byte-identical")
    require(set(outputs_a) == set(SOURCE_ORDER), "first output topology drift")
    require(set(outputs_b) == set(SOURCE_ORDER), "second output topology drift")
    for filename in SOURCE_ORDER:
        require(outputs_a[filename] == outputs_b[filename], f"independent output drift: {filename}")
        require(
            (len(outputs_a[filename]), sha256(outputs_a[filename])) == OUTPUT_PINS[filename],
            f"output pin drift: {filename}",
        )

    independent_delta = independent_delta_audit(outputs_a, allowed_lines)
    require(
        independent_delta["inventory"] == report_a["predecessor_delta_audit"]["changed_line_inventory"],
        "independent delta inventory disagrees with report",
    )
    require(independent_modes == report_a["review_effect_audit"]["by_mode"], "independent effect modes disagree")

    hostile: list[dict[str, str]] = []
    mutated = dict(before_sources)
    target = SOURCE_ORDER[0]
    changed = bytearray(mutated[target])
    changed[0] ^= 1
    mutated[target] = bytes(changed)
    hostile.append(
        expect_rejection(
            first,
            "source_payload_mutation",
            f"source pin drift: {target}",
            lambda: first.project_raws(mutated),
        )
    )
    omitted = {name: before_sources[name] for name in SOURCE_ORDER[:-1]}
    hostile.append(
        expect_rejection(
            first,
            "source_topology_omission",
            "source topology drift",
            lambda: first.project_raws(omitted),
        )
    )
    hostile.append(
        expect_rejection(
            first,
            "unsafe_output_target",
            "output directory must be exact v020 source_cyrillic",
            lambda: first.install_outputs(ROOT, outputs_a),
        )
    )

    original_manifest_pin = first.MANIFEST_PIN
    try:
        first.MANIFEST_PIN = (original_manifest_pin[0], "0" * 64)
        hostile.append(
            expect_rejection(
                first,
                "manifest_pin_tamper",
                "pin drift: v020 reviewed role manifest",
                first.validate_manifest,
            )
        )
    finally:
        first.MANIFEST_PIN = original_manifest_pin

    validated_manifest, _manifest_raw, corrected = first.validate_manifest()
    old_name = OUTPUT_NAMES[SOURCE_ORDER[0]]
    original_old_pin = first.OLD_OUTPUT_PINS[old_name]
    try:
        first.OLD_OUTPUT_PINS[old_name] = (original_old_pin[0], "0" * 64)
        hostile.append(
            expect_rejection(
                first,
                "old_output_pin_tamper",
                f"pin drift: frozen v019 output {old_name}",
                lambda: first.delta_audit(validated_manifest, corrected, outputs_a),
            )
        )
    finally:
        first.OLD_OUTPUT_PINS[old_name] = original_old_pin

    after_sources = source_raws()
    require(before_sources == after_sources, "Latin sources changed during read-only test")
    after_watch = watched_snapshot()
    after_watch_digest = describe(canonical_json(after_watch))
    require(before_watch == after_watch, "watched workspace state changed during read-only test")

    receipt = {
        "schema": "noether-isv-cyrillic-projection-v7-hostile-regression-receipt-v1",
        "status": "PASS_READ_ONLY_HOSTILE_REGRESSION",
        "test": {"path": Path(__file__).name, **describe(Path(__file__).read_bytes())},
        "projector": {"path": PROJECTOR_PATH.name, **describe(PROJECTOR_PATH.read_bytes())},
        "independent_in_memory_runs": {
            "runs": 2,
            "byte_identical_full_reports": True,
            "byte_identical_compact_reports": True,
            "byte_identical_outputs": len(SOURCE_ORDER),
            "full_report": describe(full_a),
            "compact_report": describe(compact_a),
            "report_internal_sha256": REPORT_INTERNAL,
        },
        "latin_source_immutability": {
            "files": [
                {"file": filename, **describe(before_sources[filename])}
                for filename in SOURCE_ORDER
            ],
            "before_after_byte_identical": len(SOURCE_ORDER),
            "bytes_changed": 0,
        },
        "outputs": expected_output_manifest(),
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA256,
        "review_effects": {
            "effects_verified": 372,
            "by_mode": independent_modes,
            "effect_inventory": {
                "bytes": EFFECT_INVENTORY_PIN[0],
                "sha256": EFFECT_INVENTORY_PIN[1],
            },
            "unverified": 0,
        },
        "licensed_delta": independent_delta,
        "v6_dimension_census": {
            "occurrences": 447,
            "by_surface": {"em": 219, "pt": 228},
            "source_and_output_census": EXPECTED_DIMENSION_CENSUS,
            "inventory": {
                "bytes": DIMENSION_INVENTORY_PIN[0],
                "sha256": DIMENSION_INVENTORY_PIN[1],
            },
            "cyrillic_dimension_residuals": 0,
        },
        "hostile_rejections": hostile,
        "workspace_immutability": {
            "watched_paths": len(before_watch),
            "before": before_watch_digest,
            "after": after_watch_digest,
            "changed_paths": 0,
        },
        "canonical_files_written": 0,
    }
    sys.stdout.buffer.write(canonical_json(receipt))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema": "noether-isv-cyrillic-projection-v7-hostile-regression-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
