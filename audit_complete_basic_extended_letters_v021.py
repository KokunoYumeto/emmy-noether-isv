#!/usr/bin/env python3
"""Read-only reversible audit for the remaining basic-Latin extensions."""

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import types
from typing import Any
import zipfile


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
PREVIOUS_AUDIT_PATH = ROOT / "audit_complete_basic_consonants_v021.py"
PREVIOUS_AUDIT_PIN = (
    12_857,
    "133D20D5EF489210AF311B83C0FF9712D664B6DACA54C06E17BCA2D3992A6CAE",
)
SOURCE_PINS = {
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

# Line 80's general rule is "leave out the diacritic".  Lines 106 supplies
# the sanctioned alternatives è/ò, ľ, ť/ď, which therefore collapse to the
# same standard/basic letters.
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
UPPER_MAP = {key.upper(): value.upper() for key, value in LOWER_MAP.items()}
CHAR_MAP = {**LOWER_MAP, **UPPER_MAP}
OPTIONAL_CHARACTERS = tuple(CHAR_MAP)
EXPECTED_GLOBAL_CHARACTERS = Counter(
    {"ę": 1_716, "ų": 13, "ė": 2, "è": 4, "ľ": 5, "ť": 59, "ś": 3}
)
EXPECTED_GLOBAL_TOTAL = 1_802
EXPECTED_VISIBLE_TOKENS = 1_798
EXPECTED_PHYSICAL_LINES = 1_042
EXPECTED_VISIBLE_CHARACTERS = Counter(
    {"ę": 1_716, "ų": 13, "ė": 2, "ľ": 5, "ť": 59, "ś": 3}
)
EXPECTED_ROLES = Counter(
    {"visible_prose": 1_778, "visible_math_text": 20, "protected_foreign": 4}
)
EXPECTED_NONVISIBLE_ROLES = Counter({"protected_foreign": 4})
EXPECTED_NONVISIBLE_CHARACTERS = Counter({"è": 4})
EXPECTED_FILE_DISTRIBUTION = Counter(
    {
        "44-book-isv.tex": 72,
        "45-isv.tex": 7,
        "base-papers1-43-isv.tex": 1_715,
        "bib-isv.tex": 4,
    }
)
EXPECTED_MANIFEST_PIN = (
    291_190,
    "D41F4B6588FA74D999DE749D46DC507F27600651CCC7B00E9E1DC86005A64994",
)
EXPECTED_SUCCESSOR_PINS = {
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


def authenticate_module(path: Path, expected: tuple[int, str], name: str) -> Any:
    data = authenticate(path, expected, name)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


PREVIOUS = authenticate_module(
    PREVIOUS_AUDIT_PATH,
    PREVIOUS_AUDIT_PIN,
    "isv021_edit0012_extended_predecessor_audit",
)
BASE = PREVIOUS.BASE
BASE.SOURCE_PINS = SOURCE_PINS


def basic_form(token: str) -> str:
    return "".join(CHAR_MAP.get(character, character) for character in token)


def token_character_census(token: str) -> Counter[str]:
    return Counter(character for character in token if character in OPTIONAL_CHARACTERS)


def global_character_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for data in cohort.values():
        text = data.decode("utf-8", errors="strict")
        result.update(character for character in text if character in OPTIONAL_CHARACTERS)
        for sequence in ("t\u0301", "T\u0301", "d\u0301", "D\u0301"):
            if sequence in text:
                raise RuntimeError(f"combining-acute optional sequence requires explicit handling: {sequence!r}")
    return result


def scan(
    cohort: dict[str, bytes]
) -> tuple[
    list[dict[str, Any]],
    Counter[str],
    Counter[str],
    Counter[str],
    Counter[str],
    list[dict[str, Any]],
]:
    manifest: list[dict[str, Any]] = []
    characters: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    nonvisible_roles: Counter[str] = Counter()
    nonvisible_characters: Counter[str] = Counter()
    protected_inventory: list[dict[str, Any]] = []
    for filename in BASE.SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        starts = BASE.line_starts(text)
        segmenter = BASE.SEGMENTER.TexSegmenter(text)
        segments = segmenter.segment()
        if segmenter.unknown_argument_commands:
            raise RuntimeError(f"unknown argument commands in {filename}")
        for segment in segments:
            raw = text[segment.start : segment.end]
            for match in BASE.WORD_RE.finditer(raw):
                token = match.group(0)
                token_chars = token_character_census(token)
                if not token_chars:
                    continue
                roles[segment.role] += 1
                if segment.role not in BASE.VISIBLE_ROLES:
                    nonvisible_roles[segment.role] += 1
                    nonvisible_characters.update(token_chars)
                    scalar_offset0 = segment.start + match.start()
                    line_index = BASE.line_for_offset(starts, scalar_offset0)
                    protected_inventory.append(
                        {
                            "file": filename,
                            "line": line_index + 1,
                            "column": scalar_offset0 - starts[line_index] + 1,
                            "before": token,
                            "characters": dict(sorted(token_chars.items())),
                            "role": segment.role,
                        }
                    )
                    continue
                after = basic_form(token)
                if after == token:
                    raise RuntimeError("basic mapping made no change")
                if token_character_census(after):
                    raise RuntimeError("basic mapping left optional-letter residue")
                scalar_offset0 = segment.start + match.start()
                line_index = BASE.line_for_offset(starts, scalar_offset0)
                characters.update(token_chars)
                manifest.append(
                    {
                        "file": filename,
                        "line": line_index + 1,
                        "column": scalar_offset0 - starts[line_index] + 1,
                        "byte_offset0": len(text[:scalar_offset0].encode("utf-8")),
                        "before": token,
                        "after": after,
                        "characters": dict(sorted(token_chars.items())),
                        "role": segment.role,
                    }
                )
    return (
        manifest,
        characters,
        roles,
        nonvisible_roles,
        nonvisible_characters,
        protected_inventory,
    )


def visible_residue(cohort: dict[str, bytes]) -> dict[str, Any]:
    tokens = 0
    characters: Counter[str] = Counter()
    forms: Counter[str] = Counter()
    for filename in BASE.SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        segmenter = BASE.SEGMENTER.TexSegmenter(text)
        segments = segmenter.segment()
        if segmenter.unknown_argument_commands:
            raise RuntimeError(f"unknown argument commands in {filename}")
        for segment in segments:
            if segment.role not in BASE.VISIBLE_ROLES:
                continue
            raw = text[segment.start : segment.end]
            for match in BASE.WORD_RE.finditer(raw):
                token = match.group(0)
                token_chars = token_character_census(token)
                if not token_chars:
                    continue
                tokens += 1
                characters.update(token_chars)
                forms[token.casefold()] += 1
    return {
        "tokens": tokens,
        "characters": dict(sorted(characters.items())),
        "unique_forms": len(forms),
        "forms": dict(sorted(forms.items())),
    }


def authenticate_authority() -> dict[str, Any]:
    orthography = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "orthography")
    lines = orthography.decode("utf-8", errors="strict").splitlines()
    if "simply leaving out the diacritic" not in lines[79]:
        raise RuntimeError("general basic-letter rule drift")
    if "`ĺ` can be written as `ľ`" not in lines[105] or "`ė` and `ȯ`" not in lines[105]:
        raise RuntimeError("sanctioned alternative-letter rule drift")
    archive = authenticate(ARCHIVE_PATH, ARCHIVE_PIN, "upstream archive")
    with zipfile.ZipFile(ARCHIVE_PATH) as handle:
        snapshot = handle.read(SNAPSHOT_ENTRY)
        code = handle.read(CODE_ENTRY)
    if (len(snapshot), sha256(snapshot)) != SNAPSHOT_ENTRY_PIN:
        raise RuntimeError("snapshot entry drift")
    if (len(code), sha256(code)) != CODE_ENTRY_PIN:
        raise RuntimeError("dictionary implementation drift")
    code_lines = code.decode("utf-8", errors="strict").splitlines()
    required = {
        64: "['å', 'a']",
        65: "['ę', 'e']",
        66: "['ų', 'u']",
        67: "['ȯ', 'o']",
        68: "['ė', 'e']",
        69: "['ŕ', 'r']",
        70: "['ĺ', 'l']",
        71: "['ń', 'n']",
        72: "['ť', 't']",
        73: "['ď', 'd']",
        74: "['ś', 's']",
        75: "['ź', 'z']",
    }
    for line_number, needle in required.items():
        if needle not in code_lines[line_number - 1]:
            raise RuntimeError(f"dictionary implementation drift at line {line_number}")
    payload = json.loads(snapshot.decode("utf-8", errors="strict"))["isv-en"]
    evidence: Counter[str] = Counter()
    counterexamples: list[dict[str, Any]] = []
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
                    counterexamples.append(
                        {"id": record.get("id"), "old": old, "raw": raw, "basic": basic}
                    )
    if counterexamples:
        raise RuntimeError(f"generated basic-display counterexamples: {counterexamples[:3]}")
    return {
        "orthography": {"path": str(ORTHOGRAPHY_PATH), **pin(orthography), "control_lines": [80, 106]},
        "archive": {"path": str(ARCHIVE_PATH), **pin(archive)},
        "snapshot_entry": {"name": SNAPSHOT_ENTRY, **pin(snapshot)},
        "dictionary_implementation": {"name": CODE_ENTRY, **pin(code), "mapping_lines": sorted(required)},
        "generated_basic_evidence_characters": dict(sorted(evidence.items())),
    }


def build_report() -> dict[str, Any]:
    cohort = BASE.read_cohort()
    global_characters = global_character_census(cohort)
    if global_characters != EXPECTED_GLOBAL_CHARACTERS:
        raise RuntimeError(f"global optional-character census drift: {dict(global_characters)}")
    if sum(global_characters.values()) != EXPECTED_GLOBAL_TOTAL:
        raise RuntimeError("global optional-character total drift")
    (
        manifest,
        characters,
        roles,
        nonvisible,
        nonvisible_characters,
        protected_inventory,
    ) = scan(cohort)
    if len(manifest) != EXPECTED_VISIBLE_TOKENS:
        raise RuntimeError(f"visible token cardinality drift: {len(manifest)}")
    physical_lines = len({(item["file"], item["line"]) for item in manifest})
    if physical_lines != EXPECTED_PHYSICAL_LINES:
        raise RuntimeError(f"physical-line cardinality drift: {physical_lines}")
    if characters != EXPECTED_VISIBLE_CHARACTERS:
        raise RuntimeError(f"visible character census drift: {dict(characters)}")
    if roles != EXPECTED_ROLES:
        raise RuntimeError(f"role census drift: {dict(roles)}")
    if nonvisible != EXPECTED_NONVISIBLE_ROLES:
        raise RuntimeError(f"non-visible role drift: {dict(nonvisible)}")
    if nonvisible_characters != EXPECTED_NONVISIBLE_CHARACTERS:
        raise RuntimeError(
            f"non-visible character drift: {dict(nonvisible_characters)}"
        )
    distribution = Counter(item["file"] for item in manifest)
    if distribution != EXPECTED_FILE_DISTRIBUTION:
        raise RuntimeError(f"source distribution drift: {dict(distribution)}")
    outputs = BASE.project(cohort, manifest)
    observed_successor_pins = {
        name: (len(outputs[name]), sha256(outputs[name])) for name in BASE.SOURCE_ORDER
    }
    if observed_successor_pins != EXPECTED_SUCCESSOR_PINS:
        raise RuntimeError(f"projected successor pin drift: {observed_successor_pins}")
    residue = visible_residue(outputs)
    global_residue = global_character_census(outputs)
    manifest_bytes = BASE.canonical_bytes(manifest)
    observed_manifest_pin = (len(manifest_bytes), sha256(manifest_bytes))
    if observed_manifest_pin != EXPECTED_MANIFEST_PIN:
        raise RuntimeError(f"manifest pin drift: {observed_manifest_pin}")
    if residue["tokens"] or residue["characters"]:
        raise RuntimeError(f"projected visible optional-letter residue: {residue}")
    if global_residue != EXPECTED_NONVISIBLE_CHARACTERS:
        raise RuntimeError(f"projected global protected residue drift: {dict(global_residue)}")
    return {
        "schema": "noether-isv-v021-complete-basic-extended-letters-audit-v1",
        "edit_id": "ISV021-EDIT-0012",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in BASE.SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in BASE.SOURCE_ORDER},
        "coverage": {
            "tokens": len(manifest),
            "physical_lines": physical_lines,
            "characters": dict(sorted(characters.items())),
            "global_characters": dict(sorted(global_characters.items())),
            "roles": dict(sorted(roles.items())),
            "nonvisible_roles": dict(sorted(nonvisible.items())),
            "nonvisible_characters": dict(sorted(nonvisible_characters.items())),
            "protected_inventory": protected_inventory,
            "source_distribution": dict(sorted(distribution.items())),
            "projected_visible_residue": residue,
            "projected_global_residue": dict(sorted(global_residue.items())),
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": manifest,
        },
        "authority": authenticate_authority(),
        "policy": {
            "surface": "standard/basic reader-facing Latin",
            "rule": "Leave out the diacritic on every optional extended letter; sanctioned alternative glyphs è and ľ collapse with ė and ĺ to e and l.",
            "scope_boundary": "Only reader-visible local Interslavic word tokens are eligible. Protected TeX and foreign payloads remain excluded by the pinned v2 segmenter.",
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
    print(json.dumps(report, ensure_ascii=False, sort_keys=args.compact, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
