#!/usr/bin/env python3
"""Producer-independent predecessor/successor verifier for EDIT-0011."""

from __future__ import annotations

from collections import Counter
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
    ROOT / "decision_records" / "ISV021-EDIT-0011-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    435_463,
    "450017924F7680B61379E66F01AB94BD5280E04A45672B8B6FA251CE569F0F13",
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
ARCHIVE_PATH = Path(
    r"<WORKSPACE_ROOT>\01_methodology"
    r"\claude_fable_program\data"
    r"\interslavic_dictionary_official_snapshot_20260816"
    r"\upstream_repository_0fab0c5b4463118d46b1cdcd506926d8848052c9.zip"
)
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
        "F8A278F67B87AE86C8F3CCE3F78EE32265986F0251EE8430F73BACCE20694E71",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_613,
        "34540C032E966C54E44BEDCB45902161A978051F13A7ABA07CDA1925A418E594",
    ),
    "bib-isv.tex": (
        10_020,
        "7A45365DC7C9408CF3D50FDAA4C35081E032CC6F07D73A9954D3B1DDF18C9EC7",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": (
        168_456,
        "DAF592E5F9D92186B1B7E8E7D64288D04053CE3C1FE10A48C96082F6E52F8103",
    ),
    "45-isv.tex": (
        26_043,
        "FEF628A7947285FAE15C7F5724BD3C87F027911D2C36E16A546CCEB69AF5CC33",
    ),
    "base-papers1-43-isv.tex": (
        1_894_798,
        "03995C2AC0455516F370C9752903D9826B8B1CF6FA4981BEEF90B40AC34CD6FE",
    ),
    "bib-isv.tex": (
        10_020,
        "FFA7F9FD323A7C0B134986EDFE0E1484C04C61ECA576B60DB6E2C2B70B9778E3",
    ),
}
EXPECTED_LOCATOR_PIN = (
    276_577,
    "144A137BC54C8A9FC79D963982DD425526DDC2C7D1B85E78F99E69D4931CEC12",
)
EXPECTED_CHARACTERS = Counter({"ć": 1_381, "đ": 218})
EXPECTED_ROLES = Counter({"visible_prose": 1_597, "visible_math_text": 2})
EXPECTED_DISTRIBUTION = Counter(
    {
        "44-book-isv.tex": 133,
        "45-isv.tex": 40,
        "base-papers1-43-isv.tex": 1_422,
        "bib-isv.tex": 4,
    }
)
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


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


def expected_after(before: str) -> str:
    return (
        before.replace("ć", "č")
        .replace("Ć", "Č")
        .replace("đ", "dž")
        .replace("Đ", "Dž")
    )


def load_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt status drift")
    if receipt.get("edit_id") != "ISV021-EDIT-0011":
        raise RuntimeError("candidate edit identity drift")
    manifest = receipt.get("locator_manifest", {}).get("value")
    if not isinstance(manifest, list) or len(manifest) != 1_599:
        raise RuntimeError("candidate manifest cardinality drift")
    payload = canonical_bytes(manifest)
    if (len(payload), sha256(payload)) != EXPECTED_LOCATOR_PIN:
        raise RuntimeError("candidate manifest pin drift")
    characters: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    distribution: Counter[str] = Counter()
    for item in manifest:
        before = item.get("before")
        after = item.get("after")
        if not isinstance(before, str) or not isinstance(after, str):
            raise RuntimeError("non-string manifest payload")
        c_count = before.count("ć") + before.count("Ć")
        d_count = before.count("đ") + before.count("Đ")
        if c_count + d_count != 1 or after != expected_after(before):
            raise RuntimeError("candidate scalar mapping drift")
        if "ć" in after.casefold() or "đ" in after.casefold():
            raise RuntimeError("candidate after-value retains optional consonant")
        expected_family = "standard_caron_c" if c_count else "standard_dz_digraph"
        if item.get("family") != expected_family:
            raise RuntimeError("candidate family tag drift")
        if item.get("role") not in {"visible_prose", "visible_math_text"}:
            raise RuntimeError("candidate role drift")
        if item.get("file") not in SOURCE_ORDER:
            raise RuntimeError("candidate source identity drift")
        characters["ć"] += c_count
        characters["đ"] += d_count
        roles[item["role"]] += 1
        distribution[item["file"]] += 1
    if characters != EXPECTED_CHARACTERS:
        raise RuntimeError(f"candidate character census drift: {dict(characters)}")
    if roles != EXPECTED_ROLES:
        raise RuntimeError(f"candidate role census drift: {dict(roles)}")
    if distribution != EXPECTED_DISTRIBUTION:
        raise RuntimeError(f"candidate distribution drift: {dict(distribution)}")
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


