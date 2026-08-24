#!/usr/bin/env python3
"""Independent v021 Cyrillic reconstruction without importing v8."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
V2_PATH = ROOT / "comparison" / "predecessor_v019" / "project_isv_cyrillic_v2.py"
MANIFEST_PATH = ROOT / "decision_records" / "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json"
SOURCE_DIR = ROOT / "source_latin"
OUTPUT_DIR = ROOT / "source_cyrillic"
V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
MANIFEST_PIN = (
    4_177_721,
    "E5F629E2EC381A7D3247F30CBE7FBD03815639E2C6057E39BB13E8D1E427DD4B",
)
MANIFEST_INTERNAL = "1C20345E4F52A3936FCF103358D7B4B6938A67355F7AAA46AC4DC37715F08546"
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
SOURCE_PINS = {
    "44-book-isv.tex": (168_384, "FFEAE898972515A69D9BCD4930ECEEF2C91DD7114E0CA0B0F64E2157ED32E698"),
    "45-isv.tex": (26_036, "E49033F3C3004F921CD234610425905FF1D46405107D8EB99BC431864BB4473D"),
    "base-papers1-43-isv.tex": (1_893_083, "237FFE1460816EAF8CCD6E00F9500F816A285830CE62E28E49CECB94685B16E9"),
    "bib-isv.tex": (10_016, "D14F600C71E911F49F0A81B85B2C476F7BED490D597E2045AC55744774D201B1"),
}
OUTPUT_NAMES = {
    "44-book-isv.tex": "44-book-isv-cyrl.tex",
    "45-isv.tex": "45-isv-cyrl.tex",
    "base-papers1-43-isv.tex": "base-papers1-43-isv-cyrl.tex",
    "bib-isv.tex": "bib-isv-cyrl.tex",
}
EXPECTED_OUTPUT_PINS = {
    "44-book-isv-cyrl.tex": (230_381, "0DD9907518035924993A0041B14BCAEA10D7C213DAB8DF422F6B25E7DDED9D63"),
    "45-isv-cyrl.tex": (35_874, "40870377323594B3153A1F25D6BC2FB34899B6E6FDD388837388E9D12D147140"),
    "base-papers1-43-isv-cyrl.tex": (2_706_234, "E9C7AEC849C4B2D2B6E528AFB1B62236B9CFFBAD686FA4923749C9359EB2824C"),
    "bib-isv-cyrl.tex": (13_206, "37FFF904BB16B2B460923AE2BF801BF783803FD0B78B94AF83D21FF43B81AB47"),
}
CATEGORIES = (
    "unprotected_style_payloads",
    "unprotected_name_candidates",
    "unprotected_foreign_lexicon_hits",
    "visible_one_letter_tokens",
)
VISIBLE_ROLES = {"visible_prose", "visible_math_text", "visible_metadata"}
TEX_DIMENSION_RE = re.compile(
    r"(?i)(?<=[0-9])(?:true[ \t]*)?(?:filll|fill|fil|pt|pc|in|bp|cm|mm|dd|cc|sp|em|ex|mu)\b"
)


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


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
    read_exact(V2_PATH, V2_PIN, "frozen v2 transliteration authority")
    spec = importlib.util.spec_from_file_location("isv021_independent_v2", V2_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v2")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def union_ranges(text: str, ranges: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    ordered = sorted(ranges)
    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        require(0 <= start < end <= len(text), f"range out of bounds: {start}:{end}")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def project_file(v2: Any, text: str, filename: str, ranges: Sequence[tuple[int, int]]) -> tuple[bytes, dict[str, Any]]:
    merged = union_ranges(text, ranges)
    original = v2.TexSegmenter(text).segment()
    output: list[str] = []
    conversions: Counter[str] = Counter()
    range_index = 0
    for segment in original:
        cursor = segment.start
        while range_index < len(merged) and merged[range_index][1] <= segment.start:
            range_index += 1
        local_index = range_index
        pieces: list[tuple[int, int, bool]] = []
        while local_index < len(merged) and merged[local_index][0] < segment.end:
            left, right = merged[local_index]
            overlap_start = max(segment.start, left)
            overlap_end = min(segment.end, right)
            if cursor < overlap_start:
                pieces.append((cursor, overlap_start, False))
            if overlap_start < overlap_end:
                pieces.append((overlap_start, overlap_end, True))
                cursor = overlap_end
            local_index += 1
        if cursor < segment.end:
            pieces.append((cursor, segment.end, False))
        for start, end, forced_identity in pieces:
            raw = text[start:end]
            if forced_identity or segment.role not in VISIBLE_ROLES:
                output.append(raw)
                continue
            local_cursor = 0
            for match in v2.LETTER_RE.finditer(raw):
                output.append(raw[local_cursor : match.start()])
                word = match.group(0)
                reasons = v2.token_block_reasons(word)
                require(not reasons, f"independent projection blocker: {filename}:{word}:{reasons}")
                converted, classification = v2.project_word(word)
                output.append(converted)
                conversions[classification] += 1
                local_cursor = match.end()
            output.append(raw[local_cursor:])
    rendered = "".join(output)
    v2.validate_structure(rendered)
    raw = rendered.encode("utf-8")
    require(raw.endswith(b"\n") and b"\r" not in raw, f"output transport drift: {filename}")
    return raw, {
        "manifest_and_policy_ranges": len(ranges),
        "union_ranges": len(merged),
        "conversion_classes": dict(sorted(conversions.items())),
    }


def reconstruct(require_live: bool) -> tuple[dict[str, Any], dict[str, bytes]]:
    v2 = load_v2()
    manifest_raw = read_exact(MANIFEST_PATH, MANIFEST_PIN, "v021 role manifest")
    manifest = strict_json(manifest_raw, str(MANIFEST_PATH))
    without = copy.deepcopy(manifest)
    claimed = without.pop("inventory_sha256_excluding_this_field")
    require(claimed == MANIFEST_INTERNAL and sha256(canonical_json(without)) == MANIFEST_INTERNAL, "manifest internal digest mismatch")
    sources = {
        name: read_exact(SOURCE_DIR / name, SOURCE_PINS[name], name)
        for name in SOURCE_ORDER
    }
    rows_by_file: dict[str, list[tuple[int, int]]] = {name: [] for name in SOURCE_ORDER}
    protected_rows = 0
    for category in CATEGORIES:
        for row in manifest[category]:
            if str(row["disposition"]).startswith(("PROTECT", "PRESERVE")):
                start, end = row["scalar_span"]
                rows_by_file[row["file"]].append((start, end))
                protected_rows += 1
    for row in manifest["additional_protected_spans"]:
        start, end = row["scalar_span"]
        rows_by_file[row["file"]].append((start, end))
        protected_rows += 1
    roman_rows = manifest["v021_roman_identity_spans"]
    require(len(roman_rows) == 722, "Roman census drift")
    for row in roman_rows:
        start, end = row["scalar_span"]
        rows_by_file[row["file"]].append((start, end))

    outputs: dict[str, bytes] = {}
    files: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        text = v2.strict_transport(sources[filename], filename)
        for match in TEX_DIMENSION_RE.finditer(text):
            rows_by_file[filename].append((match.start(), match.end()))
        output, evidence = project_file(v2, text, filename, rows_by_file[filename])
        output_name = OUTPUT_NAMES[filename]
        require(
            (len(output), sha256(output)) == EXPECTED_OUTPUT_PINS[output_name],
            f"independent output pin mismatch: {output_name}: {describe(output)}",
        )
        require(len(output.splitlines()) == len(sources[filename].splitlines()), f"line topology drift: {filename}")
        outputs[filename] = output
        row = {
            "source": filename,
            "output": output_name,
            "generated": describe(output),
            **evidence,
        }
        if require_live:
            live = read_exact(OUTPUT_DIR / output_name, EXPECTED_OUTPUT_PINS[output_name], f"live {output_name}")
            require(live == output, f"live/generated mismatch: {output_name}")
            row["live"] = describe(live)
        files.append(row)
    output_manifest = [
        {"file": OUTPUT_NAMES[name], **describe(outputs[name])} for name in SOURCE_ORDER
    ]
    report = {
        "schema": "noether-isv-v021-cyrillic-independent-reconstruction-v1",
        "status": "PASS_INDEPENDENT_RECONSTRUCTION_AND_LIVE_IDENTITY" if require_live else "PASS_INDEPENDENT_RECONSTRUCTION_IN_MEMORY",
        "imports_v8": False,
        "authority": {"v2": {"bytes": V2_PIN[0], "sha256": V2_PIN[1]}, "manifest": {**describe(manifest_raw), "internal_sha256": MANIFEST_INTERNAL}},
        "protected_inherited_and_additional_rows": protected_rows,
        "roman_policy_rows": len(roman_rows),
        "output_manifest": output_manifest,
        "output_manifest_sha256": sha256(canonical_json(output_manifest)),
        "files": files,
        "claims": {"source_writes": 0, "output_writes": 0, "git": False, "network": False, "build": False, "render": False},
    }
    named_outputs = {OUTPUT_NAMES[name]: outputs[name] for name in SOURCE_ORDER}
    return report, named_outputs


def exclusive_write(path: Path, raw: bytes) -> None:
    require(path.parent.is_dir() and not path.parent.is_symlink(), f"unsafe receipt parent: {path.parent}")
    require(not path.exists(), f"refusing to overwrite receipt: {path}")
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    require(path.read_bytes() == raw, f"receipt readback mismatch: {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--write-receipt", type=Path)
    parser.add_argument(
        "--write-output-dir",
        type=Path,
        help="write the independently reconstructed four-file Cyrillic surface to a new or exact-matching directory",
    )
    args = parser.parse_args(argv)
    report, outputs = reconstruct(args.require_live)
    if args.write_output_dir is not None:
        target = args.write_output_dir
        if not target.is_absolute():
            target = ROOT / target
        target.mkdir(parents=True, exist_ok=True)
        require(target.is_dir() and not target.is_symlink(), f"unsafe output directory: {target}")
        require(target.resolve() not in {SOURCE_DIR.resolve(), OUTPUT_DIR.resolve()}, "refusing to write over canonical sources")
        for name, raw in sorted(outputs.items()):
            path = target / name
            if path.exists():
                require(path.is_file() and not path.is_symlink() and path.read_bytes() == raw, f"output conflict: {path}")
            else:
                exclusive_write(path, raw)
        report["claims"]["output_writes"] = len(outputs)
        report["written_output_dir"] = str(target)
    rendered = canonical_json(report)
    if args.write_receipt is not None:
        exclusive_write(args.write_receipt, rendered)
    sys.stdout.buffer.write(rendered)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"schema": "noether-isv-v021-cyrillic-independent-reconstruction-failure-v1", "status": "ERROR_FAIL_CLOSED", "error_type": type(error).__name__, "error": str(error)}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1)
