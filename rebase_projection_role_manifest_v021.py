#!/usr/bin/env python3
"""Rebase the exhaustively reviewed v020 role policy onto frozen v021 Latin.

The semantic dispositions remain inherited evidence.  Every one of the 4,568
historical source-bound rows is relocated against line-stable v021 bytes, all
protected surfaces must remain unchanged, and the independently accepted 722
Roman-numeral identity sites are added as an explicit v021 policy.  Default
execution is read-only; requested outputs are exclusive-create only.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
V020_ROOT = ROOT.parent / "noether_isv_v020_working"
OLD_SOURCE_DIR = V020_ROOT / "source_latin"
NEW_SOURCE_DIR = ROOT / "source_latin"
OLD_MANIFEST_PATH = (
    V020_ROOT / "decision_records" / "ISV020-REVIEWED-PROJECTION-ROLE-MANIFEST.json"
)
FREEZE_RECEIPT_PATH = (
    ROOT / "decision_records" / "ISV021-LATIN-FREEZE-PROJECTION-FRONTIER-R2.json"
)
FREEZE_DECISION_PATH = ROOT / "decision_records" / "ISV021-LATIN-FREEZE-DECISION.json"
V2_PATH = V020_ROOT / "predecessor_v019" / "project_isv_cyrillic_v2.py"
OUTPUT_MANIFEST_PATH = (
    ROOT / "decision_records" / "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json"
)

OLD_MANIFEST_PIN = (
    3_577_349,
    "192BAE284EDC9BBA4A458EEBA9F7541CE16CA377A68668A70F5CFD0A2E182462",
)
FREEZE_RECEIPT_PIN = (
    360_147,
    "C0584834AF4A2638E763BCEEEA92D0A5C43F40380BC97B36A98BC4D25D6B686B",
)
FREEZE_DECISION_PIN = (
    4_283,
    "FB8606FA1001FC5BB226DC70877B99ABA443C9263064167DA9C6AE7399223340",
)
V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
OLD_SOURCE_PINS = {
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
NEW_SOURCE_PINS = {
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
CATEGORIES = (
    "unprotected_style_payloads",
    "unprotected_name_candidates",
    "unprotected_foreign_lexicon_hits",
    "visible_one_letter_tokens",
)
EXPECTED_CATEGORY_COUNTS = {
    "unprotected_style_payloads": 883,
    "unprotected_name_candidates": 616,
    "unprotected_foreign_lexicon_hits": 2_371,
    "visible_one_letter_tokens": 690,
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


class RebaseError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RebaseError(message)


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


def load_v2() -> Any:
    read_exact(V2_PATH, V2_PIN, "v019 v2 parser/projector")
    spec = importlib.util.spec_from_file_location("isv021_manifest_rebase_v2", V2_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v2")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_sources(directory: Path, pins: Mapping[str, tuple[int, str]]) -> dict[str, bytes]:
    return {
        name: read_exact(directory / name, pins[name], f"{directory.name}/{name}")
        for name in SOURCE_ORDER
    }


def boundary_opcodes(old_line: str, new_line: str) -> list[tuple[str, int, int, int, int]]:
    return difflib.SequenceMatcher(None, old_line, new_line, autojunk=False).get_opcodes()


def map_line_boundary(
    old_line: str,
    new_line: str,
    opcodes: Sequence[tuple[str, int, int, int, int]],
    position: int,
) -> int:
    require(0 <= position <= len(old_line), "line boundary out of range")
    for tag, old_start, old_end, new_start, new_end in opcodes:
        if tag == "equal" and old_start <= position <= old_end:
            return new_start + (position - old_start)
        if position == old_start:
            return new_start
        if position == old_end:
            return new_end
        if old_start < position < old_end:
            if tag == "replace" and old_end - old_start == new_end - new_start:
                return new_start + (position - old_start)
            raise RebaseError(
                f"ambiguous boundary inside {tag} opcode: {position} in "
                f"{old_start}:{old_end}->{new_start}:{new_end}"
            )
    require(position == len(old_line), "unmapped line boundary")
    return len(new_line)


def build_alignment(
    old_text: str,
    new_text: str,
    old_starts: Sequence[int],
    new_starts: Sequence[int],
    old_lines: Sequence[str],
    new_lines: Sequence[str],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, old_i1, old_i2, new_i1, new_i2 in matcher.get_opcodes():
        old_start = old_starts[old_i1] if old_i1 < len(old_starts) else len(old_text)
        old_end = old_starts[old_i2] if old_i2 < len(old_starts) else len(old_text)
        new_start = new_starts[new_i1] if new_i1 < len(new_starts) else len(new_text)
        new_end = new_starts[new_i2] if new_i2 < len(new_starts) else len(new_text)
        old_chunk = old_text[old_start:old_end]
        new_chunk = new_text[new_start:new_end]
        blocks.append(
            {
                "tag": tag,
                "old_start": old_start,
                "old_end": old_end,
                "new_start": new_start,
                "new_end": new_end,
                "old_chunk": old_chunk,
                "new_chunk": new_chunk,
                "char_opcodes": None if tag == "equal" else boundary_opcodes(old_chunk, new_chunk),
            }
        )
    return blocks


def map_global_boundary(
    old_text: str,
    new_text: str,
    alignment: Sequence[Mapping[str, Any]],
    position: int,
) -> int:
    require(0 <= position <= len(old_text), "global boundary out of range")
    if position == len(old_text):
        return len(new_text)
    for block in alignment:
        if block["old_start"] <= position <= block["old_end"]:
            relative = position - block["old_start"]
            if block["tag"] == "equal":
                mapped = relative
            else:
                mapped = map_line_boundary(
                    block["old_chunk"],
                    block["new_chunk"],
                    block["char_opcodes"],
                    relative,
                )
            return block["new_start"] + mapped
    raise RebaseError(f"unmapped global boundary: {position}")


def rebase_row(
    v2: Any,
    row: Mapping[str, Any],
    old_text: str,
    new_text: str,
    alignment: Sequence[Mapping[str, Any]],
    old_tables: tuple[Sequence[int], Sequence[int], Sequence[str]],
    new_tables: tuple[Sequence[int], Sequence[int], Sequence[str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _old_starts, _old_byte_starts, _old_lines = old_tables
    new_starts, new_byte_starts, new_lines = new_tables
    old_span = row.get("scalar_span")
    require(
        isinstance(old_span, list)
        and len(old_span) == 2
        and all(isinstance(item, int) for item in old_span),
        "invalid predecessor scalar span",
    )
    old_start, old_end = old_span
    require(old_text[old_start:old_end] == row.get("surface"), "predecessor surface drift")
    new_start = map_global_boundary(old_text, new_text, alignment, old_start)
    new_end = map_global_boundary(old_text, new_text, alignment, old_end)
    require(0 <= new_start < new_end <= len(new_text), "invalid rebased span")
    old_surface = row["surface"]
    new_surface = new_text[new_start:new_end]
    disposition = str(row.get("disposition", ""))
    protected = disposition.startswith(("PROTECT", "PRESERVE"))
    require(
        not protected or new_surface == old_surface,
        f"protected surface changed: {row.get('file')}:{row.get('line')}:{old_surface!r}->{new_surface!r}",
    )
    rebased = copy.deepcopy(dict(row))
    rebased["scalar_span"] = [new_start, new_end]
    rebased["surface"] = new_surface
    rebased["surface_sha256"] = sha256(new_surface.encode("utf-8"))
    observed = v2.locator(new_text, new_start, new_starts, new_byte_starts, new_lines)
    for key, value in observed.items():
        rebased[key] = value
    if "context" in rebased:
        rebased["context"] = new_text[max(0, new_start - 80) : min(len(new_text), new_start + 160)]
    return rebased, {
        "surface_changed": new_surface != old_surface,
        "span_shifted": [new_start, new_end] != old_span,
        "protected": protected,
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "occurrences": len(rows),
        "by_file": dict(sorted(Counter(row["file"] for row in rows).items())),
        "by_surface": dict(sorted(Counter(row["surface"] for row in rows).items())),
        "by_disposition": dict(
            sorted(Counter(row["disposition"] for row in rows).items())
        ),
        "inventory": describe(canonical_json(list(rows))),
    }


def roman_rows(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues = receipt.get("issues")
    require(isinstance(issues, list) and len(issues) == 722, "Roman issue census drift")
    counts = Counter(str(item["token_casefold"]) for item in issues)
    require(dict(sorted(counts.items())) == EXPECTED_ROMAN_FORMS, f"Roman forms drift: {counts}")
    rows: list[dict[str, Any]] = []
    for item in issues:
        start = item["scalar_offset"]
        surface = item["token"]
        rows.append(
            {
                "file": item["file"],
                "line": item["line"],
                "column": item["column"],
                "byte_offset": item["byte_offset"],
                "line_sha256": item["line_sha256"],
                "context_sha256": item["context_sha256"],
                "role": item["role"],
                "scalar_span": [start, start + len(surface)],
                "surface": surface,
                "surface_sha256": item["token_sha256"],
                "token_casefold": item["token_casefold"],
                "predecessor_scanner_reasons": item["reasons"],
                "disposition": "PRESERVE_STRUCTURAL_ROMAN_IDENTITY_V021",
            }
        )
    return rows


def validate_roman_rows(
    v2: Any,
    rows: Sequence[Mapping[str, Any]],
    texts: Mapping[str, str],
    tables: Mapping[str, tuple[Sequence[int], Sequence[int], Sequence[str]]],
) -> None:
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        filename = row["file"]
        start, end = row["scalar_span"]
        surface = row["surface"]
        require(texts[filename][start:end] == surface, "Roman surface drift")
        require(sha256(surface.encode("utf-8")) == row["surface_sha256"], "Roman hash drift")
        scalar_starts, byte_starts, lines = tables[filename]
        observed = v2.locator(texts[filename], start, scalar_starts, byte_starts, lines)
        for key in ("line", "column", "byte_offset", "line_sha256", "context_sha256"):
            require(observed[key] == row[key], f"Roman locator drift {key}")
        key = (filename, start, end)
        require(key not in seen, f"duplicate Roman span: {key}")
        seen.add(key)


def build() -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    v2 = load_v2()
    old_manifest_raw = read_exact(OLD_MANIFEST_PATH, OLD_MANIFEST_PIN, "v020 role manifest")
    old_manifest = strict_json(old_manifest_raw, str(OLD_MANIFEST_PATH))
    freeze_raw = read_exact(FREEZE_RECEIPT_PATH, FREEZE_RECEIPT_PIN, "Latin freeze receipt")
    freeze = strict_json(freeze_raw, str(FREEZE_RECEIPT_PATH))
    decision_raw = read_exact(FREEZE_DECISION_PATH, FREEZE_DECISION_PIN, "Latin freeze decision")
    decision = strict_json(decision_raw, str(FREEZE_DECISION_PATH))
    require(
        freeze.get("status") == "PASS_LIVE_SEALED_LATIN_ZERO_NON_ROMAN_PROJECTION_BLOCKS",
        "Latin freeze receipt not accepted",
    )
    require(decision.get("status") == "ACCEPT_LATIN_FREEZE_ZERO_NON_ROMAN_PROJECTION_BLOCKS", "Latin freeze decision drift")
    require(old_manifest.get("inventory_sha256_excluding_this_field") == "90EAFFEA8C2B8C17E301CCA94F80029CD1A3454E514EA3B3390376C300FDBCDE", "v020 internal digest drift")

    old_raws = read_sources(OLD_SOURCE_DIR, OLD_SOURCE_PINS)
    new_raws = read_sources(NEW_SOURCE_DIR, NEW_SOURCE_PINS)
    old_texts = {name: old_raws[name].decode("utf-8") for name in SOURCE_ORDER}
    new_texts = {name: new_raws[name].decode("utf-8") for name in SOURCE_ORDER}
    old_tables = {name: v2.line_tables(old_texts[name]) for name in SOURCE_ORDER}
    new_tables = {name: v2.line_tables(new_texts[name]) for name in SOURCE_ORDER}
    alignments = {
        name: build_alignment(
            old_texts[name],
            new_texts[name],
            old_tables[name][0],
            new_tables[name][0],
            old_tables[name][2],
            new_tables[name][2],
        )
        for name in SOURCE_ORDER
    }

    manifest = copy.deepcopy(old_manifest)
    metrics: dict[str, Any] = {}
    for category in CATEGORIES:
        rows = old_manifest.get(category)
        require(
            isinstance(rows, list) and len(rows) == EXPECTED_CATEGORY_COUNTS[category],
            f"category census drift: {category}",
        )
        rebased_rows: list[dict[str, Any]] = []
        flags: list[dict[str, Any]] = []
        for row in rows:
            filename = row["file"]
            rebased, flag = rebase_row(
                v2,
                row,
                old_texts[filename],
                new_texts[filename],
                alignments[filename],
                old_tables[filename],
                new_tables[filename],
            )
            rebased_rows.append(rebased)
            flags.append(flag)
        manifest[category] = rebased_rows
        metrics[category] = {
            "rows": len(rebased_rows),
            "surface_changes": sum(flag["surface_changed"] for flag in flags),
            "span_shifts": sum(flag["span_shifted"] for flag in flags),
            "protected_rows": sum(flag["protected"] for flag in flags),
            "protected_surface_changes": 0,
        }

    additions: list[dict[str, Any]] = []
    addition_flags: list[dict[str, Any]] = []
    for row in old_manifest["additional_protected_spans"]:
        filename = row["file"]
        rebased, flag = rebase_row(
            v2,
            row,
            old_texts[filename],
            new_texts[filename],
            alignments[filename],
            old_tables[filename],
            new_tables[filename],
        )
        additions.append(rebased)
        addition_flags.append(flag)
    require(len(additions) == 8, "additional protected-span census drift")
    manifest["additional_protected_spans"] = additions
    metrics["additional_protected_spans"] = {
        "rows": len(additions),
        "surface_changes": sum(flag["surface_changed"] for flag in addition_flags),
        "span_shifts": sum(flag["span_shifted"] for flag in addition_flags),
        "protected_rows": len(additions),
        "protected_surface_changes": 0,
    }

    romans = roman_rows(freeze)
    validate_roman_rows(v2, romans, new_texts, new_tables)
    manifest["v021_roman_identity_spans"] = romans
    manifest["schema"] = "noether-isv-reviewed-projection-role-manifest/3.0"
    manifest["status"] = "REBASED_FULLY_REVIEWED_ZERO_AMBIGUITY_BINDING_V021_GATE"
    manifest["scope"] = {
        "purpose": "source-bound role policy for deterministic Cyrillic projection",
        "predecessor_release": "NOETHER-ISV-v020",
        "successor_release": "NOETHER-ISV-v021",
        "latin_editorial_head": "ISV021-EDIT-0012",
        "latin_freeze_decision": "ISV021-LATIN-FREEZE",
        "source_order": list(SOURCE_ORDER),
        "latin_source_files_changed": 4,
        "latin_source_total_byte_delta_from_v020": sum(len(raw) for raw in new_raws.values()) - sum(len(raw) for raw in old_raws.values()),
        "cyrillic_is_independent_translation_witness": False,
    }
    manifest["closure_rule"] = (
        "The v021 projector must pin this manifest, the frozen Latin quartet, the inherited v020 review authority, and the accepted 722-site Roman identity inventory; consume every protected span; prove every corrected and Roman output effect; and reject missing, extra, duplicate, drifted, or unsafe rows before writing."
    )
    manifest["dependencies"]["v020_reviewed_role_manifest"] = {
        "path": str(OLD_MANIFEST_PATH),
        **describe(old_manifest_raw),
        "internal_sha256": "90EAFFEA8C2B8C17E301CCA94F80029CD1A3454E514EA3B3390376C300FDBCDE",
    }
    manifest["dependencies"]["v021_latin_freeze_receipt"] = {
        "path": "decision_records/ISV021-LATIN-FREEZE-PROJECTION-FRONTIER-R2.json",
        **describe(freeze_raw),
    }
    manifest["dependencies"]["v021_latin_freeze_decision"] = {
        "path": "decision_records/ISV021-LATIN-FREEZE-DECISION.json",
        **describe(decision_raw),
    }
    manifest["sources"] = [
        {
            "path": f"source_latin/{name}",
            **describe(new_raws[name]),
            "scalars": len(new_texts[name]),
            "lines": len(new_tables[name][2]),
        }
        for name in SOURCE_ORDER
    ]
    manifest["summaries"] = {
        category: summarize(manifest[category])
        for category in (*CATEGORIES, "additional_protected_spans", "v021_roman_identity_spans")
    }
    foreign_casefolds = sorted(
        {row["surface"].casefold() for row in manifest["unprotected_foreign_lexicon_hits"]}
    )
    manifest["foreign_lexicon"] = {
        "unique_casefold_tokens": len(foreign_casefolds),
        "casefold_inventory": describe(canonical_json(foreign_casefolds)),
        "policy_inherited_from": "NOETHER-ISV-v020 fully reviewed manifest",
    }
    manifest["review"]["source_rebase"] = {
        "status": "PASS_ALL_4568_HISTORICAL_ROWS_RELOCATED",
        "historical_rows": sum(EXPECTED_CATEGORY_COUNTS.values()) + 8,
        "roman_identity_rows_added": len(romans),
        "total_v021_source_bound_rows": sum(EXPECTED_CATEGORY_COUNTS.values()) + 8 + len(romans),
        "line_count_delta_by_file": {
            name: len(new_tables[name][2]) - len(old_tables[name][2])
            for name in SOURCE_ORDER
        },
        "protected_surface_changes": 0,
        "metrics": metrics,
        "method": "line-stable scalar-boundary alignment with exact old-surface authentication and full regenerated locator/hash validation",
        "human_review_gate": False,
    }
    manifest["review"]["v021_source_bound_records_emitted"] = (
        sum(EXPECTED_CATEGORY_COUNTS.values()) + 8 + len(romans)
    )
    manifest.pop("inventory_sha256_excluding_this_field", None)
    internal = sha256(canonical_json(manifest))
    manifest["inventory_sha256_excluding_this_field"] = internal
    manifest_raw = canonical_json(manifest)

    # Independent final replay from the rendered manifest object.
    reparsed = strict_json(manifest_raw, "rebased manifest in memory")
    claimed = reparsed.pop("inventory_sha256_excluding_this_field")
    require(claimed == internal and sha256(canonical_json(reparsed)) == internal, "rebased internal digest mismatch")
    report = {
        "schema": "noether-isv-v021-role-manifest-rebase-report-v1",
        "status": "PASS_REBASED_MANIFEST_IN_MEMORY",
        "predecessor_manifest": describe(old_manifest_raw),
        "output_manifest": {**describe(manifest_raw), "internal_sha256": internal},
        "source_pins": {name: describe(new_raws[name]) for name in SOURCE_ORDER},
        "line_count_delta_by_file": {
            name: len(new_tables[name][2]) - len(old_tables[name][2])
            for name in SOURCE_ORDER
        },
        "historical_rows_rebased": sum(EXPECTED_CATEGORY_COUNTS.values()) + 8,
        "roman_identity_rows_added": len(romans),
        "total_rows": sum(EXPECTED_CATEGORY_COUNTS.values()) + 8 + len(romans),
        "protected_surface_changes": 0,
        "metrics": metrics,
        "roman_forms": dict(sorted(Counter(row["token_casefold"] for row in romans).items())),
        "claims": {"source_writes": 0, "git": False, "network": False, "build": False, "render": False},
    }
    return manifest, manifest_raw, report


def exclusive_write(path: Path, raw: bytes) -> None:
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"unsafe output parent: {path.parent}")
    require(not path.exists(), f"refusing to overwrite: {path}")
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    require(path.read_bytes() == raw, f"write readback mismatch: {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--write-receipt", type=Path)
    args = parser.parse_args(argv)
    _manifest, manifest_raw, report = build()
    if args.write_manifest:
        exclusive_write(OUTPUT_MANIFEST_PATH, manifest_raw)
        report["manifest_install"] = {"path": str(OUTPUT_MANIFEST_PATH), **describe(OUTPUT_MANIFEST_PATH.read_bytes())}
    report_raw = canonical_json(report)
    if args.write_receipt is not None:
        exclusive_write(args.write_receipt, report_raw)
    sys.stdout.buffer.write(report_raw)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema": "noether-isv-v021-role-manifest-rebase-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        raise SystemExit(1)