def escaped(text: str, index: int) -> bool:
    count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        count += 1
        cursor -= 1
    return bool(count % 2)


def verify_locations(predecessor: dict[str, bytes], manifest: list[dict[str, Any]]) -> None:
    math_text_sites = 0
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
            1
            for match in re.finditer(r"\$", prefix)
            if not escaped(prefix, match.start())
        )
        if item["role"] == "visible_math_text":
            math_text_sites += 1
            if not re.search(r"\\(?:text|hbox)\{[^{}]*$", prefix):
                raise RuntimeError("visible-math-text boundary mismatch")
        elif dollars % 2:
            raise RuntimeError("visible prose target lies inside inline math")
    if math_text_sites != 2:
        raise RuntimeError("visible-math-text cardinality drift")


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


def optional_character_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for data in cohort.values():
        text = data.decode("utf-8", errors="strict")
        for character in ("ć", "Ć", "đ", "Đ"):
            result[character] += text.count(character)
    return result


def verify_authority() -> dict[str, Any]:
    orthography = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "orthography")
    orth_lines = orthography.decode("utf-8", errors="strict").splitlines()
    if "standard orthography should be replaced with `č` and `dž`" not in orth_lines[79]:
        raise RuntimeError("orthography control line drift")
    archive = authenticate(ARCHIVE_PATH, ARCHIVE_PIN, "upstream archive")
    with zipfile.ZipFile(ARCHIVE_PATH) as handle:
        snapshot = handle.read(SNAPSHOT_ENTRY)
        code = handle.read(CODE_ENTRY)
    if (len(snapshot), sha256(snapshot)) != SNAPSHOT_ENTRY_PIN:
        raise RuntimeError("snapshot entry drift")
    if (len(code), sha256(code)) != CODE_ENTRY_PIN:
        raise RuntimeError("dictionary implementation drift")
    code_lines = code.decode("utf-8", errors="strict").splitlines()
    if "['đ', 'dž']" not in code_lines[56] or "['ć', 'č']" not in code_lines[57]:
        raise RuntimeError("dictionary implementation mapping drift")
    payload = json.loads(snapshot.decode("utf-8", errors="strict"))["isv-en"]
    checked = Counter()
    for records in payload.values():
        for record in records:
            raw = record.get("isv")
            basic = record.get("original")
            if not isinstance(raw, str) or not isinstance(basic, str):
                continue
            for old, new in (("ć", "č"), ("đ", "dž")):
                count = raw.count(old)
                if not count:
                    continue
                checked[old] += count
                if old in basic or basic.count(new) < count:
                    raise RuntimeError("snapshot basic-display mapping counterexample")
    if checked["ć"] < 496 or checked["đ"] < 210:
        raise RuntimeError(f"authority evidence census unexpectedly small: {dict(checked)}")
    return {
        "orthography": {
            "path": str(ORTHOGRAPHY_PATH),
            **pin(orthography),
            "control_line": 80,
        },
        "archive": {"path": str(ARCHIVE_PATH), **pin(archive)},
        "snapshot_entry": {"name": SNAPSHOT_ENTRY, **pin(snapshot)},
        "dictionary_implementation": {
            "name": CODE_ENTRY,
            **pin(code),
            "mapping_lines": [57, 58],
        },
        "dictionary_evidence_characters": dict(sorted(checked.items())),
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
    predecessor_optional = optional_character_census(predecessor)
    expected_optional = Counter({"ć": 1_381, "đ": 218, "Ć": 0, "Đ": 0})
    if predecessor_optional != expected_optional:
        raise RuntimeError(f"predecessor optional-character drift: {dict(predecessor_optional)}")
    successor_optional = optional_character_census(successor)
    if any(successor_optional.values()):
        raise RuntimeError(f"successor optional-character residue: {dict(successor_optional)}")
    verify_locations(predecessor, manifest)
    authority = verify_authority()
    for filename in SOURCE_ORDER:
        before = predecessor[filename].decode("utf-8")
        after = successor[filename].decode("utf-8")
        if structural_signature(before) != structural_signature(after):
            raise RuntimeError(f"protected TeX structure differs in {filename}")
    report = {
        "schema": "noether-isv-v021-complete-basic-consonants-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0011",
        "status": status,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authority": authority,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "characters": dict(sorted(EXPECTED_CHARACTERS.items())),
            "roles": dict(sorted(EXPECTED_ROLES.items())),
            "source_distribution": dict(sorted(EXPECTED_DISTRIBUTION.items())),
            "successor_optional_consonant_residue": 0,
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "line_column_byte_locators": True,
            "comment_and_math_text_boundaries": True,
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
