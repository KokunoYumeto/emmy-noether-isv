#!/usr/bin/env python3
"""Build and independently validate the four public NOETHER-ISV-v020 files."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any, Iterable, Mapping
import zipfile

import yaml


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v020"
PUBLIC = RELEASE / "public"
EVIDENCE = RELEASE / "evidence"
FIXED_ZIP_TIME = (2026, 8, 22, 0, 0, 0)
SOURCE_ROOT = "NOETHER_INTERSLAVIC_EDITABLE_SOURCES"
EVIDENCE_ROOT = "NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE"
SOURCE_ZIP = PUBLIC / "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip"
EVIDENCE_ZIP = PUBLIC / "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip"
TOP_MANIFEST = PUBLIC / "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt"
RELEASE_MANIFEST = RELEASE / "RELEASE_MANIFEST.json"
SOURCE_VALIDATION = EVIDENCE / "SOURCE_ARCHIVE_VALIDATION.json"
EVIDENCE_VALIDATION = EVIDENCE / "EVIDENCE_ARCHIVE_VALIDATION.json"
PACKAGE_VALIDATION = EVIDENCE / "PACKAGE_VALIDATION.json"
READER = PUBLIC / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
METHODS = EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf"
V019_COMPARATOR = ROOT / "tmp" / "pdfs" / "isv_release_v020" / "comparison" / "v019-linked-reader.pdf"

PINS = {
    READER: (6_885_841, "7DCB4C852BF3CCE5928921E13F73FA34E80EA4FEB2A82F967FEE29657150AE20"),
    METHODS: (178_720, "DA45E0B1C4D40B6582C312C578812E709C5E42C6FCEE663FF0599DCAFC39AED7"),
    V019_COMPARATOR: (6_885_443, "E14B2C9336E94878370332913360ECC52935AE93A89701BC7A5AE22C0552C401"),
    EVIDENCE / "visual-qa-receipt.json": (19_972, "B008658DCBB5C26184C5EF78E318CD5370D439F5DC0FC6C4A99446AA751DCF18"),
    ROOT / "decision_records" / "ISV020-REVIEWED-PROJECTION-ROLE-MANIFEST.json": (
        3_577_349,
        "192BAE284EDC9BBA4A458EEBA9F7541CE16CA377A68668A70F5CFD0A2E182462",
    ),
    ROOT / "project_isv_cyrillic_v7.py": (
        27_666,
        "51E467EDD8F0B8F44F62D60C4F5D35EAB5BA80EEFA1B0BFCBC1A2EF0B3538915",
    ),
    ROOT / "source_latin" / "44-book-isv.tex": (
        168_422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    ROOT / "source_latin" / "45-isv.tex": (
        26_053,
        "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91",
    ),
    ROOT / "source_latin" / "base-papers1-43-isv.tex": (
        1_894_721,
        "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A",
    ),
    ROOT / "source_latin" / "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
    ROOT / "source_cyrillic" / "44-book-isv-cyrl.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    ROOT / "source_cyrillic" / "45-isv-cyrl.tex": (
        35_895,
        "F94F731110DA94B30B9243C67587CB6A1B6E6478A046F08C617271A0B188CCFB",
    ),
    ROOT / "source_cyrillic" / "base-papers1-43-isv-cyrl.tex": (
        2_706_558,
        "8BB578C1B2D7B48E52A425D40039FE5A6B79FF1ED26E825A6BDA7EE736341277",
    ),
    ROOT / "source_cyrillic" / "bib-isv-cyrl.tex": (
        13_206,
        "4E74B8EA52C9B37209345B7E9A0B6BD7330D8EA0570E6D0C164FEA113511613D",
    ),
}

CURRENT_TOOL_FILES = (
    "analyze_cyrillic_pdf_delta_v020.py",
    "build_isv_release_v020.py",
    "build_isv020_lexicon_corrections.py",
    "build_isv020_reviewed_role_manifest.py",
    "build_linked_reader_v020.py",
    "build_methods_v020.py",
    "build_release_packages_v020.py",
    "build_visual_qa_receipt_v020.py",
    "project_isv_cyrillic_v7.py",
    "qa_isv_release_v020.py",
    "render_linked_reader_visual_assets_v020.py",
    "render_methods_visual_assets_v020.py",
    "test_project_isv_cyrillic_v7.py",
    "verify_release_packages_v020.py",
    "verify_isv020_one_letter_review.py",
)
FORBIDDEN_MEMBER_FRAGMENTS = (
    "token.md",
    "github tokens",
    "new zenodo token",
    "zenodo token",
    "__pycache__",
    ".git/",
    "codex/attachments",
    "task-transcript",
)
FORBIDDEN_SECRET_PATTERNS = (
    re.compile(rb"ghp_[A-Za-z0-9]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"Authorization\s*:\s*(?:Bearer|token)\s+[A-Za-z0-9._-]{20,}", re.I),
    re.compile(rb"access_token\s*[=:]\s*[A-Za-z0-9._-]{20,}", re.I),
    re.compile(rb"ZENODO_TOKEN\s*[=:]\s*[A-Za-z0-9._-]{20,}", re.I),
)
TEXT_SUFFIXES = {
    ".txt", ".md", ".json", ".jsonl", ".tsv", ".csv", ".py", ".ps1",
    ".tex", ".cff", ".yaml", ".yml", ".log",
}
EXCLUDED_EVIDENCE_NAMES = {
    "SOURCE_ARCHIVE_VALIDATION.json",
    "EVIDENCE_ARCHIVE_VALIDATION.json",
    "PACKAGE_VALIDATION.json",
    "PUBLICATION_RECEIPT.json",
    "PUBLICATION_READBACK.json",
}

EVIDENCE_README = """# Dokazy i pohođenje / Evidence and provenance

