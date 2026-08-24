#!/usr/bin/env python3
"""Read-only reversible audit for ISV021-EDIT-0010.

The candidate aligns three residual consonant families with direct official
dictionary headwords: dopušćati, skraćati/skråćeńje, and
vraćati/vȯzvraćati.  It deliberately leaves the sųćstvėny family
unchanged because the official headword and its own usage example expose a
real ć/č variant split.  The audit authenticates the exact EDIT-0009 source
cohort, changes no source bytes, and proves an exact reversible projection
through the pinned v2 TeX segmenter.
"""

from __future__ import annotations

from collections import Counter
import argparse
import csv
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
BASE_AUDIT_PATH = ROOT / "audit_official_vowel_families_v021.py"
BASE_AUDIT_PIN = (
    14_950,
    "E4BCFE2C2B02D30C8A3403CACB49B1C33638B86F9939A6B34856273C49F5E6F2",
)
SOURCE_PINS = {
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


BASE = authenticate_module(
    BASE_AUDIT_PATH, BASE_AUDIT_PIN, "isv021_edit0010_vowel_audit_base"
)
BASE.SOURCE_PINS = SOURCE_PINS

TARGETS: dict[str, tuple[str, str]] = {
    "dopušča": ("dopušća", "official_dopuscati"),
    "dopuščajut": ("dopušćajut", "official_dopuscati"),
    "dopuščaje": ("dopušćaje", "official_dopuscati"),
    "dopuščanju": ("dopušćanju", "official_dopuscati"),
    "skračeno": ("skraćeno", "official_skracati"),
    "skračajuče": ("skraćajuče", "official_skracati"),
    "skračene": ("skraćene", "official_skracati"),
    "skračenja": ("skraćenja", "official_skracati"),
    "skračenom": ("skraćenom", "official_skracati"),
    "skračivati": ("skraćivati", "official_skracati"),
    "skračujuče": ("skraćujuče", "official_skracati"),
    "vračajuči": ("vraćajuči", "official_vracati_return"),
    "vozvrača": ("vozvraća", "official_vracati_return"),
    "vozvračanje": ("vozvraćanje", "official_vracati_return"),
    "vozvračenje": ("vozvraćenje", "official_vracati_return"),
    "vozvračenju": ("vozvraćenju", "official_vracati_return"),
    "vrača": ("vraća", "official_vracati_return"),
    "vračanja": ("vraćanja", "official_vracati_return"),
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
EXPECTED_FAMILIES = Counter(
    {
        "official_dopuscati": 79,
        "official_skracati": 12,
        "official_vracati_return": 8,
    }
)
EXPECTED_PHYSICAL_LINES = 96
EXPECTED_FILE_DISTRIBUTION = Counter(
    {"44-book-isv.tex": 4, "base-papers1-43-isv.tex": 95}
)
EXPECTED_SUCCESSOR_PINS = {
    "44-book-isv.tex": (
        168_427,
        "233A76BFBC11C21C0A8EEDCB74D6C6208D7A37B1085BFD7ED3D817A17B4C5793",
    ),
    "45-isv.tex": SOURCE_PINS["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_613,
        "71D7297364CFC43BD45DAE6D61E252A6351EAE116C076C8F7A58649B0E5BB4E2",
    ),
    "bib-isv.tex": SOURCE_PINS["bib-isv.tex"],
}
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


def module_receipt() -> dict[str, Any]:
    data = BASE_AUDIT_PATH.read_bytes()
    if (len(data), sha256(data)) != BASE_AUDIT_PIN:
        raise RuntimeError("base audit pin drift")
    return {"path": str(BASE_AUDIT_PATH), **pin(data)}


def authenticate_authority() -> dict[str, Any]:
    data = BASE.authenticate(
        BASE.DICTIONARY_PATH, BASE.DICTIONARY_PIN, "official dictionary"
    )
    rows: dict[str, dict[str, str]] = {}
    with BASE.DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_id = row["id"]
            if row_id in AUTHORITY_IDS:
                if row["isv"] != AUTHORITY_IDS[row_id]:
                    raise RuntimeError(f"official row {row_id} headword drift")
                rows[row_id] = {
                    key: row[key]
                    for key in ("id", "isv", "partOfSpeech", "en", "using_example")
                }
    if set(rows) != set(AUTHORITY_IDS):
        raise RuntimeError("official authority row-set drift")
    if "sučstvenyh" not in rows["20193"]["using_example"]:
        raise RuntimeError("official sųćstvėny variant example drift")
    return {
        "path": str(BASE.DICTIONARY_PATH),
        **pin(data),
        "rows": [rows[row_id] for row_id in sorted(rows, key=int)],
    }


def relevant_census(cohort: dict[str, bytes]) -> Counter[str]:
    forms = set(TARGETS) | {after for after, _family in TARGETS.values()}
    result: Counter[str] = Counter()
    for data in cohort.values():
        for token in BASE.WORD_RE.findall(data.decode("utf-8", errors="strict")):
            folded = token.casefold()
            if folded in forms:
                result[folded] += 1
    return result


def excluded_variant_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for data in cohort.values():
        for token in BASE.WORD_RE.findall(data.decode("utf-8", errors="strict")):
            folded = token.casefold()
            if folded.startswith(("sučstven", "sućstven", "najsučstven", "najsućstven", "nesučstven", "nesućstven")):
                result[folded] += 1
    return result


def build_report() -> dict[str, Any]:
    cohort = BASE.read_cohort()
    original_targets = BASE.TARGETS
    BASE.TARGETS = TARGETS
    try:
        manifest, before = BASE.scan(cohort)
        outputs = BASE.project(cohort, manifest)
    finally:
        BASE.TARGETS = original_targets
    if before != EXPECTED_BEFORE:
        raise RuntimeError(f"target census drift: {dict(before)}")
    families = Counter(item["family"] for item in manifest)
    if families != EXPECTED_FAMILIES:
        raise RuntimeError(f"family census drift: {dict(families)}")
    if len(manifest) != 99:
        raise RuntimeError(f"site cardinality drift: {len(manifest)}")
    physical_lines = len({(item["file"], item["line"]) for item in manifest})
    if physical_lines != EXPECTED_PHYSICAL_LINES:
        raise RuntimeError(f"physical-line cardinality drift: {physical_lines}")
    distribution = Counter(item["file"] for item in manifest)
    if distribution != EXPECTED_FILE_DISTRIBUTION:
        raise RuntimeError(f"source distribution drift: {dict(distribution)}")
    after = relevant_census(outputs)
    for old in TARGETS:
        if after[old]:
            raise RuntimeError(f"projected target residue: {old}")
    exclusions_before = excluded_variant_census(cohort)
    exclusions_after = excluded_variant_census(outputs)
    if exclusions_before != exclusions_after:
        raise RuntimeError("protected sųćstvėny family changed")
    observed_successor = {
        name: (len(outputs[name]), sha256(outputs[name])) for name in BASE.SOURCE_ORDER
    }
    if observed_successor != EXPECTED_SUCCESSOR_PINS:
        raise RuntimeError(f"projected successor pin drift: {observed_successor}")
    manifest_bytes = BASE.canonical_bytes(manifest)
    return {
        "schema": "noether-isv-v021-official-consonant-majorities-audit-v1",
        "edit_id": "ISV021-EDIT-0010",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in BASE.SOURCE_ORDER},
        "projected_successor": {
            name: pin(outputs[name]) for name in BASE.SOURCE_ORDER
        },
        "coverage": {
            "sites": len(manifest),
            "physical_lines": physical_lines,
            "families": dict(sorted(families.items())),
            "before_census": dict(sorted(before.items())),
            "projected_relevant_census": dict(sorted(after.items())),
            "source_distribution": dict(sorted(distribution.items())),
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": manifest,
        },
        "authority": {"official_dictionary": authenticate_authority()},
        "exclusions": {
            "official_variant_split": {
                "disposition": "All sųćstvėny-family surfaces remain byte-identical. The official headwords use ć, while official row 20193 itself uses sučstvenyh in its Interslavic example; neither spelling may be erased by a frequency-only rule.",
                "observed_forms": dict(sorted(exclusions_before.items())),
            },
            "homographic_noun": "The healer/sorcerer noun vrač is not targeted; only exact return-verb surfaces enumerated in TARGETS are eligible.",
            "already_standard_forms": "Existing dopušć-, skrać-, vrać-, and vȯzvrać- surfaces are preserved and counted only as successor controls.",
        },
        "validation": {
            "exact_reverse": True,
            "utf8": True,
            "v2_visible_roles_only": True,
            "unknown_argument_commands": 0,
            "protected_tex_structure_equal": True,
            "protected_variant_family_equal": True,
            "source_writes": 0,
        },
        "tools": {"base_read_only_audit": module_receipt()},
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
