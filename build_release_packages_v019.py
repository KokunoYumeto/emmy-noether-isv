#!/usr/bin/env python3
"""Build and independently validate the four public NOETHER-ISV-v019 files."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any, Iterable, Mapping
import zipfile


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v019"
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
READER_PIN = (
    6_885_443,
    "E14B2C9336E94878370332913360ECC52935AE93A89701BC7A5AE22C0552C401",
)

SOURCE_TOOL_FILES = (
    "project_isv_cyrillic_v2.py",
    "project_isv_cyrillic_v3.py",
    "project_isv_cyrillic_v4.py",
    "project_isv_cyrillic_v5.py",
    "project_isv_cyrillic_v6.py",
    "test_project_isv_cyrillic_v2.py",
    "test_project_isv_cyrillic_v3.py",
    "test_project_isv_cyrillic_v4.py",
    "test_project_isv_cyrillic_v5.py",
    "test_project_isv_cyrillic_v6.py",
    "audit_isv_final_projection_completeness_v019.py",
    "build_isv_release_v019.py",
    "build_linked_reader_v019.py",
    "qa_isv_release_v019.py",
    "build_visual_qa_receipt_v019.py",
    "build_decision_index_v019.py",
    "build_release_packages_v019.py",
    "verify_session_independent_state_v019.ps1",
    "seal_isv_edit0171_v019.py",
)
SOURCE_SUPPORT_FILES = (
    "cyrillic_projection_v2_fixtures.json",
    "CYRILLIC_PROJECTION_V2_SPEC_v019.md",
    "CYRILLIC_PROJECTION_V2_VALIDATION_RECEIPT_v019.json",
    "CYRILLIC_PROJECTION_V3_VALIDATION_RECEIPT_v019.json",
    "CYRILLIC_PROJECTION_V4_STRUCTURAL_SIGNATURE_v019.json",
    "CYRILLIC_PROJECTION_V4_VALIDATION_RECEIPT_v019.json",
    "CYRILLIC_PROJECTION_V5_VALIDATION_RECEIPT_v019.json",
    "00_SESSION_INDEPENDENT_STATE_v019.json",
    "00_SESSION_INDEPENDENT_WORKLOG_v019.jsonl",
    "NORMALIZATION_DECISIONS_v019.jsonl",
)
EVIDENCE_ROOT_FILES = (
    "00_SESSION_INDEPENDENT_STATE_v019.json",
    "00_SESSION_INDEPENDENT_WORKFLOW_v019.md",
    "00_SESSION_INDEPENDENT_WORKLOG_v019.jsonl",
    "NORMALIZATION_DECISIONS_v019.jsonl",
    "cyrillic_projection_v2_fixtures.json",
    "CYRILLIC_PROJECTION_V2_SPEC_v019.md",
    "CYRILLIC_PROJECTION_V2_VALIDATION_RECEIPT_v019.json",
    "CYRILLIC_PROJECTION_V3_VALIDATION_RECEIPT_v019.json",
    "CYRILLIC_PROJECTION_V4_STRUCTURAL_SIGNATURE_v019.json",
    "CYRILLIC_PROJECTION_V4_VALIDATION_RECEIPT_v019.json",
    "CYRILLIC_PROJECTION_V5_VALIDATION_RECEIPT_v019.json",
    "ISV_FOREIGN_IDENTITY_FRONTIER_INDEX_VALIDATION_RECEIPT_v019.json",
)
TOOL_PREFIXES = (
    "apply_",
    "append_",
    "audit_",
    "build_",
    "harden_",
    "prepare_",
    "project_",
    "qa_",
    "repair_",
    "seal_",
    "test_",
    "verify_",
)
FORBIDDEN_MEMBER_FRAGMENTS = (
    "token.md",
    "github tokens",
    "new zenodo token",
    "__pycache__",
    ".git/",
    "codex/attachments",
)
FORBIDDEN_SECRET_PATTERNS = (
    re.compile(rb"ghp_[A-Za-z0-9]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]{20,}", re.I),
    re.compile(rb"access_token\s*=\s*[A-Za-z0-9._-]{20,}", re.I),
)
TEXT_SUFFIXES = {
    ".txt", ".md", ".json", ".jsonl", ".tsv", ".csv", ".py", ".ps1", ".tex", ".cff", ".yaml", ".yml"
}

SOURCE_BUILD_README = """# Povtorimo sestavjenje / Reproducible build