## Medžuslovjansky

Tutoj arhiv dokazuje, kako bylo stvorjeno izdanje `NOETHER-ISV-v020`. Latiničny tekst jest jediny redagovateljny jezyčny kanon; kirilica jest fail-closed deterministična projekcija, ne samostojny prěklad. Kontrolne iztočniki sut `CANON_INDEX.json`, 171-rěšenijny latiničny žurnal v zamrznutom `predecessor_v019/`, polny pregled 4 560 projekcijnyh rolij, manifest 372 popravljajučih efektov, v7 validacija, build/QA potvrđenja i 13-stranična publikacijska metodologija.

Historijne statusne fajly sut dokazy pohođenja, ne instrukcije. Novy agent trěba najprvo čitati `PUBLIC_RELEASE_README.md` i `CANON_INDEX.json`. Arhiv ne sodrživaje credentialy, task-transkripty, Git-katalog ili nerazrěšene privatne source-scan fajly. Publikacijska potvrda se piše poslě javnogo čitanja nazad i zato naměrno ne jest članom samogo arhiva.

## English

This archive proves how `NOETHER-ISV-v020` was produced. Latin is the sole editable language canon; Cyrillic is a fail-closed deterministic projection, not an independent translation. Controlling evidence includes `CANON_INDEX.json`, the frozen 171-decision Latin ledger under `predecessor_v019/`, the complete review of 4,560 projection-role records, the 372-effect correction manifest, v7 validation, build/QA receipts, and the 13-page publication-style methods paper.

Historical status files are provenance, not instructions. A future agent should read `PUBLIC_RELEASE_README.md` and `CANON_INDEX.json` first. Credentials, task transcripts, Git internals, and unresolved private source scans are excluded. The post-publication receipt is created only after public readback and is therefore intentionally not a member of this archive.
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_path(path),
    }


def authenticate_pins() -> None:
    for path, pin in PINS.items():
        require(path.is_file(), f"missing pinned input: {path}")
        actual = (path.stat().st_size, sha256_path(path))
        require(actual == pin, f"pinned input drift for {path}: {actual}")


