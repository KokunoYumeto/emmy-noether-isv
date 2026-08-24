#!/usr/bin/env python3
"""Read-only, reversible audit for ISV021-EDIT-0009.

This combines only directly supported residual reader-facing repairs: official
dictionary vowel forms, unambiguous missing diacritics, productive matrix
adjectives, and malformed spellings of two official verb families.  It pins
the exact EDIT-0008 source cohort, changes no source bytes, and proves an exact
forward/reverse projection with protected TeX structure unchanged.
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
    BASE_AUDIT_PATH, BASE_AUDIT_PIN, "isv021_edit0009_vowel_audit_base"
)


TARGETS: dict[str, tuple[str, str]] = {
    # Direct official-vowel repairs already independently audited.
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
    # Unambiguous missing-diacritic repairs.
    "delitelj": ("dělitelj", "clear_delitelj"),
    "jedinicnogo": ("jediničnogo", "clear_jedinic_adjective"),
    "jedinicny": ("jediničny", "clear_jedinic_adjective"),
    "pomocju": ("pomoćju", "clear_pomoc_family"),
    "pomocnyh": ("pomoćnyh", "clear_pomoc_family"),
    "pomocna": ("pomoćna", "clear_pomoc_family"),
    "pomocnoj": ("pomoćnoj", "clear_pomoc_family"),
    "cela": ("cěla", "clear_cely_adjective"),
    "celo": ("cělo", "clear_cely_adjective"),
    "celu": ("cělu", "clear_cely_adjective"),
    "celyh": ("cělyh", "clear_cely_adjective"),
    "celom": ("cělom", "clear_cely_adjective"),
    # Productive/official consonant repairs; majority-only sweeps are excluded.
    "matricny": ("matričny", "productive_matric_adjective"),
    "matricnogo": ("matričnogo", "productive_matric_adjective"),
    "matricnyh": ("matričnyh", "productive_matric_adjective"),
    "dopusča": ("dopušća", "official_dopusc_error"),
    "dopusća": ("dopušća", "official_dopusc_error"),
    "isčezaje": ("izčezaje", "official_izcez_error"),
    "isčezajut": ("izčezajut", "official_izcez_error"),
    "iščezajut": ("izčezajut", "official_izcez_error"),
    # Exact same-corpus technical phrasing backed by the cěly paradigm.
    "celkovy": ("cěly", "lexical_cely_technical"),
    "celkovogo": ("cělogo", "lexical_cely_technical"),
}

PHRASE_TARGETS: dict[str, tuple[str, str]] = {
    "Jest celěsoobrazno": ("Korisno jest", "lexical_clear_paraphrase"),
    "Za tu cěl": ("Za toj cělj", "lexical_celj_agreement"),
}
EXPECTED_PHRASE_AFTER = {
    "Jest celěsoobrazno": 2,
    "Za tu cěl": 1,
}

EXPECTED_BEFORE = Counter(
    {
        "cela": 4,
        "celo": 3,
        "celom": 1,
        "celu": 2,
        "celyh": 1,
        "celkovogo": 1,
        "celkovy": 1,
        "delitelj": 1,
        "dopusča": 4,
        "dopusća": 1,
        "iměnno": 2,
        "isčezaje": 3,
        "isčezajut": 2,
        "iščezajut": 1,
        "izsledovali": 1,
        "jedinicnogo": 1,
        "jedinicny": 2,
        "matricnogo": 2,
        "matricny": 10,
        "matricnyh": 3,
        "nekoliko": 10,
        "nekoje": 14,
        "neku": 2,
        "pomocju": 1,
        "pomocna": 6,
        "pomocnoj": 2,
        "pomocnyh": 1,
        "posle": 2,
        "tesno": 1,
        "trebuje": 1,
        "trebujut": 1,
        "upotrebjena": 1,
        "upotrebjene": 1,
        "upotrebljen": 1,
        "vsěgda": 8,
        "Jest celěsoobrazno": 1,
        "Za tu cěl": 1,
    }
)
EXPECTED_FAMILIES = Counter(
    {
        "clear_cely_adjective": 11,
        "clear_delitelj": 1,
        "clear_jedinic_adjective": 3,
        "clear_pomoc_family": 10,
        "official_dopusc_error": 5,
        "official_imenno": 2,
        "official_izcez_error": 6,
        "official_izsledovati": 1,
        "official_nekoj": 16,
        "official_nekoliko": 10,
        "official_posle": 2,
        "official_tesno": 1,
        "official_trebovati": 2,
        "official_upotrebiti": 3,
        "official_vsegda": 8,
        "productive_matric_adjective": 15,
        "lexical_cely_technical": 2,
        "lexical_clear_paraphrase": 1,
        "lexical_celj_agreement": 1,
    }
)
EXPECTED_FILE_DISTRIBUTION = Counter(
    {
        "44-book-isv.tex": 17,
        "base-papers1-43-isv.tex": 82,
        "bib-isv.tex": 1,
    }
)

ADDITIONAL_AUTHORITY_IDS = {
    "100": "pomoćny",
    "1027": "cěly",
    "1267": "s pomoćjų",
    "1754": "děliti",
    "2098": "ulica",
    "25182": "dělba",
    "3545": "děljeńje",
    "3550": "izčezati",
    "3557": "izčeznųti",
    "35975": "matrica",
    "37582": "uličny",
    "3945": "pomoć",
    "5174": "jedinica",
    "7208": "dopušćati",
    "7988": "izčezneńje",
    "20859": "dopušćati",
    "421": "cělj",
    "2893": "tȯj",
    "4143": "cělkovity",
    "6271": "koristny",
    "30950": "uměstno",
}


def module_receipt() -> dict[str, Any]:
    data = BASE_AUDIT_PATH.read_bytes()
    if (len(data), sha256(data)) != BASE_AUDIT_PIN:
        raise RuntimeError("base audit pin drift")
    return {"path": str(BASE_AUDIT_PATH), **pin(data)}


def authenticate_additional_authority() -> dict[str, Any]:
    data = BASE.authenticate(
        BASE.DICTIONARY_PATH, BASE.DICTIONARY_PIN, "official dictionary"
    )
    rows: dict[str, dict[str, str]] = {}
    with BASE.DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_id = row["id"]
            if row_id in ADDITIONAL_AUTHORITY_IDS:
                expected_headword = ADDITIONAL_AUTHORITY_IDS[row_id]
                if row["isv"] != expected_headword:
                    raise RuntimeError(
                        f"official row {row_id} headword drift: {row['isv']!r}"
                    )
                rows[row_id] = {
                    key: row[key]
                    for key in ("id", "isv", "partOfSpeech", "en", "using_example")
                }
    if set(rows) != set(ADDITIONAL_AUTHORITY_IDS):
        raise RuntimeError("additional official authority row-set drift")
    example_needles = {
        "100": "pomočny",
        "1027": "Cěly",
        "3550": "izčezajut",
        "5174": "jedinic",
    }
    for row_id, needle in example_needles.items():
        if needle not in rows[row_id]["using_example"]:
            raise RuntimeError(f"official example drift for row {row_id}")
    return {
        "path": str(BASE.DICTIONARY_PATH),
        **pin(data),
        "rows": [rows[row_id] for row_id in sorted(rows, key=int)],
    }


def projected_census(cohort: dict[str, bytes]) -> Counter[str]:
    forms = set(TARGETS) | {after for after, _family in TARGETS.values()}
    result: Counter[str] = Counter()
    for data in cohort.values():
        text = data.decode("utf-8", errors="strict")
        for token in BASE.WORD_RE.findall(text):
            folded = token.casefold()
            if folded in forms:
                result[folded] += 1
    return result


def scan_phrases(cohort: dict[str, bytes]) -> tuple[list[dict[str, Any]], Counter[str]]:
    manifest: list[dict[str, Any]] = []
    census: Counter[str] = Counter()
    for filename in BASE.SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        starts = BASE.line_starts(text)
        segmenter = BASE.SEGMENTER.TexSegmenter(text)
        segments = segmenter.segment()
        if segmenter.unknown_argument_commands:
            raise RuntimeError(f"unknown argument commands in {filename}")
        for segment in segments:
            if segment.role not in BASE.VISIBLE_ROLES:
                continue
            raw = text[segment.start : segment.end]
            for before, (after, family) in PHRASE_TARGETS.items():
                cursor = 0
                while True:
                    local = raw.find(before, cursor)
                    if local < 0:
                        break
                    scalar_offset0 = segment.start + local
                    line_index = BASE.line_for_offset(starts, scalar_offset0)
                    manifest.append(
                        {
                            "file": filename,
                            "line": line_index + 1,
                            "column": scalar_offset0 - starts[line_index] + 1,
                            "byte_offset0": len(text[:scalar_offset0].encode("utf-8")),
                            "before": before,
                            "after": after,
                            "family": family,
                            "role": segment.role,
                        }
                    )
                    census[before] += 1
                    cursor = local + len(before)
    return manifest, census


def authenticate_local_lexical_controls(cohort: dict[str, bytes]) -> dict[str, Any]:
    text = cohort["base-papers1-43-isv.tex"].decode("utf-8", errors="strict")
    lines = text.splitlines()
    controls = {
        126: "cěly ręd form",
        547: "cělogo ręda form",
        553: "cěly ręd form",
        1082: "cěly ręd form",
        4906: "Korisno jest mysliti",
        4912: "cěly ręd form",
        15623: "Za toj dokaz",
    }
    result: list[dict[str, Any]] = []
    for line_number, needle in controls.items():
        line = lines[line_number - 1]
        if needle not in line:
            raise RuntimeError(f"local lexical control drift at line {line_number}")
        data = line.encode("utf-8")
        result.append(
            {
                "file": "base-papers1-43-isv.tex",
                "line": line_number,
                "needle": needle,
                **pin(data),
            }
        )
    return {"controls": result}


def build_report() -> dict[str, Any]:
    cohort = BASE.read_cohort()
    original_targets = BASE.TARGETS
    BASE.TARGETS = TARGETS
    try:
        manifest, before = BASE.scan(cohort)
        phrase_manifest, phrase_before = scan_phrases(cohort)
        manifest.extend(phrase_manifest)
        before.update(phrase_before)
        source_rank = {name: index for index, name in enumerate(BASE.SOURCE_ORDER)}
        manifest.sort(key=lambda item: (source_rank[item["file"]], item["byte_offset0"]))
        outputs = BASE.project(cohort, manifest)
    finally:
        BASE.TARGETS = original_targets
    if before != EXPECTED_BEFORE:
        raise RuntimeError(f"target census drift: {dict(before)}")
    families = Counter(item["family"] for item in manifest)
    if families != EXPECTED_FAMILIES:
        raise RuntimeError(f"family census drift: {dict(families)}")
    if len(manifest) != 100:
        raise RuntimeError(f"site cardinality drift: {len(manifest)}")
    physical_lines = len({(item["file"], item["line"]) for item in manifest})
    if physical_lines != 92:
        raise RuntimeError(f"physical-line cardinality drift: {physical_lines}")
    distribution = Counter(item["file"] for item in manifest)
    if distribution != EXPECTED_FILE_DISTRIBUTION:
        raise RuntimeError(f"source distribution drift: {dict(distribution)}")
    census = projected_census(outputs)
    for old in TARGETS:
        if census[old]:
            raise RuntimeError(f"projected target residue: {old}")
    phrase_census: dict[str, dict[str, int]] = {}
    for before_phrase, (after_phrase, _family) in PHRASE_TARGETS.items():
        before_count = sum(
            data.decode("utf-8", errors="strict").count(before_phrase)
            for data in outputs.values()
        )
        after_count = sum(
            data.decode("utf-8", errors="strict").count(after_phrase)
            for data in outputs.values()
        )
        if before_count != 0 or after_count != EXPECTED_PHRASE_AFTER[before_phrase]:
            raise RuntimeError(f"projected phrase residue: {before_phrase}")
        phrase_census[before_phrase] = {
            "old": before_count,
            "new": after_count,
        }
    manifest_bytes = BASE.canonical_bytes(manifest)
    return {
        "schema": "noether-isv-v021-residual-reader-consistency-audit-v1",
        "edit_id": "ISV021-EDIT-0009",
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
            "projected_relevant_census": dict(sorted(census.items())),
            "projected_phrase_census": phrase_census,
            "source_distribution": dict(sorted(distribution.items())),
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": manifest,
        },
        "authority": {
            "official_vowel_rows": BASE.authenticate_authority(),
            "additional_official_rows": authenticate_additional_authority(),
            "local_lexical_controls": authenticate_local_lexical_controls(cohort),
            "independent_reviews": [
                {
                    "task": "/root/residual_clear_diacritics",
                    "disposition": "25 replacements accepted subject to parent replay",
                },
                {
                    "task": "/root/residual_clear_diacritics/audit_delitelj_unit",
                    "disposition": "four-site nested review corroborated",
                },
                {
                    "task": "/root/residual_consonant_variants",
                    "disposition": "26 replacements accepted subject to parent replay; 37 official minority forms protected",
                },
                {
                    "task": "/root/residual_celj_compounds",
                    "disposition": "four lexical/agreement repairs accepted subject to parent replay",
                },
            ],
        },
        "exclusions": {
            "official_minority_forms": "Do not normalize 28 dopušć-, four sućstven-, two skrać-, or three return-sense vrać- tokens to corpus-majority spellings; official dictionary evidence supports their consonants.",
            "optional_etymological_vowels": "No svęz/svez or vzęti/vzeti form is changed; optional ę requires a separately declared house policy.",
            "lexical_alternatives_rejected": "cělkovity/cělkovitogo are official but less consistent than exact same-corpus cěly ręd/cělogo ręda; uměstno is official but less directly aligned with the established Korisno jest construction; reconstructed cěljesȯobrazno lacks direct pinned-dictionary support.",
            "protected_distinct_lexemes": "The noun jedinica and its inflections are not touched by the exact adjective mappings.",
        },
        "validation": {
            "exact_reverse": True,
            "utf8": True,
            "v2_visible_roles_only": True,
            "unknown_argument_commands": 0,
            "protected_tex_structure_equal": True,
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
