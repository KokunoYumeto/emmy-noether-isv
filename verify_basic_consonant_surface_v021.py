#!/usr/bin/env python3
"""Producer-independent predecessor/successor verifier for EDIT-0010-R2."""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
import zipfile


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
RECEIPT_PATH = (
    ROOT / "decision_records" / "ISV021-EDIT-0010-UNAPPLIED-CANDIDATE-RECEIPT-R2.json"
)
RECEIPT_PIN = (
    20_541,
    "1593BC6ACDE603BA8EAA26E5F31774F240441A3D07EC230D341F622C4D67D2AD",
)
REJECTED_R1_PATH = (
    ROOT / "decision_records" / "ISV021-EDIT-0010-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
REJECTED_R1_PIN = (
    34_939,
    "7223BC416806FF195C35BE8ECA9CD294160DC285AFAF467486C8E4DEA9118FFB",
)
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
ARCHIVE_PATH = DICTIONARY_PATH.parent / "upstream_repository_0fab0c5b4463118d46b1cdcd506926d8848052c9.zip"
ARCHIVE_PIN = (
    11_271_766,
    "E02AA89235E4A7B536F3D762126293A3E348319CA1B11CBF8D219A65D03172BE",
)
SNAPSHOT_ENTRY = (
    "interslavic-0fab0c5b4463118d46b1cdcd506926d8848052c9/"
    "src/services/dictionary-test/snapshot.json"
)
SNAPSHOT_ENTRY_PIN = (
    16_930_150,
    "DB40B9256BF257A0CEA44931A450C0B268BC81897CADEE9ECCD545FE0F4DEACC",
)
CODE_ENTRY = (
    "interslavic-0fab0c5b4463118d46b1cdcd506926d8848052c9/"
    "src/services/dictionary.ts"
)
CODE_ENTRY_PIN = (
    26_926,
    "60C09F2C2B3015033F1342BEA95FC48A1C36772F75880F669FB14C110577101D",
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
        "F8A278F67B87AE86C8F3CCE3F78EE32265986F0251EE8430F73BACCE20694E71",
    ),
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_613,
        "34540C032E966C54E44BEDCB45902161A978051F13A7ABA07CDA1925A418E594",
    ),
    "bib-isv.tex": PREDECESSOR["bib-isv.tex"],
}
EXPECTED_LOCATOR_BYTES = 7_322
EXPECTED_LOCATOR_SHA256 = (
    "6CC2C6ABDDCCE011BB3400056E13910D0C8D2A78927798674E0FEBAE4DE3B0AD"
)
VISIBLE_ROLES = {"visible_prose", "visible_math_text", "visible_metadata"}
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
WORD_MAP = {
    "dopušća": "dopušča",
    "dopušćajut": "dopuščajut",
    "dopušćati": "dopuščati",
    "skraćenja": "skračenja",
    "skraćeno": "skračeno",
    "vozvraća": "vozvrača",
    "vraćajemo": "vračajemo",
    "vraćajuči": "vračajuči",
    "sućstveno": "sučstveno",
    "sućstvene": "sučstvene",
    "sućstvena": "sučstvena",
    "sućstvenym": "sučstvenym",
}
EXPECTED_BEFORE = Counter(
    {
        "dopušća": 26,
        "dopušćajut": 6,
        "dopušćati": 1,
        "skraćenja": 1,
        "skraćeno": 1,
        "vozvraća": 1,
        "vraćajemo": 1,
        "vraćajuči": 1,
        "sućstveno": 1,
        "sućstvene": 1,
        "sućstvena": 1,
        "sućstvenym": 1,
    }
)
EXPECTED_SUCCESSOR = Counter(
    {
        "dopušča": 81,
        "dopuščajut": 27,
        "dopuščati": 1,
        "skračenja": 2,
        "skračeno": 7,
        "sučstvena": 4,
        "sučstvene": 1,
        "sučstveno": 37,
        "sučstvenym": 1,
        "vozvrača": 2,
        "vračajemo": 1,
        "vračajuči": 3,
    }
)
BASIC_ROWS = {
    "7208": ("dopušćati", "dopuščati"),
    "20859": ("dopušćati", "dopuščati"),
    "3139": ("skraćati", "skračati"),
    "953": ("skråćeńje", "skračenje"),
    "17039": ("skråćeny", "skračeny"),
    "1839": ("vraćati", "vračati"),
    "22658": ("vraćati sę", "vračati se"),
    "22646": ("vȯzvraćati", "vozvračati"),
    "18360": ("vȯzvråćeńje", "vozvračenje"),
    "20192": ("sųćstveno", "sučstveno"),
    "20193": ("sųćstveny", "sučstveny"),
}
RETURN_CONTEXTS = {
    15099: "vozvraća se k pojedinačno homogenym invariantam",
    20089: "vraćajemo se k direktnomu prědstavjenju",
    22686: "Vraćajuči se k cělym čislam",
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
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "R2 candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt status drift")
    if receipt.get("revision") != "R2":
        raise RuntimeError("candidate revision drift")
    manifest = receipt.get("locator_manifest", {}).get("value")
    if not isinstance(manifest, list) or len(manifest) != 42:
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
        "environments": (len(environments), sha256("\n".join(environments).encode("utf-8"))),
        "labels": (len(labels), sha256("\n".join(labels).encode("utf-8"))),
        "math": (len(math), sha256("\n".join(math).encode("utf-8"))),
    }


