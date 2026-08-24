#!/usr/bin/env python3
"""Read-only audit for the Interslavic čest/čęst family.

The edition uses the project's basic, reader-facing spelling for this family:
``čest``, ``česti``, ``čestično``, and ``najčestěje``.  This audit authenticates
the live EDIT-0006 cohort, enumerates every related word token, and projects the
twelve remaining etymological-alphabet spellings to that established house
surface.  It never writes source files.
"""

from __future__ import annotations

from collections import Counter
import argparse
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
        26_041,
        "90825271429A2D3156FE752E8925D8D43DC34B5B962234DFA2EFD5D425A23FE8",
    ),
    "base-papers1-43-isv.tex": (
        1_894_589,
        "F84470C69F8D54103F7BB0DB38CCBA43D632F3113BBA17FA9E66D450A9384FC2",
    ),
    "bib-isv.tex": (
        10_021,
        "01DDAB0D12E697DDE422B8871CC5587E5AC5A69B66AB8B9E868A998E16CC982C",
    ),
}

ORTHOGRAPHY_PATH = (
    ROOT.parent
    / "00_lane_control"
    / "marginal_intelligibility_20260811"
    / "authority_snapshots"
    / "snapshots"
    / "official_site"
    / "docs"
    / "learn"
    / "orthography.md"
)
ORTHOGRAPHY_PIN = (
    16_443,
    "90C609CC0E8709E8395964E9F20D6D4FB4E31159CBC2B1EA515A29D9D1C72044",
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
PRIOR_FREQUENCY_PATH = (
    ROOT.parent
    / "noether_isv_v019_working"
    / "decision_records"
    / "ISV019-EDIT-0077.json"
)
PRIOR_FREQUENCY_PIN = (
    2_844,
    "0E8E055D7904697ECE0F112A71739956C8B291CEE5E545E10DCB61CC9B548E85",
)
PRIOR_BASIC_ALPHABET_PATH = (
    ROOT.parent
    / "noether_isv_v019_working"
    / "decision_records"
    / "ISV019-EDIT-0023.json"
)
PRIOR_BASIC_ALPHABET_PIN = (
    2_923,
    "601CD6E7676E6748706224BA7B4CEC46967B1E4E027C719FF08A9D8239E92E64",
)
EDIT0003_RECEIPT_PATH = (
    ROOT
    / "decision_records"
    / "ISV021-EDIT-0003-UNAPPLIED-CANDIDATE-RECEIPT-R2.json"
)
EDIT0003_RECEIPT_PIN = (
    9_159,
    "C7F2AD8E72446B89EA4817523D286FA2464C3A51B25C5A4E852F38754E63A38B",
)
EDIT0006_RECEIPT_PATH = (
    ROOT
    / "decision_records"
    / "ISV021-EDIT-0006-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
EDIT0006_RECEIPT_PIN = (
    69_344,
    "DE3986DB5A0EA5F96EFE17EEB70A013E550E1C2BD8F55CBF1FD6F930A93CB1F8",
)

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
REPLACEMENTS = {
    "Čęst": "Čest",
    "čęst": "čest",
    "čęsti": "česti",
    "čęstično": "čestično",
}
EXPECTED_TOKEN_COUNTS = Counter(
    {
        "čest": 50,
        "čęst": 2,
        "Čęst": 4,
        "čestěje": 1,
        "česti": 47,
        "Česti": 1,
        "čęsti": 1,
        "čestično": 5,
        "čęstično": 5,
        "čestičny": 1,
        "čestij": 12,
        "čestjah": 7,
        "čestju": 5,
        "čestne": 2,
        "čestnomu": 1,
        "čestny": 2,
        "često": 7,
        "najčestěje": 1,
        "sčestnikov": 1,
        "učestjem": 1,
    }
)
EXPECTED_REPLACEMENT_COUNTS = Counter(
    {"Čęst": 4, "čęst": 2, "čęsti": 1, "čęstično": 5}
)
EXPECTED_BY_FILE = {
    "44-book-isv.tex": 0,
    "45-isv.tex": 2,
    "base-papers1-43-isv.tex": 8,
    "bib-isv.tex": 2,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"{label} pin drift: {observed}")
    return data


def read_cohort() -> dict[str, bytes]:
    cohort: dict[str, bytes] = {}
    for name in SOURCE_ORDER:
        data = authenticate(SOURCE_DIR / name, SOURCE_PINS[name], name)
        data.decode("utf-8", errors="strict")
        cohort[name] = data
    return cohort


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    math_delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "line_count": text.count("\n") + 1,
        "open_braces": text.count("{"),
        "close_braces": text.count("}"),
        "percent_count": text.count("%"),
        "commands_count": len(commands),
        "commands_sha256": sha256("\n".join(commands).encode("utf-8")),
        "environments_count": len(environments),
        "environments_sha256": sha256("\n".join(environments).encode("utf-8")),
        "labels_count": len(labels),
        "labels_sha256": sha256("\n".join(labels).encode("utf-8")),
        "math_delimiters_count": len(math_delimiters),
        "math_delimiters_sha256": sha256(
            "\n".join(math_delimiters).encode("utf-8")
        ),
    }


def escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return bool(backslashes % 2)


def assert_visible(line: str, column0: int, label: str) -> None:
    for match in re.finditer("%", line):
        if match.start() < column0 and not escaped(line, match.start()):
            raise RuntimeError(f"target follows TeX comment at {label}")
    dollars = sum(
        1
        for match in re.finditer(r"\$", line[:column0])
        if not escaped(line[:column0], match.start())
    )
    if dollars % 2:
        raise RuntimeError(f"target is inside inline math at {label}")


def is_family(token: str) -> bool:
    folded = token.casefold()
    return "čest" in folded or "čęst" in folded


def scan(cohort: dict[str, bytes]) -> tuple[list[dict[str, Any]], Counter[str]]:
    manifest: list[dict[str, Any]] = []
    census: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        byte_line_start = 0
        for line_no, line_with_eol in enumerate(text.splitlines(keepends=True), start=1):
            line = line_with_eol.rstrip("\r\n")
            for match in WORD_RE.finditer(line):
                token = match.group(0)
                if not is_family(token):
                    continue
                census[token] += 1
                if token not in REPLACEMENTS:
                    continue
                assert_visible(line, match.start(), f"{filename}:{line_no}")
                byte_offset0 = byte_line_start + len(
                    line[: match.start()].encode("utf-8")
                )
                manifest.append(
                    {
                        "file": filename,
                        "line": line_no,
                        "column": match.start() + 1,
                        "byte_offset0": byte_offset0,
                        "before": token,
                        "after": REPLACEMENTS[token],
                        "family": "basic_reader_orthography_cest",
                    }
                )
            byte_line_start += len(line_with_eol.encode("utf-8"))
        if text and not text.endswith(("\n", "\r")):
            pass
    return manifest, census


def transform_one(data: bytes, items: list[dict[str, Any]], forward: bool) -> bytes:
    output = data
    for item in sorted(items, key=lambda value: value["byte_offset0"], reverse=True):
        old = (item["before"] if forward else item["after"]).encode("utf-8")
        new = (item["after"] if forward else item["before"]).encode("utf-8")
        offset = item["byte_offset0"]
        if output[offset : offset + len(old)] != old:
            raise RuntimeError(
                f"locator payload drift at {item['file']}:{item['line']}:{item['column']}"
            )
        output = output[:offset] + new + output[offset + len(old) :]
    output.decode("utf-8", errors="strict")
    return output


def project(
    cohort: dict[str, bytes], manifest: list[dict[str, Any]]
) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        items = [item for item in manifest if item["file"] == filename]
        outputs[filename] = transform_one(cohort[filename], items, True)
        reverse_items: list[dict[str, Any]] = []
        shrink = 0
        for item in sorted(items, key=lambda value: value["byte_offset0"]):
            adjusted = dict(item)
            adjusted["byte_offset0"] = item["byte_offset0"] - shrink
            reverse_items.append(adjusted)
            shrink += len(item["before"].encode("utf-8")) - len(
                item["after"].encode("utf-8")
            )
        if transform_one(outputs[filename], reverse_items, False) != cohort[filename]:
            raise RuntimeError(f"exact reverse failed for {filename}")
        before_structure = structural_signature(
            cohort[filename].decode("utf-8", errors="strict")
        )
        after_structure = structural_signature(
            outputs[filename].decode("utf-8", errors="strict")
        )
        if before_structure != after_structure:
            raise RuntimeError(f"protected TeX structure changed in {filename}")
    return outputs


def authenticate_authorities() -> dict[str, Any]:
    orthography = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "orthography")
    orthography_lines = orthography.decode("utf-8", errors="strict").splitlines()
    required = {
        69: "optional letters",
        80: "simply leaving out the diacritic",
        102: "refrain from using this orthography in everyday conversations",
        104: "once you decide to use a certain character from the extended set, use it consistently",
    }
    for line_no, needle in required.items():
        if needle not in orthography_lines[line_no - 1]:
            raise RuntimeError(f"orthography line {line_no} evidence drift")

    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    dictionary_text = dictionary.decode("utf-8-sig", errors="strict")
    required_dictionary = (
        "čęsť,,f.,1,part",
        "čęstično,,adv.,1,\"partly, partially\"",
        "**čestično**",
        "najčęstěje,,adv.,1,\"generally, most often\"",
        "**najčestěje**",
        "**učestnikov**",
    )
    for needle in required_dictionary:
        if needle not in dictionary_text:
            raise RuntimeError(f"dictionary evidence absent: {needle}")

    frequency_bytes = authenticate(
        PRIOR_FREQUENCY_PATH, PRIOR_FREQUENCY_PIN, "frequency decision"
    )
    frequency = json.loads(frequency_bytes.decode("utf-8", errors="strict"))
    if frequency.get("choice") != "Replace največestěje with official najčestěje.":
        raise RuntimeError("prior najčestěje decision drift")
    if "project spelling najčestěje" not in str(frequency.get("evidence", {})):
        raise RuntimeError("prior project-spelling evidence drift")

    basic_bytes = authenticate(
        PRIOR_BASIC_ALPHABET_PATH,
        PRIOR_BASIC_ALPHABET_PIN,
        "basic-alphabet decision",
    )
    basic = json.loads(basic_bytes.decode("utf-8", errors="strict"))
    if "standard project spelling: pytanje" not in basic.get("choice", ""):
        raise RuntimeError("prior basic-alphabet decision drift")

    edit0003_bytes = authenticate(
        EDIT0003_RECEIPT_PATH, EDIT0003_RECEIPT_PIN, "EDIT-0003 receipt"
    )
    edit0003 = json.loads(edit0003_bytes.decode("utf-8", errors="strict"))
    edit0003_wrappers = [
        item
        for item in edit0003.get("audit", {}).get("locators", [])
        if item.get("before") == "Čest" and item.get("after") == "Čęst"
    ]
    if len(edit0003_wrappers) != 2:
        raise RuntimeError("EDIT-0003 wrapper adverse history drift")

    edit0006_bytes = authenticate(
        EDIT0006_RECEIPT_PATH, EDIT0006_RECEIPT_PIN, "EDIT-0006 receipt"
    )
    edit0006 = json.loads(edit0006_bytes.decode("utf-8", errors="strict"))
    edit0006_wrappers = [
        item
        for item in edit0006.get("locator_manifest", {}).get("value", [])
        if item.get("before") == "Čest IV" and item.get("after") == "Čęst IV"
    ]
    if len(edit0006_wrappers) != 2:
        raise RuntimeError("EDIT-0006 wrapper adverse history drift")

    return {
        "official_orthography": {
            "path": str(ORTHOGRAPHY_PATH),
            **pin(orthography),
            "lines": [69, 80, 102, 104],
            "finding": "ę is optional; the basic spelling omits its diacritic, and reader-facing use is preferred unless the extended alphabet serves an explicit purpose.",
        },
        "official_dictionary": {
            "path": str(DICTIONARY_PATH),
            **pin(dictionary),
            "finding": "Etymological headwords coexist with basic-alphabet examples čestično, najčestěje, and učestnikov.",
        },
        "project_house_decisions": [
            {"path": str(PRIOR_FREQUENCY_PATH), **pin(frequency_bytes)},
            {"path": str(PRIOR_BASIC_ALPHABET_PATH), **pin(basic_bytes)},
        ],
        "adverse_history": [
            {
                "path": str(EDIT0003_RECEIPT_PATH),
                **pin(edit0003_bytes),
                "wrapper_sites_to_reverse": 2,
            },
            {
                "path": str(EDIT0006_RECEIPT_PATH),
                **pin(edit0006_bytes),
                "wrapper_sites_to_reverse": 2,
            },
        ],
    }


