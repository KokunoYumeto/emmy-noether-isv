#!/usr/bin/env python3
"""Producer-independent verifier for ISV021-EDIT-0010.

Imports neither the audit, applicator, segmenter, nor transaction core.
"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
RECEIPT_PATH = (
    ROOT / "decision_records" / "ISV021-EDIT-0010-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    34_939,
    "7223BC416806FF195C35BE8ECA9CD294160DC285AFAF467486C8E4DEA9118FFB",
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
PREDECESSOR = {
    "44-book-isv.tex": (
        168_427,
        "39FC522BFABDCA4F61A08ED5654224122AC0C64299F078FB16D31A90F3662415",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_613,
        "C1B9BAC6DC890F8544A8661712B0B87FFC854871BFB52792FD11FAFA82358719",
    ),
    "bib-isv.tex": (
        10_020,
        "7A45365DC7C9408CF3D50FDAA4C35081E032CC6F07D73A9954D3B1DDF18C9EC7",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": (
        168_427,
        "233A76BFBC11C21C0A8EEDCB74D6C6208D7A37B1085BFD7ED3D817A17B4C5793",
    ),
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_613,
        "71D7297364CFC43BD45DAE6D61E252A6351EAE116C076C8F7A58649B0E5BB4E2",
    ),
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}
EXPECTED_LOCATOR_BYTES = 17_641
EXPECTED_LOCATOR_SHA256 = (
    "451BA8C7A605A7BA06C9C5F0749014099933DB57AE5AAF0294E1D3B1F902F715"
)
VISIBLE_ROLES = {"visible_prose", "visible_math_text", "visible_metadata"}
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
WORD_MAP = {
    "dopušča": "dopušća",
    "dopuščajut": "dopušćajut",
    "dopuščaje": "dopušćaje",
    "dopuščanju": "dopušćanju",
    "skračeno": "skraćeno",
    "skračajuče": "skraćajuče",
    "skračene": "skraćene",
    "skračenja": "skraćenja",
    "skračenom": "skraćenom",
    "skračivati": "skraćivati",
    "skračujuče": "skraćujuče",
    "vračajuči": "vraćajuči",
    "vozvrača": "vozvraća",
    "vozvračanje": "vozvraćanje",
    "vozvračenje": "vozvraćenje",
    "vozvračenju": "vozvraćenju",
    "vrača": "vraća",
    "vračanja": "vraćanja",
}
EXPECTED_BEFORE = Counter(
    {
        "dopušča": 55,
        "dopuščajut": 21,
        "dopuščaje": 2,
        "dopuščanju": 1,
        "skračeno": 6,
        "skračajuče": 1,
        "skračene": 1,
        "skračenja": 1,
        "skračenom": 1,
        "skračivati": 1,
        "skračujuče": 1,
        "vračajuči": 2,
        "vozvrača": 1,
        "vozvračanje": 1,
        "vozvračenje": 1,
        "vozvračenju": 1,
        "vrača": 1,
        "vračanja": 1,
    }
)
EXPECTED_SUCCESSOR = Counter(
    {
        "dopušća": 81,
        "dopušćaje": 2,
        "dopušćajut": 27,
        "dopušćanju": 1,
        "skraćajuče": 1,
        "skraćene": 1,
        "skraćenja": 2,
        "skraćeno": 7,
        "skraćenom": 1,
        "skraćivati": 1,
        "skraćujuče": 1,
        "vozvraća": 2,
        "vozvraćanje": 1,
        "vozvraćenje": 1,
        "vozvraćenju": 1,
        "vraća": 1,
        "vraćajuči": 3,
        "vraćanja": 1,
    }
)
AUTHORITY_IDS = {
    "7208": "dopušćati",
    "20859": "dopušćati",
    "3139": "skraćati",
    "953": "skråćeńje",
    "17039": "skråćeny",
    "1839": "vraćati",
    "22658": "vraćati sę",
    "22646": "vȯzvraćati",
    "18360": "vȯzvråćeńje",
    "20192": "sųćstvėno",
    "20193": "sųćstvėny",
}
RETURN_CONTEXTS = {
    4409: "vrača k osnovnoj formě",
    14396: "vozvrača se v §~4",
    15263: "vozvračanje k sukcesivnoj eliminaciji",
    15527: "vračajuči se ponovno",
    15642: "vozvračenje k modulam",
    19754: "vozvračenju klasov modulov",
    22791: "Vračajuči se ot togo",
    24194: "zaradi vračanja k odinokym městam",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    if (len(data), sha256(data)) != expected:
        raise RuntimeError(f"{label} pin drift")
    return data


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    for data in cohort.values():
        data.decode("utf-8", errors="strict")
    return cohort


def load_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt status drift")
    manifest = receipt.get("locator_manifest", {}).get("value")
    if not isinstance(manifest, list) or len(manifest) != 99:
        raise RuntimeError("candidate manifest cardinality drift")
    payload = canonical_bytes(manifest)
    if (len(payload), sha256(payload)) != (
        EXPECTED_LOCATOR_BYTES,
        EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("candidate manifest hash drift")
    counts: Counter[str] = Counter()
    for item in manifest:
        folded = item["before"].casefold()
        if folded not in WORD_MAP or item["after"].casefold() != WORD_MAP[folded]:
            raise RuntimeError("candidate mapping drift")
        if item.get("role") not in VISIBLE_ROLES:
            raise RuntimeError("non-visible manifest role")
        counts[folded] += 1
    if counts != EXPECTED_BEFORE:
        raise RuntimeError(f"candidate before census drift: {dict(counts)}")
    return manifest, {"path": str(RECEIPT_PATH), **pin(receipt_bytes)}


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


def transform(
    cohort: dict[str, bytes], manifest: list[dict[str, Any]], forward: bool
) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        data = cohort[filename]
        items = [item for item in manifest if item["file"] == filename]
        if not forward:
            items = shifted_for_successor(items)
        for item in sorted(items, key=lambda value: value["byte_offset0"], reverse=True):
            old_text = item["before"] if forward else item["after"]
            new_text = item["after"] if forward else item["before"]
            old = old_text.encode("utf-8")
            new = new_text.encode("utf-8")
            offset = item["byte_offset0"]
            if data[offset : offset + len(old)] != old:
                raise RuntimeError(
                    f"payload mismatch at {filename}:{item['line']}:{item['column']}"
                )
            data = data[:offset] + new + data[offset + len(old) :]
        data.decode("utf-8", errors="strict")
        outputs[filename] = data
    return outputs


def census(cohort: dict[str, bytes], forms: set[str]) -> Counter[str]:
    result: Counter[str] = Counter()
    for data in cohort.values():
        for token in WORD_RE.findall(data.decode("utf-8", errors="strict")):
            folded = token.casefold()
            if folded in forms:
                result[folded] += 1
    return result


def protected_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    prefixes = (
        "sučstven",
        "sućstven",
        "najsučstven",
        "najsućstven",
        "nesučstven",
        "nesućstven",
    )
    for data in cohort.values():
        for token in WORD_RE.findall(data.decode("utf-8", errors="strict")):
            folded = token.casefold()
            if folded.startswith(prefixes):
                result[folded] += 1
    return result


def escaped(text: str, index: int) -> bool:
    count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        count += 1
        cursor -= 1
    return bool(count % 2)


def verify_locations(predecessor: dict[str, bytes], manifest: list[dict[str, Any]]) -> None:
    for item in manifest:
        data = predecessor[item["file"]]
        text = data.decode("utf-8", errors="strict")
        lines = text.splitlines(keepends=True)
        line = lines[item["line"] - 1].rstrip("\r\n")
        column0 = item["column"] - 1
        if line[column0 : column0 + len(item["before"])] != item["before"]:
            raise RuntimeError("independent line/column locator mismatch")
        line_start = sum(
            len(value.encode("utf-8")) for value in lines[: item["line"] - 1]
        )
        offset = line_start + len(line[:column0].encode("utf-8"))
        if offset != item["byte_offset0"]:
            raise RuntimeError("independent byte locator mismatch")
        for match in re.finditer("%", line):
            if match.start() < column0 and not escaped(line, match.start()):
                raise RuntimeError("target follows a TeX comment")
        prefix = line[:column0]
        dollars = sum(
            1 for match in re.finditer(r"\$", prefix) if not escaped(prefix, match.start())
        )
        if dollars % 2:
            raise RuntimeError("target lies inside inline math")


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    math = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "lines": text.count("\n") + 1,
        "braces": (text.count("{"), text.count("}")),
        "percent": text.count("%"),
        "commands": (len(commands), sha256("\n".join(commands).encode("utf-8"))),
        "environments": (
            len(environments),
            sha256("\n".join(environments).encode("utf-8")),
        ),
        "labels": (len(labels), sha256("\n".join(labels).encode("utf-8"))),
        "math": (len(math), sha256("\n".join(math).encode("utf-8"))),
    }


def verify_authorities(predecessor: dict[str, bytes]) -> dict[str, Any]:
    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    found: dict[str, str] = {}
    example = ""
    with DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in AUTHORITY_IDS:
                found[row["id"]] = row["isv"]
                if row["id"] == "20193":
                    example = row["using_example"]
    if found != AUTHORITY_IDS:
        raise RuntimeError("official authority row drift")
    if "sučstvenyh" not in example:
        raise RuntimeError("official variant example drift")
    lines = predecessor["base-papers1-43-isv.tex"].decode("utf-8").splitlines()
    for line_number, needle in RETURN_CONTEXTS.items():
        if needle not in lines[line_number - 1]:
            raise RuntimeError(f"return-sense context drift at line {line_number}")
    return {
        "official_dictionary": {"path": str(DICTIONARY_PATH), **pin(dictionary)},
        "official_rows": AUTHORITY_IDS,
        "return_sense_control_lines": sorted(RETURN_CONTEXTS),
        "variant_example": "row 20193 contains sučstvenyh",
    }


def main() -> int:
    manifest, receipt = load_manifest()
    live = read_cohort()
    live_pins = observed_pins(live)
    if live_pins == PREDECESSOR:
        predecessor = live
        successor = transform(live, manifest, True)
        if observed_pins(successor) != SUCCESSOR:
            raise RuntimeError("independent forward projection mismatch")
        if transform(successor, manifest, False) != predecessor:
            raise RuntimeError("independent exact reverse failed")
        status = "PASS_PREDECESSOR"
    elif live_pins == SUCCESSOR:
        successor = live
        predecessor = transform(live, manifest, False)
        if observed_pins(predecessor) != PREDECESSOR:
            raise RuntimeError("independent reverse projection mismatch")
        if transform(predecessor, manifest, True) != successor:
            raise RuntimeError("independent successor replay failed")
        status = "PASS_SUCCESSOR"
    else:
        raise RuntimeError(f"live cohort is neither frozen state: {live_pins}")

    old_census = census(predecessor, set(WORD_MAP))
    if old_census != EXPECTED_BEFORE:
        raise RuntimeError(f"predecessor target census drift: {dict(old_census)}")
    if census(successor, set(WORD_MAP)):
        raise RuntimeError("successor old-word residue")
    new_census = census(successor, set(WORD_MAP.values()))
    if new_census != EXPECTED_SUCCESSOR:
        raise RuntimeError(f"successor relevant census drift: {dict(new_census)}")
    pre_protected = protected_census(predecessor)
    post_protected = protected_census(successor)
    if pre_protected != post_protected or sum(pre_protected.values()) != 58:
        raise RuntimeError("protected official-variant family drift")
    verify_locations(predecessor, manifest)
    authorities = verify_authorities(predecessor)
    for filename in SOURCE_ORDER:
        before_structure = structural_signature(predecessor[filename].decode("utf-8"))
        after_structure = structural_signature(successor[filename].decode("utf-8"))
        if before_structure != after_structure:
            raise RuntimeError(f"protected TeX structure differs in {filename}")

    report = {
        "schema": "noether-isv-v021-official-consonant-majorities-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0010",
        "status": status,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authorities": authorities,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "source_distribution": dict(sorted(Counter(item["file"] for item in manifest).items())),
            "predecessor_target_census": dict(sorted(old_census.items())),
            "successor_relevant_census": dict(sorted(new_census.items())),
            "successor_target_residue": 0,
            "protected_variant_surfaces": sum(pre_protected.values()),
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "line_column_byte_locators": True,
            "comment_and_inline_math_boundaries": True,
            "utf8": True,
            "protected_tex_structure_equal": True,
            "protected_variant_family_equal": True,
            "source_writes": 0,
        },
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