## Medžuslovjansky

Raspakujte arhiv v prazdny katalog. `source_latin/` jest jediny redagujemy jezyčny kanon; `source_cyrillic/` jest izvedena projekcija. Ne redagujte kirilicu kako oddělny prěklad.

1. `python test_project_isv_cyrillic_v6.py`
2. `python project_isv_cyrillic_v6.py --require-ready`
3. `python build_isv_release_v019.py --build`
4. `python qa_isv_release_v019.py`
5. `python build_linked_reader_v019.py`

Potrěbne sut Python 3, `pypdf`, XeLaTeX, Poppler (`pdftotext`, `pdffonts`, `pdftoppm`), PyMuPDF i Pillow za polnu vizualnu kontrolu. Build jest serijny i ne upotrěbja shell escape.

## English

Extract into an empty directory. `source_latin/` is the sole editable language canon; `source_cyrillic/` is derived. Do not edit Cyrillic as a separate translation.

Run the five commands above in order. Python 3, `pypdf`, XeLaTeX, Poppler, PyMuPDF, and Pillow are required for the complete build and visual QA. The build is serial and disables shell escape.
"""

EVIDENCE_README = """# Dokazy i pohođenje / Evidence and provenance

## Medžuslovjansky

Tutoj arhiv dokazuje, kako bylo stvorjeno izdanje `NOETHER-ISV-v019`. Glavny čitateljnik ne jest zaměnjen operacijnym dnevnikom; tehničny material jest razděljen po funkciji. Kontrolne iztočniki sut `CANON_INDEX.json`, `LATIN_FREEZE_RECEIPT_v019.json`, polny žurnal 171 rěšenij, v6 potvrđenje, build/QA potvrđenja i manifesty členov arhiva.

Historijne workflow i worklog fajly sut dokaz pohođenja, ne instrukcije za novogo agenta. Novi agent trěba najprvo čitati `CANON_INDEX.json` i živy kanon. Arhiv ne sodrživaje credentialy, task-transkripty, Git-katalog ili source-scan fajly s nerěšenymi pravami.

## English

This archive proves how `NOETHER-ISV-v019` was produced. The human reader is not replaced by an operational diary; technical material is grouped by function. Controlling evidence is the canon index, Latin freeze receipt, complete 171-decision ledger, v6 receipt, build/QA receipts, and archive member manifests.

Historical workflow and worklog files are provenance, not instructions to a future agent. A future agent should read `CANON_INDEX.json` and the live canon first. Credentials, task transcripts, Git internals, and source scans with unresolved redistribution rights are excluded.
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def file_record(path: Path) -> dict[str, Any]:
    return {"path": path.resolve().relative_to(ROOT.resolve()).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_path(path)}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def add_bytes(members: dict[str, bytes], archive_name: str, payload: bytes) -> None:
    name = PurePosixPath(archive_name).as_posix()
    if name.startswith("/") or ".." in PurePosixPath(name).parts:
        raise RuntimeError(f"unsafe archive name: {name}")
    if name in members:
        raise RuntimeError(f"duplicate archive member: {name}")
    lowered = name.casefold()
    if any(fragment in lowered for fragment in FORBIDDEN_MEMBER_FRAGMENTS):
        raise RuntimeError(f"forbidden archive member: {name}")
    suffix = PurePosixPath(name).suffix.casefold()
    if suffix in TEXT_SUFFIXES:
        for pattern in FORBIDDEN_SECRET_PATTERNS:
            if pattern.search(payload):
                raise RuntimeError(f"secret-like content rejected in {name}: {pattern.pattern!r}")
    members[name] = payload