def build_report() -> dict[str, Any]:
    cohort = read_cohort()
    authorities = authenticate_authorities()
    manifest, census = scan(cohort)
    if census != EXPECTED_TOKEN_COUNTS:
        raise RuntimeError(f"čest-family census drift: {dict(census)}")
    replacement_counts = Counter(item["before"] for item in manifest)
    if replacement_counts != EXPECTED_REPLACEMENT_COUNTS:
        raise RuntimeError(f"replacement census drift: {dict(replacement_counts)}")
    by_file = Counter(item["file"] for item in manifest)
    if {name: by_file[name] for name in SOURCE_ORDER} != EXPECTED_BY_FILE:
        raise RuntimeError(f"per-file replacement census drift: {dict(by_file)}")
    if len(manifest) != 12 or len({(i["file"], i["line"]) for i in manifest}) != 8:
        raise RuntimeError("site or physical-line cardinality drift")

    outputs = project(cohort, manifest)
    projected_manifest, projected_census = scan_projected(outputs)
    if projected_manifest:
        raise RuntimeError("projected cohort retains nasalized target family")
    expected_projected = EXPECTED_TOKEN_COUNTS.copy()
    for before, count in EXPECTED_REPLACEMENT_COUNTS.items():
        expected_projected[before] -= count
        if not expected_projected[before]:
            del expected_projected[before]
        expected_projected[REPLACEMENTS[before]] += count
    if projected_census != expected_projected:
        raise RuntimeError("projected family census drift")

    manifest_payload = canonical_bytes(manifest)
    return {
        "schema": "noether-isv-v021-cest-family-basic-orthography-audit-v1",
        "edit_id": "ISV021-EDIT-0007",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "coverage": {
            "family_tokens": sum(census.values()),
            "sites": len(manifest),
            "physical_lines": len({(i["file"], i["line"]) for i in manifest}),
            "by_before": dict(sorted(replacement_counts.items())),
            "by_file": {name: by_file[name] for name in SOURCE_ORDER},
            "predecessor_token_census": dict(sorted(census.items())),
            "projected_token_census": dict(sorted(projected_census.items())),
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_payload),
            "sha256": sha256(manifest_payload),
            "value": manifest,
        },
        "authorities": authorities,
        "explicit_exclusions": {
            "sčestnikov": "Separate lexical defect candidate; not silently conflated with this orthographic family.",
            "učestjem": "Semantically transparent participation noun and consistent with the basic-alphabet house surface; retained pending its own grammar check.",
            "all_other_family_tokens": "Already use the established nonnasal house surface and remain byte-identical.",
        },
        "validation": {
            "exact_reverse": True,
            "utf8": True,
            "visible_prose_only": True,
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


def scan_projected(
    cohort: dict[str, bytes]
) -> tuple[list[dict[str, Any]], Counter[str]]:
    manifest: list[dict[str, Any]] = []
    census: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in WORD_RE.finditer(line):
                token = match.group(0)
                if not is_family(token):
                    continue
                census[token] += 1
                if token in REPLACEMENTS:
                    manifest.append(
                        {
                            "file": filename,
                            "line": line_no,
                            "column": match.start() + 1,
                            "before": token,
                        }
                    )
    return manifest, census


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
