#!/usr/bin/env python3
"""Read-only reversible audit for corrected ISV021-EDIT-0010-R2.

The edition declares a basic reader-facing Latin surface.  Official
orthography therefore requires etymological ć to appear as standard č.  This
audit aligns the 42 remaining minority surfaces in the dopušč-, skrač-,
vrač-/vozvrač-, and sučstven- families with the official generated basic
display.  It also authenticates and rejects the never-applied R1 candidate,
which had mistakenly read the dictionary's etymological source column as a
basic-spelling mandate.
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
import zipfile


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
REJECTED_R1_RECEIPT_PATH = (
    ROOT / "decision_records" / "ISV021-EDIT-0010-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
REJECTED_R1_RECEIPT_PIN = (
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
SNAPSHOT_ARCHIVE_PATH = Path(
    r"<WORKSPACE_ROOT>\01_methodology"
    r"\claude_fable_program\data"
    r"\interslavic_dictionary_official_snapshot_20260816"
    r"\upstream_repository_0fab0c5b4463118d46b1cdcd506926d8848052c9.zip"
)
SNAPSHOT_ARCHIVE_PIN = (
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
DICTIONARY_CODE_ENTRY = (
    "interslavic-0fab0c5b4463118d46b1cdcd506926d8848052c9/"
    "src/services/dictionary.ts"
)
DICTIONARY_CODE_ENTRY_PIN = (
    26_926,
    "60C09F2C2B3015033F1342BEA95FC48A1C36772F75880F669FB14C110577101D",
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


BASE = authenticate_module(
    BASE_AUDIT_PATH, BASE_AUDIT_PIN, "isv021_edit0010_r2_vowel_audit_base"
)
BASE.SOURCE_PINS = SOURCE_PINS

TARGETS: dict[str, tuple[str, str]] = {
    "dopušća": ("dopušča", "basic_dopuscati"),
    "dopušćajut": ("dopuščajut", "basic_dopuscati"),
    "dopušćati": ("dopuščati", "basic_dopuscati"),
    "skraćenja": ("skračenja", "basic_skracati"),
    "skraćeno": ("skračeno", "basic_skracati"),
    "vozvraća": ("vozvrača", "basic_vracati_return"),
    "vraćajemo": ("vračajemo", "basic_vracati_return"),
    "vraćajuči": ("vračajuči", "basic_vracati_return"),
    "sućstveno": ("sučstveno", "basic_sucstven"),
    "sućstvene": ("sučstvene", "basic_sucstven"),
    "sućstvena": ("sučstvena", "basic_sucstven"),
    "sućstvenym": ("sučstvenym", "basic_sucstven"),
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
EXPECTED_FAMILIES = Counter(
    {
        "basic_dopuscati": 33,
        "basic_skracati": 2,
        "basic_vracati_return": 3,
        "basic_sucstven": 4,
    }
)
EXPECTED_PHYSICAL_LINES = 40
EXPECTED_FILE_DISTRIBUTION = Counter(
    {"44-book-isv.tex": 4, "base-papers1-43-isv.tex": 38}
)
EXPECTED_SUCCESSOR_PINS = {
    "44-book-isv.tex": (
        168_427,
        "F8A278F67B87AE86C8F3CCE3F78EE32265986F0251EE8430F73BACCE20694E71",
    ),
    "45-isv.tex": SOURCE_PINS["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_613,
        "34540C032E966C54E44BEDCB45902161A978051F13A7ABA07CDA1925A418E594",
    ),
    "bib-isv.tex": SOURCE_PINS["bib-isv.tex"],
}
BASIC_DISPLAY_ROWS = {
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
RAW_SOURCE_HEADWORDS = {
    **{row_id: values[0] for row_id, values in BASIC_DISPLAY_ROWS.items()},
    "20192": "sųćstvėno",
    "20193": "sųćstvėny",
}


def module_receipt() -> dict[str, Any]:
    data = authenticate(BASE_AUDIT_PATH, BASE_AUDIT_PIN, "base audit")
    return {"path": str(BASE_AUDIT_PATH), **pin(data)}


def authenticate_orthography() -> dict[str, Any]:
    data = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "official orthography")
    lines = data.decode("utf-8", errors="strict").splitlines()
    needles = {
        69: "optional letters",
        77: "`ć` and `đ`",
        80: "`ć` and `đ`, which in standard orthography should be replaced with `č` and `dž`",
        102: "please refrain from using this orthography in everyday conversations",
        104: "use it consistently",
    }
    controls: list[dict[str, Any]] = []
    for line_number, needle in needles.items():
        line = lines[line_number - 1]
        if needle not in line:
            raise RuntimeError(f"orthography control drift at line {line_number}")
        controls.append({"line": line_number, "text_sha256": sha256(line.encode("utf-8"))})
    return {"path": str(ORTHOGRAPHY_PATH), **pin(data), "controls": controls}


def authenticate_basic_display() -> dict[str, Any]:
    archive = authenticate(SNAPSHOT_ARCHIVE_PATH, SNAPSHOT_ARCHIVE_PIN, "snapshot archive")
    with zipfile.ZipFile(SNAPSHOT_ARCHIVE_PATH) as handle:
        names = [info.filename for info in handle.infolist()]
        if names.count(SNAPSHOT_ENTRY) != 1:
            raise RuntimeError("snapshot entry identity drift")
        entry = handle.read(SNAPSHOT_ENTRY)
        dictionary_code = handle.read(DICTIONARY_CODE_ENTRY)
    if (len(entry), sha256(entry)) != SNAPSHOT_ENTRY_PIN:
        raise RuntimeError("snapshot entry pin drift")
    if (len(dictionary_code), sha256(dictionary_code)) != DICTIONARY_CODE_ENTRY_PIN:
        raise RuntimeError("dictionary implementation pin drift")
    code_lines = dictionary_code.decode("utf-8", errors="strict").splitlines()
    if "['ć', 'č']" not in code_lines[57]:
        raise RuntimeError("dictionary ć-to-č rule drift")
    if "!['š', 'ž', 'č', 'ě', 'y'].includes(replacement[0])" not in code_lines[762]:
        raise RuntimeError("dictionary flavor exception rule drift")
    payload = json.loads(entry.decode("utf-8", errors="strict"))
    index = payload.get("isv-en")
    if not isinstance(index, dict):
        raise RuntimeError("snapshot isv-en index missing")
    found: list[dict[str, str]] = []
    for row_id, (etymological, basic) in BASIC_DISPLAY_ROWS.items():
        records = index.get(row_id)
        if not isinstance(records, list):
            raise RuntimeError(f"snapshot row missing: {row_id}")
        matches = [record for record in records if record.get("id") == row_id]
        if len(matches) != 1:
            raise RuntimeError(f"snapshot row identity ambiguity: {row_id}")
        record = matches[0]
        if record.get("isv") != etymological or record.get("original") != basic:
            raise RuntimeError(f"snapshot surface drift: {row_id}")
        found.append({"id": row_id, "isv": etymological, "original": basic})
    return {
        "archive": {"path": str(SNAPSHOT_ARCHIVE_PATH), **pin(archive)},
        "entry": {"name": SNAPSHOT_ENTRY, **pin(entry)},
        "implementation": {
            "name": DICTIONARY_CODE_ENTRY,
            **pin(dictionary_code),
            "control_lines": [58, 763],
        },
        "rows": found,
    }


def authenticate_raw_source_rows() -> dict[str, Any]:
    data = BASE.authenticate(
        BASE.DICTIONARY_PATH, BASE.DICTIONARY_PIN, "official dictionary source sheet"
    )
    found: dict[str, str] = {}
    with BASE.DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in BASIC_DISPLAY_ROWS:
                found[row["id"]] = row["isv"]
    if found != RAW_SOURCE_HEADWORDS:
        raise RuntimeError("raw etymological source rows drift")
    return {"path": str(BASE.DICTIONARY_PATH), **pin(data), "rows": found}


def authenticate_rejected_r1() -> dict[str, Any]:
    data = authenticate(
        REJECTED_R1_RECEIPT_PATH, REJECTED_R1_RECEIPT_PIN, "rejected R1 candidate"
    )
    receipt = json.loads(data.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("R1 candidate status drift")
    if receipt.get("projected_successor", {}).get("44-book-isv.tex", {}).get("sha256") != (
        "233A76BFBC11C21C0A8EEDCB74D6C6208D7A37B1085BFD7ED3D817A17B4C5793"
    ):
        raise RuntimeError("R1 projected head drift")
    return {
        "path": str(REJECTED_R1_RECEIPT_PATH),
        **pin(data),
        "disposition": "REJECTED_BEFORE_APPLY_WRONG_ORTHOGRAPHY_LAYER",
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
    if len(manifest) != 42:
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
    observed_successor = {
        name: (len(outputs[name]), sha256(outputs[name])) for name in BASE.SOURCE_ORDER
    }
    if observed_successor != EXPECTED_SUCCESSOR_PINS:
        raise RuntimeError(f"projected successor pin drift: {observed_successor}")
    manifest_bytes = BASE.canonical_bytes(manifest)
    return {
        "schema": "noether-isv-v021-basic-consonant-surface-audit-v1",
        "edit_id": "ISV021-EDIT-0010",
        "revision": "R2",
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
        "authority": {
            "official_orthography": authenticate_orthography(),
            "official_generated_basic_display": authenticate_basic_display(),
            "raw_etymological_source_sheet": authenticate_raw_source_rows(),
        },
        "adverse_history": {
            "rejected_r1": authenticate_rejected_r1(),
            "reason": "R1 inferred basic reader spelling directly from the etymological isv source column. Official orthography line 80 and the upstream generated original field both require č for these standard surfaces.",
            "r1_source_writes": 0,
        },
        "exclusions": {
            "majority_basic_forms": "The 99 already-basic č sites are controls, not targets.",
            "homographic_noun": "The healer/sorcerer noun vrač is not targeted; only three exact return-verb minority surfaces are eligible.",
            "other_etymological_letters": "This decision changes only optional ć to standard č in four exact lexical families; it does not declare a global spelling migration for unrelated optional letters.",
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