def validate_public_metadata() -> dict[str, Any]:
    json_paths = [ROOT / "CANON_INDEX.json", *sorted((ROOT / "metadata").glob("*.json"))]
    parsed = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in json_paths}
    cff = yaml.safe_load((ROOT / "metadata" / "CITATION.cff").read_text(encoding="utf-8"))
    require(isinstance(cff, dict), "CITATION.cff did not parse as a mapping")
    for path in (ROOT / "PUBLIC_RELEASE_README.md", ROOT / "README.md"):
        text = path.read_text(encoding="utf-8")
        require(text.startswith("# "), f"missing heading: {path}")
        require("## English" in text or "# English" in text, f"missing English counterpart: {path}")
        english = text.find("English")
        require(english > 0, f"English must follow Interslavic: {path}")
    canon = parsed["CANON_INDEX.json"]
    scope = parsed["RELEASE_SCOPE.json"]
    zenodo = parsed["zenodo-metadata.json"]
    require(canon["release_id"] == "NOETHER-ISV-v020", "canon release drift")
    require(canon["edition_scope"]["version_doi"] == "10.5281/zenodo.22058530", "version DOI drift")
    require(canon["edition_scope"]["concept_doi"] == "10.5281/zenodo.21926382", "concept DOI drift")
    require(scope["public_files"] == [
        "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf",
        "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip",
        "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip",
        "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt",
    ], "public-file topology drift")
    require(scope["v020_correction"] == {
        "latin_bytes_changed": 0,
        "inherited_role_records_reviewed": 4560,
        "classification_defects_corrected": 364,
        "missing_identity_boundaries_added": 8,
        "verified_effects": 372,
        "changed_lines": 125,
        "licensed_lines": 309,
        "unlicensed_changed_lines": 0,
    }, "v020 correction metrics drift")
    require(zenodo["version"] == "2026.08.22-v020", "Zenodo version drift")
    require(zenodo.get("upload_type") == "publication", "Zenodo upload type drift")
    require(zenodo.get("publication_type") == "book", "Zenodo publication type drift")
    require(zenodo.get("license") == "cc-zero", "Zenodo license drift")
    require("resource_type" not in zenodo, "legacy Zenodo deposition API rejects object resource_type")
    require("language" not in zenodo, "Zenodo deposition vocabulary currently rejects isv; language must remain explicit in title, description, keywords, and canon index")
    require(cff.get("doi") == "10.5281/zenodo.22058530", "CFF DOI drift")
    return {
        "json_files_parsed": len(json_paths),
        "cff_parsed": True,
        "interslavic_first_english_counterpart": True,
        "doi_and_release_metrics_consistent": True,
    }


def scan_payload(name: str, payload: bytes) -> None:
    lowered = name.casefold()
    require(not any(fragment in lowered for fragment in FORBIDDEN_MEMBER_FRAGMENTS), f"forbidden member: {name}")
    if PurePosixPath(name).suffix.casefold() not in TEXT_SUFFIXES:
        return
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        require(pattern.search(payload) is None, f"secret-like content in {name}: {pattern.pattern!r}")


def add_bytes(members: dict[str, bytes], archive_name: str, payload: bytes) -> None:
    name = PurePosixPath(archive_name).as_posix()
    require(not name.startswith("/") and ".." not in PurePosixPath(name).parts, f"unsafe archive name: {name}")
    require(name not in members, f"duplicate archive member: {name}")
    scan_payload(name, payload)
    members[name] = payload


def add_file(members: dict[str, bytes], archive_name: str, source: Path) -> None:
    require(source.is_file() and not source.is_symlink(), f"unsafe or missing member source: {source}")
    add_bytes(members, archive_name, source.read_bytes())