def add_file(members: dict[str, bytes], archive_name: str, source: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f"unsafe or missing source member: {source}")
    add_bytes(members, archive_name, source.read_bytes())


def add_tree(
    members: dict[str, bytes],
    archive_root: str,
    source_root: Path,
    *,
    exclude_names: Iterable[str] = (),
) -> None:
    excluded = set(exclude_names)
    for path in sorted(source_root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.name in excluded:
            continue
        relative = path.relative_to(source_root).as_posix()
        add_file(members, f"{archive_root}/{relative}", path)


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
        "release_id": "NOETHER-ISV-v019",
        "archive_role": archive_role,
        "fixed_member_timestamp": "2026-08-22T00:00:00",
        "compression": "ZIP_DEFLATED level 9",
        "member_order": "UTF-8 path lexical order",
        "member_permissions": "regular file 0644",
        "member_manifest": f"manifests/{manifest_name}",
        "member_manifest_excludes_itself": True,
        "credentials_and_task_transcripts_excluded": True,
    }
    add_bytes(members, f"{root_name}/manifests/ARCHIVE_POLICY.json", json.dumps(policy, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    manifest_payload = member_manifest(members)
    add_bytes(members, f"{root_name}/manifests/{manifest_name}", manifest_payload)
    return members


def zip_payload(members: Mapping[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
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
        if path.is_file() and path.read_bytes() == payload:
            return
        raise FileExistsError(f"refusing to replace non-identical frozen output: {path}")
    stage = path.with_suffix(path.suffix + ".new")
    if stage.exists():
        raise FileExistsError(stage)
    stage.write_bytes(payload)
    if stage.read_bytes() != payload:
        raise RuntimeError(f"stage readback mismatch: {stage}")
    stage.replace(path)


def validate_zip(path: Path, members: Mapping[str, bytes]) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if names != sorted(members):
            raise RuntimeError(f"ZIP inventory order/topology drift: {path}")
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failure: {path}: {bad}")
        for name in names:
            payload = archive.read(name)
            if payload != members[name]:
                raise RuntimeError(f"ZIP member byte mismatch: {path}: {name}")
    return {
        "archive": file_record(path),
        "member_count": len(members),
        "uncompressed_member_bytes": sum(len(payload) for payload in members.values()),
        "crc_test": "PASS",
        "inventory_and_member_byte_readback": "PASS",
    }


def write_json_exact(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    if path.exists() and path.read_bytes() != payload:
        path.write_bytes(payload)
    elif not path.exists():
        path.write_bytes(payload)
    if json.loads(path.read_text(encoding="utf-8")) != value:
        raise RuntimeError(f"JSON readback mismatch: {path}")


def source_members() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    add_bytes(members, f"{SOURCE_ROOT}/README.md", SOURCE_BUILD_README.encode("utf-8"))
    add_file(members, f"{SOURCE_ROOT}/PUBLIC_RELEASE_README.md", RELEASE / "README.md")
    add_file(members, f"{SOURCE_ROOT}/CANON_INDEX.json", RELEASE / "CANON_INDEX.json")
    add_tree(members, f"{SOURCE_ROOT}/LICENSES", RELEASE / "LICENSES")
    add_tree(members, f"{SOURCE_ROOT}/metadata", RELEASE / "metadata")
    add_tree(members, f"{SOURCE_ROOT}/source_latin", ROOT / "source_latin")
    add_tree(members, f"{SOURCE_ROOT}/source_cyrillic", ROOT / "source_cyrillic")
    add_tree(members, f"{SOURCE_ROOT}/assets", ROOT / "assets")
    add_file(
        members,
        f"{SOURCE_ROOT}/release_v019/source/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex",
        RELEASE / "source" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/docs/METHODS_AI_INTERSLAVIC_NOETHER_v019.tex",
        RELEASE / "source" / "METHODS_AI_INTERSLAVIC_NOETHER_v019.tex",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/docs/AI_INTERSLAVIC_NOETHER_METHODS_v019.pdf",
        EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v019.pdf",
    )
    for name in SOURCE_TOOL_FILES:
        add_file(members, f"{SOURCE_ROOT}/{name}", ROOT / name)
    for name in SOURCE_SUPPORT_FILES:
        add_file(members, f"{SOURCE_ROOT}/{name}", ROOT / name)
    add_file(
        members,
        f"{SOURCE_ROOT}/decision_records/ISV019-EDIT-0171.json",
        ROOT / "decision_records" / "ISV019-EDIT-0171.json",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/decision_records/ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json",
        ROOT / "decision_records" / "ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/decision_records/ISV019-CYR2-EDIT0153-STRUCTURAL-IDENTITY-MANIFEST.json",
        ROOT / "decision_records" / "ISV019-CYR2-EDIT0153-STRUCTURAL-IDENTITY-MANIFEST.json",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/CYRILLIC_PROJECTION_V6_VALIDATION_RECEIPT_v019.json",
        EVIDENCE / "CYRILLIC_PROJECTION_V6_VALIDATION_RECEIPT_v019.json",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/LATIN_FREEZE_RECEIPT_v019.json",
        EVIDENCE / "LATIN_FREEZE_RECEIPT_v019.json",
    )
    return with_internal_manifest(members, SOURCE_ROOT, "SOURCE_MEMBER_SHA256.tsv", "editable_sources")


def evidence_members() -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    add_bytes(members, f"{EVIDENCE_ROOT}/00_README_EVIDENCE.md", EVIDENCE_README.encode("utf-8"))
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/README.md", RELEASE / "README.md")
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/CANON_INDEX.json", RELEASE / "CANON_INDEX.json")
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/RELEASE_WORKLOG.jsonl", RELEASE / "RELEASE_WORKLOG.jsonl")
    add_tree(members, f"{EVIDENCE_ROOT}/01_release_identity/metadata", RELEASE / "metadata")
    add_file(members, f"{EVIDENCE_ROOT}/02_source_authority/SOURCE_AUTHORITY.json", RELEASE / "metadata" / "SOURCE_AUTHORITY.json")

    add_file(members, f"{EVIDENCE_ROOT}/03_v019_linguistic_lineage/NORMALIZATION_DECISIONS_v019.jsonl", ROOT / "NORMALIZATION_DECISIONS_v019.jsonl")
    add_tree(members, f"{EVIDENCE_ROOT}/03_v019_linguistic_lineage/decision_records", ROOT / "decision_records")
    for name in ("DECISION_INDEX.json", "REJECTED_ALTERNATIVES_INDEX.jsonl", "APPLIED_EDIT_MANIFEST.tsv"):
        add_file(members, f"{EVIDENCE_ROOT}/03_v019_linguistic_lineage/{name}", EVIDENCE / name)
    for path in sorted(ROOT.glob("*.py"), key=lambda item: item.name):
        if path.name.startswith(TOOL_PREFIXES):
            add_file(members, f"{EVIDENCE_ROOT}/03_v019_linguistic_lineage/tools/{path.name}", path)
    for name in EVIDENCE_ROOT_FILES:
        add_file(members, f"{EVIDENCE_ROOT}/03_v019_linguistic_lineage/control_and_projection/{name}", ROOT / name)
    add_tree(members, f"{EVIDENCE_ROOT}/04_mathematical_intelligibility/producer_units", ROOT / "producer_units")

    add_file(members, f"{EVIDENCE_ROOT}/06_normalization_boundaries_and_script/CYRILLIC_PROJECTION_V6_VALIDATION_RECEIPT_v019.json", EVIDENCE / "CYRILLIC_PROJECTION_V6_VALIDATION_RECEIPT_v019.json")
    add_file(members, f"{EVIDENCE_ROOT}/06_normalization_boundaries_and_script/LATIN_FREEZE_RECEIPT_v019.json", EVIDENCE / "LATIN_FREEZE_RECEIPT_v019.json")
    add_file(members, f"{EVIDENCE_ROOT}/06_normalization_boundaries_and_script/final_role_inventory.json", ROOT / "decision_records" / "ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json")

    add_tree(
        members,
        f"{EVIDENCE_ROOT}/07_build_render_and_content_qa/evidence",
        EVIDENCE,
        exclude_names=("EVIDENCE_ARCHIVE_VALIDATION.json", "PACKAGE_VALIDATION.json", "PUBLICATION_RECEIPT.json"),
    )
    add_file(members, f"{EVIDENCE_ROOT}/07_build_render_and_content_qa/methods/METHODS_AI_INTERSLAVIC_NOETHER_v019.tex", RELEASE / "source" / "METHODS_AI_INTERSLAVIC_NOETHER_v019.tex")
    for path, archive_name in (
        (ROOT / "tmp/pdfs/isv_release_v019/visual/linked-reader/contact-front-boundaries.png", "contact-front-boundaries.png"),
        (ROOT / "tmp/pdfs/isv_release_v019/visual/linked-reader/contact-latin-samples.png", "contact-latin-samples.png"),
        (ROOT / "tmp/pdfs/isv_release_v019/visual/linked-reader/contact-cyrillic-samples.png", "contact-cyrillic-samples.png"),
        (ROOT / "tmp/pdfs/isv_release_v019/visual/methods/contact-methods.png", "contact-methods.png"),
    ):
        add_file(members, f"{EVIDENCE_ROOT}/07_build_render_and_content_qa/visual/{archive_name}", path)
    log_root = ROOT / "tmp" / "pdfs" / "isv_release_v019"
    for path in sorted(log_root.rglob("*.log"), key=lambda item: item.as_posix()):
        relative = path.relative_to(log_root).as_posix()
        add_file(members, f"{EVIDENCE_ROOT}/07_build_render_and_content_qa/logs/{relative}", path)

    for name in ("00_SESSION_INDEPENDENT_STATE_v019.json", "00_SESSION_INDEPENDENT_WORKFLOW_v019.md", "00_SESSION_INDEPENDENT_WORKLOG_v019.jsonl"):
        add_file(members, f"{EVIDENCE_ROOT}/08_custody_and_version_lineage/historical_non_controlling/{name}", ROOT / name)
    add_tree(members, f"{EVIDENCE_ROOT}/09_rights_privacy_and_exclusions/LICENSES", RELEASE / "LICENSES")
    return with_internal_manifest(members, EVIDENCE_ROOT, "EVIDENCE_MEMBER_SHA256.tsv", "evidence_and_provenance")


def build_one_zip(path: Path, members: dict[str, bytes]) -> dict[str, Any]:
    first = zip_payload(members)
    second = zip_payload(members)
    if first != second:
        raise RuntimeError(f"deterministic duplicate ZIP drift: {path}")
    install_exact(path, first)
    result = validate_zip(path, members)
    result["deterministic_duplicate_byte_identical"] = True
    result["member_inventory_sha256"] = sha256_bytes(member_manifest(members))
    return result


def main() -> int:
    if (READER.stat().st_size, sha256_path(READER)) != READER_PIN:
        raise RuntimeError("linked reader pin drift")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    source = build_one_zip(SOURCE_ZIP, source_members())
    source_receipt = {
        "schema": "noether-interslavic-source-archive-validation/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-22T00:00:00Z",
        "status": "PASS",
        **source,
    }
    write_json_exact(SOURCE_VALIDATION, source_receipt)

    evidence = build_one_zip(EVIDENCE_ZIP, evidence_members())
    evidence_receipt = {
        "schema": "noether-interslavic-evidence-archive-validation/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-22T00:00:00Z",
        "status": "PASS",
        **evidence,
        "note": "This external receipt is intentionally not a member of the evidence ZIP, avoiding a self-hash cycle.",
    }
    write_json_exact(EVIDENCE_VALIDATION, evidence_receipt)

    public_three = [READER, SOURCE_ZIP, EVIDENCE_ZIP]
    manifest_lines = [
        f"{sha256_path(path)}\t{path.stat().st_size}\t{path.name}" for path in public_three
    ]
    manifest_payload = ("\n".join(manifest_lines) + "\n").encode("utf-8")
    install_exact(TOP_MANIFEST, manifest_payload)
    public_four = public_three + [TOP_MANIFEST]

    release_manifest = {
        "schema": "noether-interslavic-release-manifest/1.0",
        "release_id": "NOETHER-ISV-v019",
        "publication_date": "2026-08-22",
        "language": "isv",
        "scripts": ["isv-Latn", "isv-Cyrl"],
        "concept_doi": "10.5281/zenodo.21926382",
        "version_doi": "10.5281/zenodo.22050935",
        "global_catalogue_concept_doi": "10.5281/zenodo.20412587",
        "repository": "https://github.com/KokunoYumeto/emmy-noether-isv",
        "editorial_head": "ISV019-EDIT-0171",
        "public_files": [file_record(path) for path in public_four],
        "source_archive_validation": source_receipt,
        "evidence_archive_validation": evidence_receipt,
        "reader": {**file_record(READER), "pages": 1159, "latin_pages": 565, "cyrillic_pages": 588, "front_and_divider_pages": 6},
        "methods_paper": {**file_record(EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v019.pdf"), "pages": 6},
        "qa": {
            "release_report": file_record(EVIDENCE / "qa-report.json"),
            "visual_receipt": file_record(EVIDENCE / "visual-qa-receipt.json"),
            "projection_v6_receipt": file_record(EVIDENCE / "CYRILLIC_PROJECTION_V6_VALIDATION_RECEIPT_v019.json"),
            "release_checks": 38,
            "release_errors": 0,
        },
        "review_and_claim_boundary": "Machine-assisted scholarly working edition. No independent native-speaker, community, official-standard, or scholarly-peer-review certification is claimed. Cyrillic is a deterministic representation, not an independent witness.",
        "repository_identity_note": "The immutable release tag and commit are recorded after the public push in PUBLICATION_RECEIPT.json to avoid a self-referential file/commit hash cycle.",
    }
    write_json_exact(RELEASE_MANIFEST, release_manifest)

    with zipfile.ZipFile(SOURCE_ZIP) as source_archive, zipfile.ZipFile(EVIDENCE_ZIP) as evidence_archive:
        package_receipt = {
            "schema": "noether-interslavic-package-validation/1.0",
            "release_id": "NOETHER-ISV-v019",
            "generated_at": "2026-08-22T00:00:00Z",
            "status": "PASS",
            "public_file_count": 4,
            "public_files": [file_record(path) for path in public_four],
            "top_manifest_readback": TOP_MANIFEST.read_bytes() == manifest_payload,
            "source_zip": {
                "testzip": source_archive.testzip(),
                "members": len(source_archive.namelist()),
                "unsafe_member_names": [name for name in source_archive.namelist() if name.startswith("/") or ".." in PurePosixPath(name).parts],
            },
            "evidence_zip": {
                "testzip": evidence_archive.testzip(),
                "members": len(evidence_archive.namelist()),
                "unsafe_member_names": [name for name in evidence_archive.namelist() if name.startswith("/") or ".." in PurePosixPath(name).parts],
            },
            "release_manifest": file_record(RELEASE_MANIFEST),
            "credentials_included": False,
            "task_transcripts_included": False,
        }
    if not package_receipt["top_manifest_readback"] or package_receipt["source_zip"]["testzip"] or package_receipt["evidence_zip"]["testzip"]:
        raise RuntimeError("package validation failed")
    if package_receipt["source_zip"]["unsafe_member_names"] or package_receipt["evidence_zip"]["unsafe_member_names"]:
        raise RuntimeError("unsafe ZIP member names")
    write_json_exact(PACKAGE_VALIDATION, package_receipt)
    print(
        json.dumps(
            {
                "status": "PASS",
                "public_files": package_receipt["public_files"],
                "source_members": package_receipt["source_zip"]["members"],
                "evidence_members": package_receipt["evidence_zip"]["members"],
                "release_manifest": package_receipt["release_manifest"],
                "package_validation": file_record(PACKAGE_VALIDATION),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
