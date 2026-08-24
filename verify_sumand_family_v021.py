#!/usr/bin/env python3
"""Independent predecessor/successor verifier for ISV021-EDIT-0008.

This verifier imports neither the audit, applicator, nor transaction core.
"""

from __future__ import annotations

from collections import Counter
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
    ROOT / "decision_records" / "ISV021-EDIT-0008-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    6_701,
    "ECF461D81F9C81F84D905FB1EA631F11FA2EB544FC72B9FBAE8D7AEABB1B1E4F",
)
GERMAN_PATH = Path(
    r"<WORKSPACE_ROOT>\03_projects\noether"
    r"\07_german_canon_control\candidates\ED0015\noether.tex"
)
GERMAN_PIN = (
    2_154_017,
    "51A25101C04877AE740989E72B2AD65A7A7E65B081077C4A518BF1737AD5B907",
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
        168_410,
        "77A0DA8AE3385520C12D91795CE645944AE7CE60F7F7831D3A7CE47BC76A27F5",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_581,
        "C33CF08D12E98E198C6BCAB122567930DD2466F2A5115E450A4C16274CED44C8",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": PREDECESSOR["44-book-isv.tex"],
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_571,
        "66399487B71DBA6FB8FC8DE8D91FC95F415D9974D602373D9F5E5C4E1EE401B1",
    ),
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}
EXPECTED_LOCATOR_BYTES = 1_307
EXPECTED_LOCATOR_SHA256 = (
    "A352DCF21C0C5511E9A32D8388630578D3860FCAF7232B20BC75AC9FDC50E779"
)
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
PREDECESSOR_CENSUS = Counter(
    {
        "sumand": 16,
        "sumandami": 1,
        "sumandov": 2,
        "sumandy": 7,
        "summand": 4,
        "summandov": 2,
        "summandy": 1,
        "sčestnikov": 1,
    }
)
SUCCESSOR_CENSUS = Counter(
    {"sumand": 20, "sumandami": 1, "sumandov": 5, "sumandy": 8}
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
    if not isinstance(manifest, list) or len(manifest) != 8:
        raise RuntimeError("candidate manifest absent or wrong cardinality")
    payload = canonical_bytes(manifest)
    if (len(payload), sha256(payload)) != (
        EXPECTED_LOCATOR_BYTES,
        EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("candidate manifest hash drift")
    before = Counter(item["before"] for item in manifest)
    if before != Counter(
        {"summand": 4, "summandov": 2, "summandy": 1, "sčestnikov": 1}
    ):
        raise RuntimeError("candidate form census drift")
    for item in manifest:
        expected = (
            "sumandov"
            if item["before"] == "sčestnikov"
            else "sumand" + item["before"][len("summand") :]
        )
        if item["after"] != expected:
            raise RuntimeError("candidate mapping drift")
    return manifest, {"path": str(RECEIPT_PATH), **pin(receipt_bytes)}


def shifted_for_successor(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    shrink = 0
    for item in sorted(items, key=lambda value: value["byte_offset0"]):
        adjusted = dict(item)
        adjusted["byte_offset0"] = item["byte_offset0"] - shrink
        result.append(adjusted)
        shrink += len(item["before"].encode("utf-8")) - len(
            item["after"].encode("utf-8")
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


def census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        for match in WORD_RE.finditer(text):
            token = match.group(0)
            if token == "sčestnikov" or token.startswith(("sumand", "summand")):
                result[token] += 1
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
        line_start = sum(len(value.encode("utf-8")) for value in lines[: item["line"] - 1])
        offset = line_start + len(line[:column0].encode("utf-8"))
        if offset != item["byte_offset0"]:
            raise RuntimeError("independent byte locator mismatch")
        for match in re.finditer("%", line):
            if match.start() < column0 and not escaped(line, match.start()):
                raise RuntimeError("target follows a TeX comment")
        prefix = line[:column0]
        dollars = sum(
            1
            for match in re.finditer(r"\$", prefix)
            if not escaped(prefix, match.start())
        )
        if dollars % 2:
            raise RuntimeError("target lies inside inline math")


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    math_delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
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
        "math": (
            len(math_delimiters),
            sha256("\n".join(math_delimiters).encode("utf-8")),
        ),
    }


def verify_authorities(predecessor: dict[str, bytes]) -> dict[str, Any]:
    german = authenticate(GERMAN_PATH, GERMAN_PIN, "German authority")
    german_line = german.decode("utf-8", errors="strict").splitlines()[10128]
    for needle in (
        "additiven Zerlegung der Restgruppe",
        "immer nur \\emph{endlich} viele Summanden auftreten",
    ):
        if needle not in german_line:
            raise RuntimeError("German line 10129 evidence drift")
    base_lines = predecessor["base-papers1-43-isv.tex"].decode("utf-8").splitlines()
    controls = {
        10959: "konečno mnogo sčestnikov",
        11321: "za dva sumandy",
        11350: "sogrupujemo sumandy",
        11352: "v \\(k\\) sumandov",
    }
    for line_no, needle in controls.items():
        if needle not in base_lines[line_no - 1]:
            raise RuntimeError(f"local terminology control drift at line {line_no}")
    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    dictionary_text = dictionary.decode("utf-8-sig", errors="strict")
    if ",suma,,f.,1,sum," not in dictionary_text:
        raise RuntimeError("official suma headword absent")
    for absent in (",sčestnik,", ",sumand,", ",summand,"):
        if absent in dictionary_text:
            raise RuntimeError(f"dictionary-silence premise drift: {absent}")
    return {
        "german_ed0015": {"path": str(GERMAN_PATH), **pin(german), "line": 10129},
        "official_dictionary": {"path": str(DICTIONARY_PATH), **pin(dictionary)},
        "local_interslavic_control_lines": [10959, 11321, 11350, 11352],
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

    if census(predecessor) != PREDECESSOR_CENSUS:
        raise RuntimeError("predecessor sumand-family census drift")
    if census(successor) != SUCCESSOR_CENSUS:
        raise RuntimeError("successor sumand-family census drift")
    verify_locations(predecessor, manifest)
    authorities = verify_authorities(predecessor)
    for filename in SOURCE_ORDER:
        if structural_signature(predecessor[filename].decode("utf-8")) != structural_signature(
            successor[filename].decode("utf-8")
        ):
            raise RuntimeError(f"protected TeX structure differs in {filename}")

    report = {
        "schema": "noether-isv-v021-sumand-family-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0008",
        "status": status,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authorities": authorities,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "predecessor_census": dict(sorted(census(predecessor).items())),
            "successor_census": dict(sorted(census(successor).items())),
            "successor_target_residue": sum(
                count
                for token, count in census(successor).items()
                if token == "sčestnikov" or token.startswith("summand")
            ),
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "line_column_byte_locators": True,
            "visible_prose_only": True,
            "utf8": True,
            "protected_tex_structure_equal": True,
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
