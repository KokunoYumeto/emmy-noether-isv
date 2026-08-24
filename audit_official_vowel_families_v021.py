#!/usr/bin/env python3
"""Read-only audit of direct-official residual vowel families for v021.

The audit authenticates the exact EDIT-0008 successor, uses the pinned v2 TeX
segmenter only to identify reader-visible roles, proves an exact reversible
projection, and never writes source files.
"""

from __future__ import annotations

from collections import Counter
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import types
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
SEGMENTER_PATH = ROOT.parent / "noether_isv_v019_working" / "project_isv_cyrillic_v2.py"
SEGMENTER_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
DICTIONARY_PATH = Path(
    r"<WORKSPACE_ROOT>\01_methodology"
    r"\claude_fable_program\data"
    r"\interslavic_dictionary_official_snapshot_20260816"
    r"\source_sheet_basic.csv"
)
DICTIONARY_PIN = (
    8_101_157,
    "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561",
)
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
SOURCE_PINS = {
    "44-book-isv.tex": (
        168_410,
        "77A0DA8AE3385520C12D91795CE645944AE7CE60F7F7831D3A7CE47BC76A27F5",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_571,
        "66399487B71DBA6FB8FC8DE8D91FC95F415D9974D602373D9F5E5C4E1EE401B1",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
VISIBLE_ROLES = frozenset({"visible_prose", "visible_math_text", "visible_metadata"})
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
TARGETS = {
    "iměnno": ("imenno", "official_imenno"),
    "izsledovali": ("izslědovali", "official_izsledovati"),
    "nekoliko": ("několiko", "official_nekoliko"),
    "nekoje": ("někoje", "official_nekoj"),
    "neku": ("něku", "official_nekoj"),
    "posle": ("poslě", "official_posle"),
    "tesno": ("těsno", "official_tesno"),
    "trebuje": ("trěbuje", "official_trebovati"),
    "trebujut": ("trěbujut", "official_trebovati"),
    "upotrebjena": ("upotrěbjena", "official_upotrebiti"),
    "upotrebjene": ("upotrěbjene", "official_upotrebiti"),
    "upotrebljen": ("upotrěbljen", "official_upotrebiti"),
    "vsěgda": ("vsegda", "official_vsegda"),
}
EXPECTED_BEFORE = Counter(
    {
        "iměnno": 2,
        "izsledovali": 1,
        "nekoliko": 10,
        "nekoje": 14,
        "neku": 2,
        "posle": 2,
        "tesno": 1,
        "trebuje": 1,
        "trebujut": 1,
        "upotrebjena": 1,
        "upotrebjene": 1,
        "upotrebljen": 1,
        "vsěgda": 8,
    }
)
EXPECTED_FAMILIES = Counter(
    {
        "official_nekoj": 16,
        "official_nekoliko": 10,
        "official_vsegda": 8,
        "official_imenno": 2,
        "official_posle": 2,
        "official_trebovati": 2,
        "official_upotrebiti": 3,
        "official_izsledovati": 1,
        "official_tesno": 1,
    }
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"{label} pin drift: {observed}")
    return data


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_segmenter() -> Any:
    data = authenticate(SEGMENTER_PATH, SEGMENTER_PIN, "v2 TeX segmenter")
    module = types.ModuleType("isv021_edit0009_segmenter")
    module.__file__ = str(SEGMENTER_PATH)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    exec(compile(data, str(SEGMENTER_PATH), "exec"), module.__dict__)
    return module


SEGMENTER = load_segmenter()


def read_cohort() -> dict[str, bytes]:
    cohort: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        data = authenticate(SOURCE_DIR / filename, SOURCE_PINS[filename], filename)
        data.decode("utf-8", errors="strict")
        cohort[filename] = data
    return cohort


def line_starts(text: str) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    return starts


def line_for_offset(starts: list[int], offset: int) -> int:
    lo = 0
    hi = len(starts)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if starts[mid] <= offset:
            lo = mid
        else:
            hi = mid
    return lo


def mapped(token: str) -> tuple[str, str] | None:
    value = TARGETS.get(token.casefold())
    if value is None:
        return None
    after, family = value
    if token and token[0].isupper():
        after = after[0].upper() + after[1:]
    return after, family


def scan(cohort: dict[str, bytes]) -> tuple[list[dict[str, Any]], Counter[str]]:
    manifest: list[dict[str, Any]] = []
    before_census: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        starts = line_starts(text)
        segmenter = SEGMENTER.TexSegmenter(text)
        segments = segmenter.segment()
        if segmenter.unknown_argument_commands:
            raise RuntimeError(f"unknown argument commands in {filename}")
        for segment in segments:
            if segment.role not in VISIBLE_ROLES:
                continue
            raw = text[segment.start : segment.end]
            for match in WORD_RE.finditer(raw):
                token = match.group(0)
                change = mapped(token)
                if change is None:
                    continue
                after, family = change
                scalar_offset0 = segment.start + match.start()
                line_index = line_for_offset(starts, scalar_offset0)
                column = scalar_offset0 - starts[line_index] + 1
                before_census[token.casefold()] += 1
                manifest.append(
                    {
                        "file": filename,
                        "line": line_index + 1,
                        "column": column,
                        "byte_offset0": len(text[:scalar_offset0].encode("utf-8")),
                        "before": token,
                        "after": after,
                        "family": family,
                        "role": segment.role,
                    }
                )
    return manifest, before_census


def shifted_for_successor(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    delta = 0
    for item in sorted(items, key=lambda value: value["byte_offset0"]):
        adjusted = dict(item)
        adjusted["byte_offset0"] = item["byte_offset0"] + delta
        result.append(adjusted)
        delta += len(item["after"].encode("utf-8")) - len(
            item["before"].encode("utf-8")
        )
    return result


def transform_one(data: bytes, items: list[dict[str, Any]], forward: bool) -> bytes:
    output = data
    for item in sorted(items, key=lambda value: value["byte_offset0"], reverse=True):
        old_text = item["before"] if forward else item["after"]
        new_text = item["after"] if forward else item["before"]
        old = old_text.encode("utf-8")
        new = new_text.encode("utf-8")
        offset = item["byte_offset0"]
        if output[offset : offset + len(old)] != old:
            raise RuntimeError(
                f"payload drift at {item['file']}:{item['line']}:{item['column']}"
            )
        output = output[:offset] + new + output[offset + len(old) :]
    output.decode("utf-8", errors="strict")
    return output


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    math = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "lines": text.count("\n") + 1,
        "braces": [text.count("{"), text.count("}")],
        "percent": text.count("%"),
        "commands": [len(commands), sha256("\n".join(commands).encode("utf-8"))],
        "environments": [
            len(environments),
            sha256("\n".join(environments).encode("utf-8")),
        ],
        "labels": [len(labels), sha256("\n".join(labels).encode("utf-8"))],
        "math": [len(math), sha256("\n".join(math).encode("utf-8"))],
    }


def project(
    cohort: dict[str, bytes], manifest: list[dict[str, Any]]
) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        items = [item for item in manifest if item["file"] == filename]
        output = transform_one(cohort[filename], items, True)
        reverse = transform_one(output, shifted_for_successor(items), False)
        if reverse != cohort[filename]:
            raise RuntimeError(f"exact reverse failed for {filename}")
        if structural_signature(cohort[filename].decode("utf-8")) != structural_signature(
            output.decode("utf-8")
        ):
            raise RuntimeError(f"protected TeX structure changed in {filename}")
        outputs[filename] = output
    return outputs


def authenticate_authority() -> dict[str, Any]:
    data = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "official dictionary")
    wanted = {
        "imenno",
        "izslědovati",
        "někoj",
        "několiko",
        "poněkoj",
        "poslě",
        "těsno",
        "trěbovati",
        "upotrěbiti",
        "vsegda, vsegdy",
    }
    rows: dict[str, dict[str, str]] = {}
    with DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["isv"] in wanted:
                rows[row["isv"]] = {
                    key: row[key]
                    for key in ("id", "isv", "partOfSpeech", "en", "using_example")
                }
    if set(rows) != wanted:
        raise RuntimeError(f"official authority rows drifted: {sorted(rows)}")
    evidence_needles = {
        "někoj": "někojih",
        "poněkoj": "Poněkoje",
        "trěbovati": "trěbujut",
        "upotrěbiti": "upotrěbjena",
        "vsegda, vsegdy": "vsegda",
    }
    for headword, needle in evidence_needles.items():
        if needle not in rows[headword]["using_example"]:
            raise RuntimeError(f"dictionary example drift for {headword}")
    return {
        "path": str(DICTIONARY_PATH),
        **pin(data),
        "rows": [rows[key] for key in sorted(rows)],
    }


def output_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    forms = set(TARGETS) | {value[0] for value in TARGETS.values()}
    for data in cohort.values():
        text = data.decode("utf-8", errors="strict")
        for token in WORD_RE.findall(text):
            if token.casefold() in forms:
                result[token.casefold()] += 1
    return result


def build_report() -> dict[str, Any]:
    cohort = read_cohort()
    authority = authenticate_authority()
    manifest, before = scan(cohort)
    if before != EXPECTED_BEFORE:
        raise RuntimeError(f"target census drift: {dict(before)}")
    families = Counter(item["family"] for item in manifest)
    if families != EXPECTED_FAMILIES:
        raise RuntimeError(f"family census drift: {dict(families)}")
    if len(manifest) != 45 or len({(i["file"], i["line"]) for i in manifest}) != 42:
        raise RuntimeError("site or physical-line cardinality drift")
    if Counter(item["file"] for item in manifest) != Counter(
        {"base-papers1-43-isv.tex": 44, "44-book-isv.tex": 1}
    ):
        raise RuntimeError("source distribution drift")
    outputs = project(cohort, manifest)
    after = output_census(outputs)
    for old in TARGETS:
        if after[old]:
            raise RuntimeError(f"projected target residue: {old}")
    manifest_bytes = canonical_bytes(manifest)
    return {
        "schema": "noether-isv-v021-official-vowel-families-audit-v1",
        "edit_id": "ISV021-EDIT-0009",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(i["file"], i["line"]) for i in manifest}),
            "families": dict(sorted(families.items())),
            "before_census": dict(sorted(before.items())),
            "projected_relevant_census": dict(sorted(after.items())),
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": manifest,
        },
        "authority": {"official_dictionary": authority},
        "exclusions": {
            "optional_etymological_vowels": "No svęz/svez or vzęti/vzeti form is changed; ę is optional and those families require a separate declared house-policy decision.",
            "non_direct_house_variants": "složnejši and Sovmestno are excluded pending separate grammar/house review because the pinned dictionary does not directly expose their exact surfaces.",
        },
        "validation": {
            "exact_reverse": True,
            "utf8": True,
            "v2_visible_roles_only": True,
            "unknown_argument_commands": 0,
            "protected_tex_structure_equal": True,
            "source_writes": 0,
        },
        "claims": {
            "applied": False,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
            "native_or_community_certification": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = build_report()
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=args.compact,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