def verify_authority(predecessor: dict[str, bytes]) -> dict[str, Any]:
    orthography = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "orthography")
    orth_lines = orthography.decode("utf-8", errors="strict").splitlines()
    if "standard orthography should be replaced with `č` and `dž`" not in orth_lines[79]:
        raise RuntimeError("orthography ć-to-č control drift")
    raw_dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary source")
    found: set[str] = set()
    with DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in BASIC_ROWS:
                found.add(row["id"])
    if found != set(BASIC_ROWS):
        raise RuntimeError("dictionary row-set drift")
    authenticate(ARCHIVE_PATH, ARCHIVE_PIN, "upstream archive")
    with zipfile.ZipFile(ARCHIVE_PATH) as handle:
        snapshot = handle.read(SNAPSHOT_ENTRY)
        code = handle.read(CODE_ENTRY)
    if (len(snapshot), sha256(snapshot)) != SNAPSHOT_ENTRY_PIN:
        raise RuntimeError("snapshot entry drift")
    if (len(code), sha256(code)) != CODE_ENTRY_PIN:
        raise RuntimeError("dictionary implementation drift")
    code_lines = code.decode("utf-8", errors="strict").splitlines()
    if "['ć', 'č']" not in code_lines[57]:
        raise RuntimeError("dictionary implementation mapping drift")
    payload = json.loads(snapshot.decode("utf-8", errors="strict"))["isv-en"]
    for row_id, (etymological, basic) in BASIC_ROWS.items():
        records = [record for record in payload[row_id] if record.get("id") == row_id]
        if len(records) != 1:
            raise RuntimeError("snapshot row identity drift")
        if records[0].get("isv") != etymological or records[0].get("original") != basic:
            raise RuntimeError(f"snapshot basic display drift at {row_id}")
    rejected_r1 = authenticate(REJECTED_R1_PATH, REJECTED_R1_PIN, "rejected R1")
    lines = predecessor["base-papers1-43-isv.tex"].decode("utf-8").splitlines()
    for line_number, needle in RETURN_CONTEXTS.items():
        if needle not in lines[line_number - 1]:
            raise RuntimeError(f"return-sense context drift at line {line_number}")
    return {
        "orthography": {"path": str(ORTHOGRAPHY_PATH), **pin(orthography), "control_line": 80},
        "raw_dictionary": {"path": str(DICTIONARY_PATH), **pin(raw_dictionary)},
        "snapshot_entry": {"name": SNAPSHOT_ENTRY, **pin(snapshot)},
        "dictionary_implementation": {"name": CODE_ENTRY, **pin(code), "mapping_line": 58},
        "rejected_r1": {"path": str(REJECTED_R1_PATH), **pin(rejected_r1)},
        "return_sense_control_lines": sorted(RETURN_CONTEXTS),
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
    verify_locations(predecessor, manifest)
    authority = verify_authority(predecessor)
    for filename in SOURCE_ORDER:
        if structural_signature(predecessor[filename].decode("utf-8")) != structural_signature(
            successor[filename].decode("utf-8")
        ):
            raise RuntimeError(f"protected TeX structure differs in {filename}")
    report = {
        "schema": "noether-isv-v021-basic-consonant-surface-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0010",
        "revision": "R2",
        "status": status,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authority": authority,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "source_distribution": dict(sorted(Counter(item["file"] for item in manifest).items())),
            "predecessor_target_census": dict(sorted(old_census.items())),
            "successor_relevant_census": dict(sorted(new_census.items())),
            "successor_target_residue": 0,
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "line_column_byte_locators": True,
            "comment_and_inline_math_boundaries": True,
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
