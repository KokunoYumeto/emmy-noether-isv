#!/usr/bin/env python3
"""Producer-independent predecessor/successor verifier for EDIT-0012."""

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
    ROOT / "decision_records" / "ISV021-EDIT-0012-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    504_696,
    "D9519C0677BA506F421C0E44F4EC5850A290D1C0153B021E0BBF483371A88345",
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
SUCCESSOR = {
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
EXPECTED_LOCATOR_PIN = (
    291_190,
    "D41F4B6588FA74D999DE749D46DC507F27600651CCC7B00E9E1DC86005A64994",
)
LOWER_MAP = {
    "å": "a",
    "ę": "e",
    "ų": "u",
    "ȯ": "o",
    "ė": "e",
    "è": "e",
    "ŕ": "r",
    "ĺ": "l",
    "ľ": "l",
    "ń": "n",
    "ť": "t",
    "ď": "d",
    "ś": "s",
    "ź": "z",
}
CHAR_MAP = {**LOWER_MAP, **{key.upper(): value.upper() for key, value in LOWER_MAP.items()}}
OPTIONAL_CHARACTERS = tuple(CHAR_MAP)
EXPECTED_VISIBLE_CHARACTERS = Counter(
    {"ę": 1_716, "ų": 13, "ė": 2, "ľ": 5, "ť": 59, "ś": 3}
)
EXPECTED_PREDECESSOR_GLOBAL = Counter({**EXPECTED_VISIBLE_CHARACTERS, "è": 4})
EXPECTED_SUCCESSOR_GLOBAL = Counter({"è": 4})
EXPECTED_ROLES = Counter({"visible_prose": 1_778, "visible_math_text": 20})
EXPECTED_DISTRIBUTION = Counter(
    {
        "44-book-isv.tex": 72,
        "45-isv.tex": 7,
        "base-papers1-43-isv.tex": 1_715,
        "bib-isv.tex": 4,
    }
)
PROTECTED_FOREIGN = (
    ("base-papers1-43-isv.tex", 6753, 1232, "Liège"),
    ("base-papers1-43-isv.tex", 10729, 1083, "système"),
    ("base-papers1-43-isv.tex", 24453, 119, "algèbre"),
    ("bib-isv.tex", 220, 90, "Cavaillès"),
)


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
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    for data in cohort.values():
        data.decode("utf-8", errors="strict")
    return cohort


def expected_after(before: str) -> str:
    return "".join(CHAR_MAP.get(character, character) for character in before)


def token_characters(token: str) -> Counter[str]:
    return Counter(character for character in token if character in OPTIONAL_CHARACTERS)


def load_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt status drift")
    if receipt.get("edit_id") != "ISV021-EDIT-0012":
        raise RuntimeError("candidate edit identity drift")
    manifest = receipt.get("locator_manifest", {}).get("value")
    if not isinstance(manifest, list) or len(manifest) != 1_798:
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
        found = token_characters(before)
        if sum(found.values()) != 1 or found.get("è"):
            raise RuntimeError("candidate token character boundary drift")
        if after != expected_after(before) or token_characters(after):
            raise RuntimeError("candidate scalar mapping drift")
        if item.get("characters") != dict(sorted(found.items())):
            raise RuntimeError("candidate character tag drift")
        if item.get("role") not in {"visible_prose", "visible_math_text"}:
            raise RuntimeError("candidate role drift")
        if item.get("file") not in SOURCE_ORDER:
            raise RuntimeError("candidate source identity drift")
        characters.update(found)
        roles[item["role"]] += 1
        distribution[item["file"]] += 1
    if characters != EXPECTED_VISIBLE_CHARACTERS:
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
        delta += len(item["after"].encode("utf-8")) - len(item["before"].encode("utf-8"))
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
                raise RuntimeError(f"payload mismatch at {filename}:{item['line']}:{item['column']}")
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
        text = predecessor[item["file"]].decode("utf-8", errors="strict")
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
        dollars = sum(1 for match in re.finditer(r"\$", prefix) if not escaped(prefix, match.start()))
        if item["role"] == "visible_math_text":
            math_text_sites += 1
            if not re.search(r"\\(?:text|hbox)\{[^{}]*$", prefix):
                raise RuntimeError("visible-math-text boundary mismatch")
        elif dollars % 2:
            raise RuntimeError("visible prose target lies inside inline math")
    if math_text_sites != 20:
        raise RuntimeError("visible-math-text cardinality drift")


def inside_foreign(line: str, column0: int) -> bool:
    starts = [match.end() for match in re.finditer(r"\\foreign\{", line[:column0])]
    for start in reversed(starts):
        depth = 1
        for character in line[start:column0]:
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
        if depth > 0:
            return True
    return False


def verify_protected_foreign(cohort: dict[str, bytes]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for filename, line_number, column, token in PROTECTED_FOREIGN:
        line = cohort[filename].decode("utf-8").splitlines()[line_number - 1]
        column0 = column - 1
        if line[column0 : column0 + len(token)] != token:
            raise RuntimeError("protected foreign locator drift")
        if not inside_foreign(line, column0):
            raise RuntimeError("protected token is not inside foreign custody")
        result.append({"file": filename, "line": line_number, "column": column, "token": token})
    return result


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


def global_optional_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for data in cohort.values():
        text = data.decode("utf-8", errors="strict")
        result.update(character for character in text if character in OPTIONAL_CHARACTERS)
        if any(sequence in text for sequence in ("t\u0301", "T\u0301", "d\u0301", "D\u0301")):
            raise RuntimeError("unhandled combining-acute optional sequence")
    return result


def verify_authority() -> dict[str, Any]:
    orthography = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "orthography")
    lines = orthography.decode("utf-8", errors="strict").splitlines()
    if "simply leaving out the diacritic" not in lines[79]:
        raise RuntimeError("general basic-letter rule drift")
    if "`ĺ` can be written as `ľ`" not in lines[105] or "`ė` and `ȯ`" not in lines[105]:
        raise RuntimeError("alternative-letter control drift")
    archive = authenticate(ARCHIVE_PATH, ARCHIVE_PIN, "upstream archive")
    with zipfile.ZipFile(ARCHIVE_PATH) as handle:
        snapshot = handle.read(SNAPSHOT_ENTRY)
        code = handle.read(CODE_ENTRY)
    if (len(snapshot), sha256(snapshot)) != SNAPSHOT_ENTRY_PIN:
        raise RuntimeError("snapshot entry drift")
    if (len(code), sha256(code)) != CODE_ENTRY_PIN:
        raise RuntimeError("dictionary implementation drift")
    code_lines = code.decode("utf-8", errors="strict").splitlines()
    required = {64:"['å', 'a']",65:"['ę', 'e']",66:"['ų', 'u']",67:"['ȯ', 'o']",68:"['ė', 'e']",69:"['ŕ', 'r']",70:"['ĺ', 'l']",71:"['ń', 'n']",72:"['ť', 't']",73:"['ď', 'd']",74:"['ś', 's']",75:"['ź', 'z']"}
    for line_number, needle in required.items():
        if needle not in code_lines[line_number - 1]:
            raise RuntimeError(f"dictionary implementation drift at {line_number}")
    payload = json.loads(snapshot.decode("utf-8", errors="strict"))["isv-en"]
    evidence: Counter[str] = Counter()
    for records in payload.values():
        for record in records:
            raw = record.get("isv")
            basic = record.get("original")
            if not isinstance(raw, str) or not isinstance(basic, str):
                continue
            for old, new in LOWER_MAP.items():
                if old in {"è", "ľ"}:
                    continue
                count = raw.count(old)
                if not count:
                    continue
                evidence[old] += count
                if old in basic or basic.count(new) < count:
                    raise RuntimeError("generated basic-display counterexample")
    return {
        "orthography": {"path": str(ORTHOGRAPHY_PATH), **pin(orthography), "control_lines": [80, 106]},
        "archive": {"path": str(ARCHIVE_PATH), **pin(archive)},
        "snapshot_entry": {"name": SNAPSHOT_ENTRY, **pin(snapshot)},
        "dictionary_implementation": {"name": CODE_ENTRY, **pin(code), "mapping_lines": sorted(required)},
        "generated_basic_evidence_characters": dict(sorted(evidence.items())),
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
    predecessor_global = global_optional_census(predecessor)
    successor_global = global_optional_census(successor)
    if predecessor_global != EXPECTED_PREDECESSOR_GLOBAL:
        raise RuntimeError(f"predecessor optional census drift: {dict(predecessor_global)}")
    if successor_global != EXPECTED_SUCCESSOR_GLOBAL:
        raise RuntimeError(f"successor protected residue drift: {dict(successor_global)}")
    verify_locations(predecessor, manifest)
    protected = verify_protected_foreign(predecessor)
    if verify_protected_foreign(successor) != protected:
        raise RuntimeError("protected foreign inventory changed")
    authority = verify_authority()
    for filename in SOURCE_ORDER:
        before = predecessor[filename].decode("utf-8")
        after = successor[filename].decode("utf-8")
        if structural_signature(before) != structural_signature(after):
            raise RuntimeError(f"protected TeX structure differs in {filename}")
    report = {
        "schema": "noether-isv-v021-complete-basic-extended-letters-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0012",
        "status": status,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authority": authority,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "characters": dict(sorted(EXPECTED_VISIBLE_CHARACTERS.items())),
            "roles": dict(sorted(EXPECTED_ROLES.items())),
            "source_distribution": dict(sorted(EXPECTED_DISTRIBUTION.items())),
            "protected_foreign": protected,
            "successor_visible_optional_residue": 0,
            "successor_global_optional_residue": dict(sorted(successor_global.items())),
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "line_column_byte_locators": True,
            "comment_and_math_text_boundaries": True,
            "protected_foreign_unchanged": True,
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