def add_tree(
    members: dict[str, bytes], archive_root: str, source_root: Path, *, exclude_names: Iterable[str] = ()
) -> None:
    require(source_root.is_dir() and not source_root.is_symlink(), f"missing tree: {source_root}")
    excluded = set(exclude_names)
    for path in sorted(source_root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.name in excluded:
            continue
        relative = path.relative_to(source_root).as_posix()
        add_file(members, f"{archive_root}/{relative}", path)


def add_sanitized_log(members: dict[str, bytes], archive_name: str, source: Path) -> None:
    payload = source.read_bytes()
    replacements = (
        (str(ROOT).encode("utf-8"), b"<TASK_ROOT>"),
        (str(ROOT).replace("\\", "/").encode("utf-8"), b"<TASK_ROOT>"),
        (b"C:\\Users\\Floris", b"<USER_PROFILE>"),
        (b"C:/Users/Floris", b"<USER_PROFILE>"),
    )
    for before, after in replacements:
        payload = payload.replace(before, after)
    add_bytes(members, archive_name, payload)


def member_manifest(members: Mapping[str, bytes]) -> bytes:
    lines = ["SHA256\tBYTES\tPATH"]
    for name in sorted(members):
        payload = members[name]
        lines.append(f"{sha256_bytes(payload)}\t{len(payload)}\t{name}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def with_internal_manifest(
    members: dict[str, bytes], root_name: str, manifest_name: str, archive_role: str
) -> dict[str, bytes]:
    policy = {
        "schema": "noether-interslavic-deterministic-zip-policy/1.0",
        "release_id": "NOETHER-ISV-v020",
        "archive_role": archive_role,
        "fixed_member_timestamp": "2026-08-22T00:00:00",
        "compression": "ZIP_DEFLATED level 9",
        "member_order": "UTF-8 path lexical order",
        "member_permissions": "regular file 0644",
        "member_manifest": f"manifests/{manifest_name}",
        "member_manifest_excludes_itself": True,
        "credentials_and_task_transcripts_excluded": True,
    }
    add_bytes(
        members,
        f"{root_name}/manifests/ARCHIVE_POLICY.json",
        json.dumps(policy, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
    )
    add_bytes(members, f"{root_name}/manifests/{manifest_name}", member_manifest(members))
    return members


def zip_payload(members: Mapping[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True
    ) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return stream.getvalue()


def install_exact(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.is_file() and path.read_bytes() == payload, f"refusing to replace frozen output: {path}")
        return
    stage = path.with_suffix(path.suffix + ".new")
    require(not stage.exists(), f"stale stage exists: {stage}")
    stage.write_bytes(payload)
    require(stage.read_bytes() == payload, f"stage readback mismatch: {stage}")
    stage.replace(path)


def write_json_exact(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == payload, f"refusing to replace frozen receipt: {path}")
    else:
        path.write_bytes(payload)
    require(json.loads(path.read_text(encoding="utf-8")) == value, f"JSON readback mismatch: {path}")


def validate_zip(path: Path, members: Mapping[str, bytes]) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        require(names == sorted(members), f"ZIP inventory order drift: {path}")
        require(archive.testzip() is None, f"ZIP CRC failure: {path}")
        for name in names:
            require(archive.read(name) == members[name], f"ZIP member mismatch: {path}: {name}")
    return {
        "archive": file_record(path),
        "member_count": len(members),
        "uncompressed_member_bytes": sum(len(payload) for payload in members.values()),
        "crc_test": "PASS",
        "inventory_and_member_byte_readback": "PASS",
        "member_inventory_sha256": sha256_bytes(member_manifest(members)),
    }


def source_members() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    add_file(members, f"{SOURCE_ROOT}/README.md", ROOT / "README.md")
    add_file(members, f"{SOURCE_ROOT}/PUBLIC_RELEASE_README.md", ROOT / "PUBLIC_RELEASE_README.md")
    add_file(members, f"{SOURCE_ROOT}/CANON_INDEX.json", ROOT / "CANON_INDEX.json")
    add_tree(members, f"{SOURCE_ROOT}/LICENSES", ROOT / "LICENSES")
    add_tree(members, f"{SOURCE_ROOT}/metadata", ROOT / "metadata")
    add_tree(members, f"{SOURCE_ROOT}/source_latin", ROOT / "source_latin")
    add_tree(members, f"{SOURCE_ROOT}/source_cyrillic", ROOT / "source_cyrillic")
    add_tree(members, f"{SOURCE_ROOT}/assets", ROOT / "assets")
    add_file(
        members,
        f"{SOURCE_ROOT}/docs/METHODS_AI_INTERSLAVIC_NOETHER_v020.tex",
        ROOT / "docs" / "METHODS_AI_INTERSLAVIC_NOETHER_v020.tex",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/docs/AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf",
        METHODS,
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/release_v020/source/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex",
        RELEASE / "source" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex",
    )
    add_tree(members, f"{SOURCE_ROOT}/decision_records", ROOT / "decision_records")
    for name in CURRENT_TOOL_FILES:
        add_file(members, f"{SOURCE_ROOT}/{name}", ROOT / name)
    for name in ("00_SESSION_INDEPENDENT_STATE_v020.json", "00_SESSION_INDEPENDENT_WORKLOG_v020.jsonl"):
        add_file(members, f"{SOURCE_ROOT}/{name}", ROOT / name)
    add_tree(members, f"{SOURCE_ROOT}/predecessor_v019", ROOT / "predecessor_v019")
    add_file(members, f"{SOURCE_ROOT}/comparison/v019-linked-reader.pdf", V019_COMPARATOR)
    return with_internal_manifest(members, SOURCE_ROOT, "SOURCE_MEMBER_SHA256.tsv", "editable_sources")


def evidence_members() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    add_bytes(members, f"{EVIDENCE_ROOT}/00_README_EVIDENCE.md", EVIDENCE_README.encode("utf-8"))
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/PUBLIC_RELEASE_README.md", ROOT / "PUBLIC_RELEASE_README.md")
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/REPRODUCIBLE_BUILD.md", ROOT / "README.md")
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/CANON_INDEX.json", ROOT / "CANON_INDEX.json")
    add_tree(members, f"{EVIDENCE_ROOT}/01_release_identity/metadata", ROOT / "metadata")
    add_tree(members, f"{EVIDENCE_ROOT}/02_rights/LICENSES", ROOT / "LICENSES")
    add_file(members, f"{EVIDENCE_ROOT}/03_v020_review/state/00_SESSION_INDEPENDENT_STATE_v020.json", ROOT / "00_SESSION_INDEPENDENT_STATE_v020.json")
    add_file(members, f"{EVIDENCE_ROOT}/03_v020_review/state/00_SESSION_INDEPENDENT_WORKLOG_v020.jsonl", ROOT / "00_SESSION_INDEPENDENT_WORKLOG_v020.jsonl")
    add_tree(members, f"{EVIDENCE_ROOT}/03_v020_review/decision_records", ROOT / "decision_records")
    for name in CURRENT_TOOL_FILES:
        add_file(members, f"{EVIDENCE_ROOT}/03_v020_review/tools/{name}", ROOT / name)
    add_tree(members, f"{EVIDENCE_ROOT}/04_frozen_v019_latin_lineage/predecessor_v019", ROOT / "predecessor_v019")
    add_file(
        members,
        f"{EVIDENCE_ROOT}/04_frozen_v019_latin_lineage/public_comparator/v019-linked-reader.pdf",
        V019_COMPARATOR,
    )
    add_tree(
        members,
        f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/evidence",
        EVIDENCE,
        exclude_names=EXCLUDED_EVIDENCE_NAMES,
    )
    add_file(
        members,
        f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/methods/METHODS_AI_INTERSLAVIC_NOETHER_v020.tex",
        ROOT / "docs" / "METHODS_AI_INTERSLAVIC_NOETHER_v020.tex",
    )
    for manifest_name in ("linked-reader-visual-assets.json", "methods-visual-assets.json"):
        manifest = json.loads((EVIDENCE / manifest_name).read_text(encoding="utf-8"))
        for declaration in manifest["contact_sheets"]:
            source = ROOT / declaration["path"]
            add_file(
                members,
                f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/visual/{source.parent.name}/{source.name}",
                source,
            )
    log_root = ROOT / "tmp" / "pdfs" / "isv_release_v020"
    for path in sorted(log_root.rglob("*.log"), key=lambda item: item.as_posix()):
        relative = path.relative_to(log_root).as_posix()
        add_sanitized_log(
            members,
            f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/sanitized_logs/{relative}",
            path,
        )
    return with_internal_manifest(members, EVIDENCE_ROOT, "EVIDENCE_MEMBER_SHA256.tsv", "evidence_and_provenance")


def build_one_zip(path: Path, members: dict[str, bytes]) -> dict[str, Any]:
    first = zip_payload(members)
    second = zip_payload(members)
    require(first == second, f"deterministic duplicate ZIP drift: {path}")
    install_exact(path, first)
    result = validate_zip(path, members)
    result["deterministic_duplicate_byte_identical"] = True
    return result


def main() -> int:
    authenticate_pins()
    metadata_validation = validate_public_metadata()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    source = build_one_zip(SOURCE_ZIP, source_members())
    source_receipt = {
        "schema": "noether-interslavic-source-archive-validation/1.0",
        "release_id": "NOETHER-ISV-v020",
        "generated_at": "2026-08-22T00:00:00Z",
        "status": "PASS",
        "metadata_validation": metadata_validation,
        **source,
    }
    write_json_exact(SOURCE_VALIDATION, source_receipt)

    evidence = build_one_zip(EVIDENCE_ZIP, evidence_members())
    evidence_receipt = {
        "schema": "noether-interslavic-evidence-archive-validation/1.0",
        "release_id": "NOETHER-ISV-v020",
        "generated_at": "2026-08-22T00:00:00Z",
        "status": "PASS",
        **evidence,
        "note": "This external receipt is intentionally not a member of the evidence ZIP, avoiding a self-hash cycle.",
    }
    write_json_exact(EVIDENCE_VALIDATION, evidence_receipt)

    public_three = [READER, SOURCE_ZIP, EVIDENCE_ZIP]
    manifest_payload = (
        "\n".join(f"{sha256_path(path)}\t{path.stat().st_size}\t{path.name}" for path in public_three)
        + "\n"
    ).encode("utf-8")
    install_exact(TOP_MANIFEST, manifest_payload)
    public_four = public_three + [TOP_MANIFEST]

    release_manifest = {
        "schema": "noether-interslavic-release-manifest/1.0",
        "release_id": "NOETHER-ISV-v020",
        "publication_date": "2026-08-22",
        "language": "isv",
        "scripts": ["isv-Latn", "isv-Cyrl"],
        "concept_doi": "10.5281/zenodo.21926382",
        "version_doi": "10.5281/zenodo.22058530",
        "global_catalogue_concept_doi": "10.5281/zenodo.20412587",
        "repository": "https://github.com/KokunoYumeto/emmy-noether-isv",
        "latin_editorial_head": "ISV019-EDIT-0171",
        "public_files": [file_record(path) for path in public_four],
        "source_archive_validation": source_receipt,
        "evidence_archive_validation": evidence_receipt,
        "reader": {
            **file_record(READER),
            "pages": 1159,
            "latin_pages": 565,
            "cyrillic_pages": 588,
            "front_and_divider_pages": 6,
        },
        "methods_paper": {**file_record(METHODS), "pages": 13},
        "v020_correction": {
            "latin_bytes_changed": 0,
            "role_records_reviewed": 4560,
            "classification_defects_corrected": 364,
            "missing_identity_boundaries_added": 8,
            "verified_effects": 372,
            "changed_lines": 125,
            "licensed_lines": 309,
            "unlicensed_changed_lines": 0,
        },
        "qa": {
            "release_report": file_record(EVIDENCE / "qa-report.json"),
            "visual_receipt": file_record(EVIDENCE / "visual-qa-receipt.json"),
            "projection_v7_receipt": file_record(ROOT / "decision_records" / "ISV020-CYRILLIC-V7-VALIDATION-RECEIPT.json"),
            "release_checks": 38,
            "release_errors": 0,
            "changed_pages_visually_reviewed": 86,
            "adjacent_controls_visually_reviewed": 103,
        },
        "review_and_claim_boundary": "Machine-assisted scholarly working edition. No independent native-speaker, community, official-standard, or scholarly-peer-review certification is claimed. Cyrillic is a deterministic representation, not an independent witness.",
        "repository_identity_note": "The immutable release tag and commit are recorded after public push in PUBLICATION_RECEIPT.json to avoid a self-referential file/commit hash cycle.",
    }
    write_json_exact(RELEASE_MANIFEST, release_manifest)

    with zipfile.ZipFile(SOURCE_ZIP) as source_archive, zipfile.ZipFile(EVIDENCE_ZIP) as evidence_archive:
        package_receipt = {
            "schema": "noether-interslavic-package-validation/1.0",
            "release_id": "NOETHER-ISV-v020",
            "generated_at": "2026-08-22T00:00:00Z",
            "status": "PASS",
            "public_file_count": 4,
            "public_files": [file_record(path) for path in public_four],
            "top_manifest_readback": TOP_MANIFEST.read_bytes() == manifest_payload,
            "source_zip": {
                "testzip": source_archive.testzip(),
                "members": len(source_archive.namelist()),
                "unsafe_member_names": [
                    name for name in source_archive.namelist()
                    if name.startswith("/") or ".." in PurePosixPath(name).parts
                ],
            },
            "evidence_zip": {
                "testzip": evidence_archive.testzip(),
                "members": len(evidence_archive.namelist()),
                "unsafe_member_names": [
                    name for name in evidence_archive.namelist()
                    if name.startswith("/") or ".." in PurePosixPath(name).parts
                ],
            },
            "release_manifest": file_record(RELEASE_MANIFEST),
            "credentials_included": False,
            "task_transcripts_included": False,
        }
    require(package_receipt["top_manifest_readback"], "top manifest readback failed")
    require(package_receipt["source_zip"]["testzip"] is None, "source ZIP CRC failure")
    require(package_receipt["evidence_zip"]["testzip"] is None, "evidence ZIP CRC failure")
    require(not package_receipt["source_zip"]["unsafe_member_names"], "unsafe source ZIP member")
    require(not package_receipt["evidence_zip"]["unsafe_member_names"], "unsafe evidence ZIP member")
    write_json_exact(PACKAGE_VALIDATION, package_receipt)

    print(json.dumps({
        "status": "PASS",
        "public_files": package_receipt["public_files"],
        "source_members": package_receipt["source_zip"]["members"],
        "evidence_members": package_receipt["evidence_zip"]["members"],
        "release_manifest": package_receipt["release_manifest"],
        "package_validation": file_record(PACKAGE_VALIDATION),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
