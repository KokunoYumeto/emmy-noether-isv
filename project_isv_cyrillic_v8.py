#!/usr/bin/env python3
"""Fail-closed deterministic v021 Latin-to-Cyrillic projector.

The frozen v020/v7 engine and its fully reviewed role policy remain the
projection authority.  v8 consumes the one-to-one rebased v021 manifest,
unions the exact accepted 722-site Roman-numeral identity inventory, verifies
every inherited correction and every Roman output effect, and licenses output
changes only where the frozen Latin predecessor-to-successor alignment changed.
Default execution is read-only.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence


sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
V020_ROOT = ROOT.parent / "noether_isv_v020_working"
V7_PATH = V020_ROOT / "project_isv_cyrillic_v7.py"
MANIFEST_PATH = ROOT / "decision_records" / "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json"
FREEZE_RECEIPT_PATH = ROOT / "decision_records" / "ISV021-LATIN-FREEZE-PROJECTION-FRONTIER-R2.json"
FREEZE_DECISION_PATH = ROOT / "decision_records" / "ISV021-LATIN-FREEZE-DECISION.json"
SOURCE_DIR = ROOT / "source_latin"
OUTPUT_DIR = ROOT / "source_cyrillic"
V020_SOURCE_DIR = V020_ROOT / "source_latin"
V020_OUTPUT_DIR = V020_ROOT / "source_cyrillic"

V7_PIN = (
    27_666,
    "51E467EDD8F0B8F44F62D60C4F5D35EAB5BA80EEFA1B0BFCBC1A2EF0B3538915",
)
MANIFEST_PIN = (
    4_177_431,
    "BE0A9902DAC546350227C048777A78AC300647D5FB514895F7CB91EC3D900970",
)
MANIFEST_INTERNAL = "D3D2732B162B1033FED1F9AA4932540112085206AA257D4B19BEB26CCA8F1BC8"
FREEZE_RECEIPT_PIN = (
    360_147,
    "C0584834AF4A2638E763BCEEEA92D0A5C43F40380BC97B36A98BC4D25D6B686B",
)
FREEZE_DECISION_PIN = (
    4_283,
    "FB8606FA1001FC5BB226DC70877B99ABA443C9263064167DA9C6AE7399223340",
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
SOURCE_PINS = {
    "44-book-isv.tex": (
        168_384,
        "FFEAE898972515A69D9BCD4930ECEEF2C91DD7114E0CA0B0F64E2157ED32E698",
    ),
    "45-isv.tex": (
        26_036,
        "E49033F3C3004F921CD234610425905FF1D46405107D8EB99BC431864BB4473D",
    ),
    "base-papers1-43-isv.tex": (
        1_893_083,
        "237FFE1460816EAF8CCD6E00F9500F816A285830CE62E28E49CECB94685B16E9",
    ),
    "bib-isv.tex": (
        10_016,
        "D14F600C71E911F49F0A81B85B2C476F7BED490D597E2045AC55744774D201B1",
    ),
}
V020_SOURCE_PINS = {
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
V020_OUTPUT_PINS = {
    "44-book-isv-cyrl.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "45-isv-cyrl.tex": (
        35_895,
        "F94F731110DA94B30B9243C67587CB6A1B6E6478A046F08C617271A0B188CCFB",
    ),
    "base-papers1-43-isv-cyrl.tex": (
        2_706_558,
        "8BB578C1B2D7B48E52A425D40039FE5A6B79FF1ED26E825A6BDA7EE736341277",
    ),
    "bib-isv-cyrl.tex": (
        13_206,
        "4E74B8EA52C9B37209345B7E9A0B6BD7330D8EA0570E6D0C164FEA113511613D",
    ),
}
CATEGORIES = (
    "unprotected_style_payloads",
    "unprotected_name_candidates",
    "unprotected_foreign_lexicon_hits",
    "visible_one_letter_tokens",
)
CATEGORY_COUNTS = {
    "unprotected_style_payloads": 883,
    "unprotected_name_candidates": 616,
    "unprotected_foreign_lexicon_hits": 2_371,
    "visible_one_letter_tokens": 690,
}
EXPECTED_DISPOSITIONS = {
    "unprotected_style_payloads": {
        "KEEP_PROJECTABLE_INTERSLAVIC_STYLE_PAYLOAD": 730,
        "PROTECT_COMPLETE_ORIGINAL_LANGUAGE_STYLE_PAYLOAD": 153,
    },
    "unprotected_name_candidates": {
        "KEEP_PROJECTABLE_INTEGRATED_OR_NONNAME_CANDIDATE": 374,
        "PROTECT_COMPLETE_UNINFLECTED_IDENTITY": 242,
    },
    "unprotected_foreign_lexicon_hits": {
        "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT": 1_126,
        "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN": 1_245,
    },
    "visible_one_letter_tokens": {
        "PRESERVE_COVERED_BY_ALLOWED_LETTER_FOREIGN_RANGE": 19,
        "PRESERVE_DOTTED_INITIAL_OR_ROMAN_ORDINAL": 32,
        "PRESERVE_FOREIGN_INITIAL_OR_CITATION_ABBREVIATION": 32,
        "PRESERVE_STRUCTURAL_ROMAN_LABEL": 249,
        "PROJECT_LEXICAL_INTERSLAVIC_WORD": 358,
    },
}
EXPECTED_ROMAN_FORMS = {
    "ii": 215,
    "iii": 165,
    "iv": 103,
    "vi": 40,
    "vii": 44,
    "viii": 39,
    "ix": 19,
    "x": 18,
    "xi": 20,
    "xii": 11,
    "xiii": 10,
    "xiv": 12,
    "xv": 7,
    "xvi": 6,
    "xvii": 9,
    "xix": 3,
    "xxii": 1,
}


class ProjectionV8Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProjectionV8Error(message)


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


def strict_json(raw: bytes, label: str) -> Any:
    require(raw.endswith(b"\n") and b"\r" not in raw, f"transport drift: {label}")
    require(not raw.startswith(b"\xef\xbb\xbf"), f"BOM not allowed: {label}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)


def read_exact(path: Path, pin: tuple[int, str], label: str) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe {label}: {path}")
    raw = path.read_bytes()
    require((len(raw), sha256(raw)) == pin, f"pin drift: {label}: {describe(raw)}")
    return raw


def load_v7() -> Any:
    read_exact(V7_PATH, V7_PIN, "frozen v020/v7 projector")
    spec = importlib.util.spec_from_file_location("isv021_frozen_v020_v7", V7_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v7")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_raws(directory: Path, pins: Mapping[str, tuple[int, str]]) -> dict[str, bytes]:
    return {
        name: read_exact(directory / name, pins[name], f"{directory.name}/{name}")
        for name in SOURCE_ORDER
    }


def validate_manifest() -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    raw = read_exact(MANIFEST_PATH, MANIFEST_PIN, "v021 rebased role manifest")
    value = strict_json(raw, str(MANIFEST_PATH))
    require(value.get("schema") == "noether-isv-reviewed-projection-role-manifest/3.0", "manifest schema drift")
    require(value.get("status") == "REBASED_FULLY_REVIEWED_ZERO_AMBIGUITY_BINDING_V021_GATE", "manifest status drift")
    claimed = value.get("inventory_sha256_excluding_this_field")
    without = copy.deepcopy(value)
    without.pop("inventory_sha256_excluding_this_field", None)
    require(claimed == MANIFEST_INTERNAL, "manifest embedded digest drift")
    require(sha256(canonical_json(without)) == MANIFEST_INTERNAL, "manifest internal digest mismatch")
    scope = value.get("scope", {})
    require(scope.get("successor_release") == "NOETHER-ISV-v021", "manifest successor drift")
    require(scope.get("latin_editorial_head") == "ISV021-EDIT-0012", "manifest Latin head drift")
    require(scope.get("latin_freeze_decision") == "ISV021-LATIN-FREEZE", "manifest freeze drift")
    require(tuple(scope.get("source_order", ())) == SOURCE_ORDER, "manifest source order drift")

    corrected: list[dict[str, Any]] = []
    seen_rows: set[tuple[Any, ...]] = set()
    for category in CATEGORIES:
        rows = value.get(category)
        require(isinstance(rows, list) and len(rows) == CATEGORY_COUNTS[category], f"category count drift: {category}")
        observed = dict(sorted(Counter(row.get("disposition") for row in rows).items()))
        require(observed == EXPECTED_DISPOSITIONS[category], f"category disposition drift: {category}")
        for index, row in enumerate(rows):
            key = (category, index, row.get("file"), *row.get("scalar_span", []))
            require(key not in seen_rows, f"duplicate inherited row: {key}")
            seen_rows.add(key)
            correction = row.get("review_correction")
            if correction is not None:
                require(correction.get("category_index0") == index, f"correction ordinal drift: {category}:{index}")
                corrected.append({"category": category, "category_index0": index, **row})
    require(len(corrected) == 364, "classification correction census drift")
    additions = value.get("additional_protected_spans")
    require(isinstance(additions, list) and len(additions) == 8, "additional-span census drift")
    romans = value.get("v021_roman_identity_spans")
    require(isinstance(romans, list) and len(romans) == 722, "Roman policy census drift")
    roman_counts = Counter(row.get("token_casefold") for row in romans)
    require(dict(sorted(roman_counts.items())) == EXPECTED_ROMAN_FORMS, f"Roman form drift: {roman_counts}")
    roman_keys = {(row["file"], *row["scalar_span"]) for row in romans}
    require(len(roman_keys) == 722, "duplicate Roman spans")
    require(all(row.get("surface", "").isupper() for row in romans), "non-uppercase Roman surface")
    return value, raw, corrected


def authenticate_v020_predecessor(v7: Any) -> dict[str, Any]:
    frozen_sources = source_raws(V020_SOURCE_DIR, V020_SOURCE_PINS)
    frozen_outputs = {
        source: read_exact(
            V020_OUTPUT_DIR / OUTPUT_NAMES[source],
            V020_OUTPUT_PINS[OUTPUT_NAMES[source]],
            f"v020 output {OUTPUT_NAMES[source]}",
        )
        for source in SOURCE_ORDER
    }
    report, recomputed = v7.project_corpus()
    require(recomputed == frozen_outputs, "frozen v7 does not reproduce v020 output vector")
    require(
        {name: (len(frozen_sources[name]), sha256(frozen_sources[name])) for name in SOURCE_ORDER}
        == V020_SOURCE_PINS,
        "v020 source vector drift",
    )
    return {
        "status": "PASS_FROZEN_V7_REPRODUCES_V020",
        "projector": {"path": str(V7_PATH), "bytes": V7_PIN[0], "sha256": V7_PIN[1]},
        "report_sha256_excluding_this_field": report["report_sha256_excluding_this_field"],
        "source_pins": {name: describe(frozen_sources[name]) for name in SOURCE_ORDER},
        "output_pins": {OUTPUT_NAMES[name]: describe(frozen_outputs[name]) for name in SOURCE_ORDER},
    }


def ranges_cover(ranges: Sequence[tuple[int, int, str]], start: int, end: int) -> bool:
    return any(left <= start and end <= right for left, right, _reason in ranges)


def patched_v5_factory(v7: Any) -> Callable[..., Any]:
    inherited_factory = v7.patched_v5

    def patched_v5(v6: Any, manifest: dict[str, Any]):
        v5, inherited_selector = inherited_factory(v6, manifest)
        v5.ROOT = ROOT
        v5.SOURCE_DIR = SOURCE_DIR
        v5.SOURCE_PINS = SOURCE_PINS
        v5.MANIFEST_PATH = MANIFEST_PATH
        v5.MANIFEST_PIN = MANIFEST_PIN
        v5.MANIFEST_INTERNAL = MANIFEST_INTERNAL

        def structural_ranges(
            _v4: Any,
            v2: Any,
            _raws: Mapping[str, bytes],
            texts: Mapping[str, str],
        ) -> tuple[dict[str, list[tuple[int, int, str]]], dict[str, Any]]:
            result: dict[str, list[tuple[int, int, str]]] = {
                name: [] for name in SOURCE_ORDER
            }
            scanned_issues: list[dict[str, Any]] = []
            manifest_keys: set[tuple[Any, ...]] = set()
            for row in manifest["v021_roman_identity_spans"]:
                filename = row["file"]
                start, end = v5.validate_row(v2, texts[filename], row, filename)
                result[filename].append(
                    (start, end, "v8:accepted_structural_roman_identity")
                )
                manifest_keys.add((filename, start, end, row["surface"]))
            for filename in SOURCE_ORDER:
                scanned = v2.scan_text(texts[filename], filename)
                require(
                    scanned["coverage"]["status"] == "PASS",
                    f"v2 coverage failure: {filename}",
                )
                require(
                    not scanned["unknown_argument_commands"],
                    f"unknown argument command: {filename}",
                )
                scanned_issues.extend(scanned["issues"])
            scanned_keys = {
                (
                    issue["file"],
                    issue["scalar_offset"],
                    issue["scalar_offset"] + len(issue["token"]),
                    issue["token"],
                )
                for issue in scanned_issues
            }
            require(len(scanned_issues) == 722, "live structural scanner census drift")
            require(scanned_keys == manifest_keys, "live structural scanner/manifest mismatch")
            require(
                v2.issue_inventory_sha256(scanned_issues)
                == "B4791B7F5B769381C258C7EE1AFDE631F04808AC4047AD501E58F2E0E6D22D49",
                "live structural scanner inventory drift",
            )
            return result, {
                "head_validation": {
                    "status": "PASS_ISV021_LATIN_FREEZE",
                    "decision": "ISV021-LATIN-FREEZE",
                    "sources": {
                        name: {"bytes": SOURCE_PINS[name][0], "sha256": SOURCE_PINS[name][1]}
                        for name in SOURCE_ORDER
                    },
                },
                "approved_occurrences": len(scanned_issues),
                "inventory_sha256": v2.issue_inventory_sha256(scanned_issues),
                "non_roman_occurrences": 0,
                "policy": "exact finite uppercase Roman theorem/section identity inventory",
            }

        v5.structural_ranges = structural_ranges

        def selector(v2: Any, supplied: dict[str, Any], texts: Mapping[str, str]):
            selected, selection = inherited_selector(v2, supplied, texts)
            romans = supplied["v021_roman_identity_spans"]
            already_covered = 0
            newly_covering = 0
            projectable_partial_overlaps = 0
            projectable_fully_swallowed = 0
            projectable_rows = {
                filename: [
                    row
                    for category in CATEGORIES
                    for row in supplied[category]
                    if row["file"] == filename
                    and not str(row["disposition"]).startswith(("PROTECT", "PRESERVE"))
                ]
                for filename in SOURCE_ORDER
            }
            projectable_corrections = {
                filename: [row for row in projectable_rows[filename] if row.get("review_correction") is not None]
                for filename in SOURCE_ORDER
            }
            correction_overlaps = 0
            before_union: dict[str, int] = {}
            after_union: dict[str, int] = {}
            for filename in SOURCE_ORDER:
                merged_before, _ = v5.union_ranges(texts[filename], selected[filename], filename)
                before_union[filename] = len(merged_before)
            for row in romans:
                filename = row["file"]
                start, end = v5.validate_row(v2, texts[filename], row, filename)
                if ranges_cover(selected[filename], start, end):
                    already_covered += 1
                else:
                    newly_covering += 1
                for candidate in projectable_rows[filename]:
                    left, right = candidate["scalar_span"]
                    if max(left, start) < min(right, end):
                        projectable_partial_overlaps += 1
                        if start <= left and right <= end:
                            projectable_fully_swallowed += 1
                for candidate in projectable_corrections[filename]:
                    left, right = candidate["scalar_span"]
                    if max(left, start) < min(right, end):
                        correction_overlaps += 1
                selected[filename].append((start, end, "manifest:v021_roman_identity_exact_token"))
            require(projectable_fully_swallowed == 0, "Roman policy fully swallows a projectable row")
            require(correction_overlaps == 0, "Roman policy overlaps a corrected projectable row")
            for filename in SOURCE_ORDER:
                merged_after, _ = v5.union_ranges(texts[filename], selected[filename], filename)
                after_union[filename] = len(merged_after)
            result = copy.deepcopy(selection)
            result["selected_occurrences_before_union"] += len(romans)
            result["v021_roman_identity"] = {
                "policy_sites": len(romans),
                "already_covered_by_inherited_ranges": already_covered,
                "newly_covering_exact_tokens": newly_covering,
                "projectable_partial_token_overlaps": projectable_partial_overlaps,
                "projectable_rows_fully_swallowed": projectable_fully_swallowed,
                "corrected_projectable_row_overlaps": correction_overlaps,
                "manifest_union_intervals_before": before_union,
                "manifest_union_intervals_after": after_union,
            }
            return selected, result

        v5.selected_manifest_ranges = selector
        return v5, selector

    return patched_v5


def v021_delta_audit(
    _manifest: Mapping[str, Any],
    _corrected: Sequence[Mapping[str, Any]],
    projected: Mapping[str, bytes],
) -> dict[str, Any]:
    old_sources = source_raws(V020_SOURCE_DIR, V020_SOURCE_PINS)
    new_sources = source_raws(SOURCE_DIR, SOURCE_PINS)
    rows: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    total_equal_blocks = 0
    total_changed_blocks = 0
    for filename in SOURCE_ORDER:
        old_output = read_exact(
            V020_OUTPUT_DIR / OUTPUT_NAMES[filename],
            V020_OUTPUT_PINS[OUTPUT_NAMES[filename]],
            f"v020 output {OUTPUT_NAMES[filename]}",
        )
        new_output = projected[filename]
        old_source_lines = old_sources[filename].splitlines(keepends=True)
        new_source_lines = new_sources[filename].splitlines(keepends=True)
        old_output_lines = old_output.splitlines(keepends=True)
        new_output_lines = new_output.splitlines(keepends=True)
        require(len(old_source_lines) == len(old_output_lines), f"v020 source/output line topology drift: {filename}")
        require(len(new_source_lines) == len(new_output_lines), f"v021 source/output line topology drift: {filename}")
        matcher = difflib.SequenceMatcher(None, old_source_lines, new_source_lines, autojunk=False)
        equal_blocks = 0
        changed_blocks = 0
        changed_old_lines = 0
        changed_new_lines = 0
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            old_chunk = b"".join(old_output_lines[old_start:old_end])
            new_chunk = b"".join(new_output_lines[new_start:new_end])
            if tag == "equal":
                require(old_chunk == new_chunk, f"unlicensed output change on unchanged Latin block: {filename}:{old_start + 1}")
                equal_blocks += 1
                continue
            changed_blocks += 1
            changed_old_lines += old_end - old_start
            changed_new_lines += new_end - new_start
            rows.append(
                {
                    "file": filename,
                    "tag": tag,
                    "old_source_lines": [old_start + 1, old_end],
                    "new_source_lines": [new_start + 1, new_end],
                    "old_source": describe(b"".join(old_source_lines[old_start:old_end])),
                    "new_source": describe(b"".join(new_source_lines[new_start:new_end])),
                    "old_output": describe(old_chunk),
                    "new_output": describe(new_chunk),
                }
            )
        total_equal_blocks += equal_blocks
        total_changed_blocks += changed_blocks
        files.append(
            {
                "source": filename,
                "output": OUTPUT_NAMES[filename],
                "v020": describe(old_output),
                "v021": describe(new_output),
                "size_delta": len(new_output) - len(old_output),
                "old_lines": len(old_output_lines),
                "new_lines": len(new_output_lines),
                "unchanged_input_blocks_with_identical_output": equal_blocks,
                "changed_input_blocks_licensing_output": changed_blocks,
                "changed_old_input_lines": changed_old_lines,
                "changed_new_input_lines": changed_new_lines,
            }
        )
    return {
        "status": "PASS_ALL_OUTPUT_CHANGES_LICENSED_BY_LATIN_ALIGNMENT",
        "unchanged_input_blocks_with_identical_output": total_equal_blocks,
        "changed_input_blocks": total_changed_blocks,
        "unlicensed_output_changes": 0,
        "changed_block_inventory": describe(canonical_json(rows)),
        "files": files,
    }


def roman_effect_audit(
    v7: Any,
    manifest: Mapping[str, Any],
    raws: Mapping[str, bytes],
    projected: Mapping[str, bytes],
) -> dict[str, Any]:
    v6 = v7.load_v6()
    v5, selector = v7.patched_v5(v6, dict(manifest))
    v6.load_v5 = lambda: v5
    v4 = v5.load_v4()
    v2 = v4.load_v2()
    texts = {filename: v2.strict_transport(raws[filename], filename) for filename in SOURCE_ORDER}
    selected, selection = selector(v2, dict(manifest), texts)
    dimensions, _dimension_evidence = v6.dimension_inventory(v5, v2, texts)
    structural, _structural_evidence = v5.structural_ranges(v4, v2, raws, texts)
    protected_maps: dict[str, list[dict[str, int]]] = {}
    for filename in SOURCE_ORDER:
        selected[filename].extend(dimensions[filename])
        merged, _ = v5.union_ranges(texts[filename], selected[filename] + structural[filename], filename)
        segments = v5.split_segments(v2, texts[filename], merged)
        output_text = projected[filename].decode("utf-8")
        output_cursor = 0
        rebuilt: list[str] = []
        protected_maps[filename] = []
        for segment in segments:
            raw = texts[filename][segment.start : segment.end]
            if segment.role in v5.VISIBLE_ROLES:
                chunk = v7.project_visible(v2, raw, filename)
            else:
                chunk = raw
                protected_maps[filename].append(
                    {
                        "input_start": segment.start,
                        "input_end": segment.end,
                        "output_start": output_cursor,
                        "output_end": output_cursor + len(chunk),
                    }
                )
            rebuilt.append(chunk)
            output_cursor += len(chunk)
        require("".join(rebuilt) == output_text, f"Roman effect reconstruction drift: {filename}")

    effect_rows: list[dict[str, Any]] = []
    for row in manifest["v021_roman_identity_spans"]:
        filename = row["file"]
        start, end = row["scalar_span"]
        covering = [
            span
            for span in protected_maps[filename]
            if span["input_start"] <= start and end <= span["input_end"]
        ]
        require(len(covering) == 1, f"Roman span not uniquely protected: {filename}:{start}:{end}")
        span = covering[0]
        output_start = span["output_start"] + start - span["input_start"]
        output_end = output_start + end - start
        observed = projected[filename].decode("utf-8")[output_start:output_end]
        require(observed == row["surface"], f"Roman output drift: {filename}:{row['line']}:{row['surface']}")
        effect_rows.append(
            {
                "file": filename,
                "line": row["line"],
                "column": row["column"],
                "surface": row["surface"],
                "observed_sha256": sha256(observed.encode("utf-8")),
            }
        )
    policy = selection["v021_roman_identity"]
    require(policy["policy_sites"] == 722, "Roman selector census drift")
    require(policy["already_covered_by_inherited_ranges"] + policy["newly_covering_exact_tokens"] == 722, "Roman coverage partition drift")
    return {
        "status": "PASS_ALL_722_ROMAN_SITES_BYTE_IDENTICAL",
        **policy,
        "by_form": dict(sorted(Counter(row["surface"] for row in effect_rows).items())),
        "effect_inventory": describe(canonical_json(effect_rows)),
        "unverified_sites": 0,
    }


def prepare_v7(v7: Any) -> None:
    v7.SOURCE_DIR = SOURCE_DIR
    v7.OUTPUT_DIR = OUTPUT_DIR
    v7.SOURCE_PINS = SOURCE_PINS
    v7.MANIFEST_PATH = MANIFEST_PATH
    v7.MANIFEST_PIN = MANIFEST_PIN
    v7.MANIFEST_INTERNAL = MANIFEST_INTERNAL
    v7.validate_manifest = validate_manifest
    v7.patched_v5 = patched_v5_factory(v7)
    v7.delta_audit = v021_delta_audit


def project_corpus() -> tuple[dict[str, Any], dict[str, bytes]]:
    freeze_receipt_raw = read_exact(
        FREEZE_RECEIPT_PATH,
        FREEZE_RECEIPT_PIN,
        "sealed v021 Latin freeze frontier receipt",
    )
    freeze_receipt = strict_json(freeze_receipt_raw, str(FREEZE_RECEIPT_PATH))
    require(
        isinstance(freeze_receipt, dict)
        and freeze_receipt.get("schema") == "noether-isv-v021-sealed-latin-cyrillic-frontier-audit-v3"
        and freeze_receipt.get("status") == "PASS_LIVE_SEALED_LATIN_ZERO_NON_ROMAN_PROJECTION_BLOCKS",
        "Latin freeze frontier receipt semantic gate failed",
    )
    freeze_decision_raw = read_exact(
        FREEZE_DECISION_PATH,
        FREEZE_DECISION_PIN,
        "sealed v021 Latin freeze decision",
    )
    freeze_decision = strict_json(freeze_decision_raw, str(FREEZE_DECISION_PATH))
    require(
        isinstance(freeze_decision, dict)
        and freeze_decision.get("schema") == "noether-isv-v021-latin-freeze-decision-v1"
        and freeze_decision.get("status") == "ACCEPT_LATIN_FREEZE_ZERO_NON_ROMAN_PROJECTION_BLOCKS",
        "Latin freeze decision semantic gate failed",
    )
    v7 = load_v7()
    predecessor = authenticate_v020_predecessor(v7)
    prepare_v7(v7)
    raws = source_raws(SOURCE_DIR, SOURCE_PINS)
    manifest, manifest_raw, _corrected = validate_manifest()
    report, projected = v7.project_raws(raws)
    roman = roman_effect_audit(v7, manifest, raws, projected)
    report.pop("report_sha256_excluding_this_field", None)
    report["schema"] = "noether-isv-cyrillic-projection-v8-report-v1"
    report["status"] = "READY_DETERMINISTIC_V021_DERIVATION_IN_MEMORY"
    report["release"] = "NOETHER-ISV-v021"
    report["classification"] = "deterministic Cyrillic representation of the frozen Latin Interslavic canon; not an independent translation witness"
    inherited_dependencies = copy.deepcopy(report["dependencies"])
    require(isinstance(inherited_dependencies, dict), "inherited dependency inventory drift")
    inherited_dependencies.pop("reviewed_role_manifest", None)
    report["dependencies"] = {
        "frozen_v020_v7": {"path": str(V7_PATH), "bytes": V7_PIN[0], "sha256": V7_PIN[1]},
        "rebased_v021_role_manifest": {
            "path": "decision_records/ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json",
            **describe(manifest_raw),
            "internal_sha256": MANIFEST_INTERNAL,
        },
        "Latin_freeze_receipt": {"path": str(FREEZE_RECEIPT_PATH), **describe(freeze_receipt_raw)},
        "Latin_freeze_decision": {"path": str(FREEZE_DECISION_PATH), **describe(freeze_decision_raw)},
        **inherited_dependencies,
    }
    report["predecessor_reproduction"] = predecessor
    report["latin_source_freeze"] = {
        "head": "ISV021-EDIT-0012",
        "decision": "ISV021-LATIN-FREEZE",
        "cumulative_v021_sites_changed": 4_053,
        "total_byte_delta_from_v020": sum(len(raw) for raw in raws.values()) - sum(pin[0] for pin in V020_SOURCE_PINS.values()),
        "files": [{"file": name, **describe(raws[name])} for name in SOURCE_ORDER],
    }
    report["roman_identity_effect_audit"] = roman
    report["limitations"] = [
        "The Cyrillic files are a deterministic representation of the editable Latin canon, not an independent translation witness.",
        "Role decisions are exhaustively source-bound but are not native-speaker, community, official-standard, or external scholarly-peer-review certification.",
        "Complete TeX build, text, math, font, link, render, and visual QA remain separate release gates.",
    ]
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    return report, projected


def install_outputs(output_dir: Path, projected: Mapping[str, bytes]) -> list[dict[str, Any]]:
    require(output_dir.resolve() == OUTPUT_DIR.resolve(), "output directory must be exact v021 source_cyrillic")
    require(output_dir.is_dir() and not output_dir.is_symlink(), "unsafe output directory")
    targets = {name: output_dir / OUTPUT_NAMES[name] for name in SOURCE_ORDER}
    for name, target in targets.items():
        if target.exists():
            require(target.is_file() and not target.is_symlink(), f"unsafe existing output: {target}")
            require(target.read_bytes() == projected[name], f"refusing to overwrite different output: {target}")
    installed: list[Path] = []
    try:
        for ordinal, name in enumerate(SOURCE_ORDER, 1):
            target = targets[name]
            if target.exists():
                continue
            stage = output_dir / f".{target.name}.v8-stage-{os.getpid()}-{ordinal}"
            require(not stage.exists(), f"stage collision: {stage}")
            try:
                with stage.open("xb") as handle:
                    handle.write(projected[name])
                    handle.flush()
                    os.fsync(handle.fileno())
                require(stage.read_bytes() == projected[name], f"stage readback mismatch: {stage}")
                os.replace(stage, target)
                require(target.read_bytes() == projected[name], f"install readback mismatch: {target}")
                installed.append(target)
            finally:
                if stage.exists():
                    stage.unlink()
    except Exception:
        for target in reversed(installed):
            matching = next((projected[name] for name in SOURCE_ORDER if OUTPUT_NAMES[name] == target.name), None)
            if matching is not None and target.is_file() and not target.is_symlink() and target.read_bytes() == matching:
                target.unlink()
        raise
    return [{"path": str(targets[name]), **describe(targets[name].read_bytes())} for name in SOURCE_ORDER]


def exclusive_write(path: Path, raw: bytes) -> None:
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"unsafe receipt parent: {path.parent}")
    require(not path.exists(), f"refusing to overwrite receipt: {path}")
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    require(path.read_bytes() == raw, f"receipt readback mismatch: {path}")


def compact(report: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "schema",
        "status",
        "release",
        "classification",
        "output_manifest",
        "output_manifest_sha256",
        "conversion_classes",
        "projection_issues",
        "tex_dimension_policy",
        "latin_source_freeze",
        "review_effect_audit",
        "roman_identity_effect_audit",
        "predecessor_reproduction",
        "predecessor_delta_audit",
        "report_sha256_excluding_this_field",
    )
    return {key: report[key] for key in keys}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-output-dir", type=Path)
    parser.add_argument("--write-receipt", type=Path)
    parser.add_argument("--full-report", action="store_true")
    args = parser.parse_args(argv)
    require(
        not (args.write_output_dir is not None and args.write_receipt is not None),
        "--write-output-dir and --write-receipt are separate fail-closed transactions",
    )
    report, projected = project_corpus()
    payload: dict[str, Any] = copy.deepcopy(report if args.full_report else compact(report))
    if args.write_output_dir is not None:
        output_dir = args.write_output_dir if args.write_output_dir.is_absolute() else ROOT / args.write_output_dir
        payload["install"] = install_outputs(output_dir, projected)
    rendered = canonical_json(payload)
    if args.write_receipt is not None:
        exclusive_write(args.write_receipt, rendered)
    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema": "noether-isv-cyrillic-projection-v8-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
