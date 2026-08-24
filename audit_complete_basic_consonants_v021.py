#!/usr/bin/env python3
"""Read-only reversible audit for ISV021-EDIT-0011.

The edition declares a standard/basic reader-facing Latin surface.  Official
orthography requires optional etymological ć and đ to be represented as č and
dž respectively.  This audit enumerates every remaining reader-visible word
token containing either optional consonant, constructs the exact scalar
projection, authenticates the official rule and generated dictionary
implementation, and proves reversible UTF-8 and protected-TeX preservation.
"""

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
PREVIOUS_AUDIT_PATH = ROOT / "audit_basic_consonant_surface_v021.py"
PREVIOUS_AUDIT_PIN = (
    16_244,
    "D7B1D7186603DED07B17DCDAE5B6BF83916F6C57D763A11FDDA2259CE6CAA433",
)
SOURCE_PINS = {
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
EXPECTED_SITES = 1_599
EXPECTED_PHYSICAL_LINES = 1_195
EXPECTED_CHARACTERS = Counter({"ć": 1_381, "đ": 218})
EXPECTED_ROLES = Counter({"visible_prose": 1_597, "visible_math_text": 2})
EXPECTED_FILE_DISTRIBUTION = Counter(
    {
        "44-book-isv.tex": 133,
        "45-isv.tex": 40,
        "base-papers1-43-isv.tex": 1_422,
        "bib-isv.tex": 4,
    }
)
EXPECTED_MANIFEST_PIN = (
    276_577,
    "144A137BC54C8A9FC79D963982DD425526DDC2C7D1B85E78F99E69D4931CEC12",
)
EXPECTED_SUCCESSOR_PINS = {
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate_module(path: Path, expected: tuple[int, str], name: str) -> Any:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"{name} pin drift: {observed}")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


PREVIOUS = authenticate_module(
    PREVIOUS_AUDIT_PATH,
    PREVIOUS_AUDIT_PIN,
    "isv021_edit0011_basic_consonant_predecessor_audit",
)
BASE = PREVIOUS.BASE
BASE.SOURCE_PINS = SOURCE_PINS


def basic_form(token: str) -> str:
    """Apply the two official standard-consonant mappings, preserving case."""
    return (
        token.replace("ć", "č")
        .replace("Ć", "Č")
        .replace("đ", "dž")
        .replace("Đ", "Dž")
    )


def scan(
    cohort: dict[str, bytes]
) -> tuple[list[dict[str, Any]], Counter[str], Counter[str], Counter[str]]:
    manifest: list[dict[str, Any]] = []
    character_census: Counter[str] = Counter()
    role_census: Counter[str] = Counter()
    nonvisible_roles: Counter[str] = Counter()
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
                chars = Counter({"ć": token.count("ć"), "đ": token.count("đ")})
                chars += Counter({"ć": token.count("Ć"), "đ": token.count("Đ")})
                if not sum(chars.values()):
                    continue
                role_census[segment.role] += 1
                if segment.role not in BASE.VISIBLE_ROLES:
                    nonvisible_roles[segment.role] += 1
                    continue
                after = basic_form(token)
                if after == token:
                    raise RuntimeError("basic mapping made no change")
                if "ć" in after.casefold() or "đ" in after.casefold():
                    raise RuntimeError("basic mapping left optional-consonant residue")
                scalar_offset0 = segment.start + match.start()
                line_index = BASE.line_for_offset(starts, scalar_offset0)
                character_census.update(chars)
                manifest.append(
                    {
                        "file": filename,
                        "line": line_index + 1,
                        "column": scalar_offset0 - starts[line_index] + 1,
                        "byte_offset0": len(text[:scalar_offset0].encode("utf-8")),
                        "before": token,
                        "after": after,
                        "family": "standard_caron_c" if chars["ć"] else "standard_dz_digraph",
                        "role": segment.role,
                    }
                )
    return manifest, character_census, role_census, nonvisible_roles


def visible_optional_census(cohort: dict[str, bytes]) -> dict[str, Any]:
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
                c_count = token.casefold().count("ć")
                d_count = token.casefold().count("đ")
                if not c_count and not d_count:
                    continue
                tokens += 1
                characters["ć"] += c_count
                characters["đ"] += d_count
                forms[token.casefold()] += 1
    return {
        "tokens": tokens,
        "characters": dict(sorted(characters.items())),
        "unique_forms": len(forms),
        "forms": dict(sorted(forms.items())),
    }


def module_receipt() -> dict[str, Any]:
    data = PREVIOUS_AUDIT_PATH.read_bytes()
    if (len(data), sha256(data)) != PREVIOUS_AUDIT_PIN:
        raise RuntimeError("previous audit pin drift")
    return {"path": str(PREVIOUS_AUDIT_PATH), **pin(data)}


def build_report() -> dict[str, Any]:
    cohort = BASE.read_cohort()
    manifest, characters, roles, nonvisible = scan(cohort)
    if len(manifest) != EXPECTED_SITES:
        raise RuntimeError(f"site cardinality drift: {len(manifest)}")
    physical_lines = len({(item["file"], item["line"]) for item in manifest})
    if physical_lines != EXPECTED_PHYSICAL_LINES:
        raise RuntimeError(f"physical-line cardinality drift: {physical_lines}")
    if characters != EXPECTED_CHARACTERS:
        raise RuntimeError(f"character census drift: {dict(characters)}")
    if roles != EXPECTED_ROLES:
        raise RuntimeError(f"role census drift: {dict(roles)}")
    if nonvisible:
        raise RuntimeError(f"optional consonants in protected roles: {dict(nonvisible)}")
    distribution = Counter(item["file"] for item in manifest)
    if distribution != EXPECTED_FILE_DISTRIBUTION:
        raise RuntimeError(f"source distribution drift: {dict(distribution)}")
    family_census = Counter(item["family"] for item in manifest)
    if family_census != Counter(
        {"standard_caron_c": 1_381, "standard_dz_digraph": 218}
    ):
        raise RuntimeError(f"family census drift: {dict(family_census)}")
    outputs = BASE.project(cohort, manifest)
    observed_successor_pins = {
        name: (len(outputs[name]), sha256(outputs[name])) for name in BASE.SOURCE_ORDER
    }
    if observed_successor_pins != EXPECTED_SUCCESSOR_PINS:
        raise RuntimeError(f"projected successor pin drift: {observed_successor_pins}")
    residue = visible_optional_census(outputs)
    if residue["tokens"] or any(residue["characters"].values()):
        raise RuntimeError(f"projected optional-consonant residue: {residue}")
    manifest_bytes = BASE.canonical_bytes(manifest)
    observed_manifest_pin = (len(manifest_bytes), sha256(manifest_bytes))
    if observed_manifest_pin != EXPECTED_MANIFEST_PIN:
        raise RuntimeError(f"manifest pin drift: {observed_manifest_pin}")
    return {
        "schema": "noether-isv-v021-complete-basic-consonants-audit-v1",
        "edit_id": "ISV021-EDIT-0011",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in BASE.SOURCE_ORDER},
        "projected_successor": {
            name: pin(outputs[name]) for name in BASE.SOURCE_ORDER
        },
        "coverage": {
            "sites": len(manifest),
            "physical_lines": physical_lines,
            "characters": dict(sorted(characters.items())),
            "families": dict(sorted(family_census.items())),
            "roles": dict(sorted(roles.items())),
            "source_distribution": dict(sorted(distribution.items())),
            "projected_visible_optional_consonant_residue": residue,
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": manifest,
        },
        "authority": {
            "official_orthography": PREVIOUS.authenticate_orthography(),
            "official_generated_basic_display": PREVIOUS.authenticate_basic_display(),
            "raw_etymological_source_sheet": PREVIOUS.authenticate_raw_source_rows(),
        },
        "policy": {
            "surface": "standard/basic reader-facing Latin",
            "rule": "Every visible ISV ć becomes č and every visible ISV đ becomes dž. The two transformations are exact official standard-orthography rules, not corpus-frequency guesses.",
            "scope_boundary": "Only reader-visible ISV word tokens are eligible. TeX commands, comments, math syntax, foreign spans, identifiers, and protected source payloads are excluded by the pinned v2 segmenter; this cohort contains zero optional-consonant token in a non-visible role.",
            "prior_decisions": "EDIT0011 supersedes only the spelling-layer subdecisions that introduced or preserved visible ć/đ on a claimed basic surface. It retains their semantic and lexical decisions and preserves all adverse history.",
        },
        "validation": {
            "exact_reverse": True,
            "utf8": True,
            "v2_visible_roles_only": True,
            "unknown_argument_commands": 0,
            "protected_tex_structure_equal": True,
            "source_writes": 0,
        },
        "tools": {"authenticated_predecessor_audit": module_receipt()},
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
