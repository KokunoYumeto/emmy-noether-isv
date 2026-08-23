#!/usr/bin/env python3
"""Independently replay and validate the frozen NOETHER-ISV-v020 packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any
import zipfile


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v020"
PUBLIC = RELEASE / "public"
EVIDENCE = RELEASE / "evidence"
SOURCE_ZIP = PUBLIC / "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip"
EVIDENCE_ZIP = PUBLIC / "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip"
TOP_MANIFEST = PUBLIC / "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt"
RELEASE_MANIFEST = RELEASE / "RELEASE_MANIFEST.json"
OUTPUT = EVIDENCE / "PUBLIC_PACKAGE_REPLAY_VALIDATION.json"
PUBLIC_NAMES = (
    "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf",
    "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip",
    "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip",
    "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_path(path),
    }


def parse_top_manifest() -> list[dict[str, Any]]:
    rows = []
    for line in TOP_MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, byte_text, name = line.split("\t")
        path = PUBLIC / name
        require(path.is_file(), f"manifest target missing: {name}")
        require(path.stat().st_size == int(byte_text), f"manifest byte drift: {name}")
        require(sha256_path(path) == digest, f"manifest hash drift: {name}")
        rows.append({"name": name, "bytes": int(byte_text), "sha256": digest})
    require([row["name"] for row in rows] == list(PUBLIC_NAMES[:3]), "top manifest topology drift")
    return rows


def validate_zip_inventory(path: Path, expected_root: str) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        require(names == sorted(names), f"ZIP order drift: {path}")
        require(archive.testzip() is None, f"ZIP CRC failure: {path}")
        require(len(names) == len(set(names)), f"duplicate ZIP members: {path}")
        for name in names:
            pure = PurePosixPath(name)
            require(not name.startswith("/") and ".." not in pure.parts, f"unsafe ZIP path: {name}")
            require(pure.parts and pure.parts[0] == expected_root, f"unexpected ZIP root: {name}")
        top_manifest_prefix = f"{expected_root}/manifests/"
        internal_manifest_names = [
            name
            for name in names
            if name.startswith(top_manifest_prefix)
            and "/" not in name[len(top_manifest_prefix):]
            and name.endswith("_MEMBER_SHA256.tsv")
        ]
        require(len(internal_manifest_names) == 1, f"internal manifest topology drift: {path}")
        manifest_name = internal_manifest_names[0]
        manifest_rows = archive.read(manifest_name).decode("utf-8").splitlines()
        require(manifest_rows and manifest_rows[0] == "SHA256\tBYTES\tPATH", f"bad internal header: {path}")
        expected_members = [name for name in names if name != manifest_name]
        observed_members = []
        for row in manifest_rows[1:]:
            digest, byte_text, name = row.split("\t")
            payload = archive.read(name)
            require(len(payload) == int(byte_text), f"internal byte drift: {path}: {name}")
            require(sha256_bytes(payload) == digest, f"internal hash drift: {path}: {name}")
            observed_members.append(name)
        require(observed_members == expected_members, f"internal member manifest coverage drift: {path}")
        return {
            "archive": record(path),
            "members": len(names),
            "crc": "PASS",
            "safe_topology": "PASS",
            "internal_manifest": manifest_name,
            "internal_manifest_rows": len(observed_members),
            "internal_member_hash_readback": "PASS",
        }


def extract_safe(archive: zipfile.ZipFile, destination: Path) -> None:
    for info in archive.infolist():
        pure = PurePosixPath(info.filename)
        require(not info.filename.startswith("/") and ".." not in pure.parts, f"unsafe extract path: {info.filename}")
        target = destination.joinpath(*pure.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(info.filename))


def normalized_process_record(result: subprocess.CompletedProcess[bytes], ephemeral: Path) -> dict[str, Any]:
    before_variants = {
        str(ephemeral).encode("utf-8"),
        str(ephemeral).replace("\\", "/").encode("utf-8"),
    }
    stdout, stderr = result.stdout, result.stderr
    for before in before_variants:
        stdout = stdout.replace(before, b"<EXTRACT_ROOT>")
        stderr = stderr.replace(before, b"<EXTRACT_ROOT>")
    return {
        "exit_code": result.returncode,
        "stdout_bytes": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_bytes": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
    }


def replay_source_archive() -> dict[str, Any]:
    tmp_parent = ROOT / "tmp"
    tmp_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isv020-package-replay-", dir=tmp_parent) as temporary:
        temporary_path = Path(temporary)
        with zipfile.ZipFile(SOURCE_ZIP, "r") as archive:
            extract_safe(archive, temporary_path)
        extracted = temporary_path / "NOETHER_INTERSLAVIC_EDITABLE_SOURCES"
        require(extracted.is_dir(), "extracted source root missing")
        canon = json.loads((extracted / "CANON_INDEX.json").read_text(encoding="utf-8"))
        for surface in ("interslavic_canon", "cyrillic_projection"):
            for declared in canon["authority_chain"][surface]["files"]:
                path = extracted / declared["path"]
                require(path.stat().st_size == declared["bytes"], f"extracted source byte drift: {path}")
                require(sha256_path(path) == declared["sha256"], f"extracted source hash drift: {path}")
        commands = (
            [sys.executable, "test_project_isv_cyrillic_v7.py"],
            [sys.executable, "project_isv_cyrillic_v7.py", "--full-report"],
        )
        runs = []
        for command in commands:
            result = subprocess.run(
                command,
                cwd=extracted,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=180,
            )
            row = normalized_process_record(result, temporary_path)
            row["command"] = ["python", *command[1:]]
            require(result.returncode == 0, f"extracted replay failed: {row}")
            runs.append(row)
        return {
            "temporary_tree_removed_after_replay": True,
            "canonical_and_derived_files_authenticated": 8,
            "commands": runs,
            "status": "PASS",
        }


def write_exact(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    if path.exists():
        require(path.read_bytes() == payload, f"refusing to replace frozen replay receipt: {path}")
    else:
        path.write_bytes(payload)
    require(json.loads(path.read_text(encoding="utf-8")) == value, "replay receipt readback mismatch")


def main() -> int:
    require(all((PUBLIC / name).is_file() for name in PUBLIC_NAMES), "public four incomplete")
    public_rows = parse_top_manifest()
    release_manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    require(release_manifest["release_id"] == "NOETHER-ISV-v020", "release identity drift")
    expected_public = [record(PUBLIC / name) for name in PUBLIC_NAMES]
    require(release_manifest["public_files"] == expected_public, "release manifest/public byte drift")
    source_inventory = validate_zip_inventory(SOURCE_ZIP, "NOETHER_INTERSLAVIC_EDITABLE_SOURCES")
    evidence_inventory = validate_zip_inventory(EVIDENCE_ZIP, "NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE")
    replay = replay_source_archive()
    receipt = {
        "schema": "noether-interslavic-public-package-replay-validation/1.0",
        "release_id": "NOETHER-ISV-v020",
        "generated_at": "2026-08-22T00:00:00Z",
        "status": "PASS",
        "public_files": expected_public,
        "top_manifest_rows": public_rows,
        "release_manifest": record(RELEASE_MANIFEST),
        "source_zip": source_inventory,
        "evidence_zip": evidence_inventory,
        "extracted_source_replay": replay,
    }
    write_exact(OUTPUT, receipt)
    print(json.dumps({"status": "PASS", "receipt": record(OUTPUT), "replay": replay}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
