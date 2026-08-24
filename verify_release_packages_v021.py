#!/usr/bin/env python3
"""Independently replay and validate the frozen NOETHER-ISV-v021 packages."""

from __future__ import annotations

import hashlib
import bisect
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any
import zipfile


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v021"
PUBLIC = RELEASE / "public"
EVIDENCE = RELEASE / "evidence"
SOURCE_ZIP = PUBLIC / "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip"
EVIDENCE_ZIP = PUBLIC / "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip"
TOP_MANIFEST = PUBLIC / "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt"
RELEASE_MANIFEST = RELEASE / "RELEASE_MANIFEST.json"
OUTPUT = EVIDENCE / "PUBLIC_PACKAGE_REPLAY_VALIDATION.json"
FIXED_ZIP_TIME = (2026, 8, 24, 0, 0, 0)
SOURCE_ROOT = "NOETHER_INTERSLAVIC_EDITABLE_SOURCES"
EVIDENCE_ROOT = "NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE"
PORTABLE_PROJECTION_VERIFIER = "verify_cyrillic_v8_independent.py"
PORTABLE_V2 = "comparison/predecessor_v019/project_isv_cyrillic_v2.py"
PUBLIC_NAMES = (
    "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf",
    "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip",
    "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip",
    "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt",
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
    "00_session_independent_state",
    "00_session_independent_worklog",
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
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
WINDOWS_FORBIDDEN_CHARS = frozenset('<>"|?*')
WINDOWS_RESERVED_STEMS = frozenset({
    "con", "prn", "aux", "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
})


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


def validate_member_name(name: str, expected_root: str | None = None) -> PurePosixPath:
    require(name != "", "empty ZIP member name")
    require("\x00" not in name, f"NUL in ZIP member name: {name!r}")
    require("\\" not in name, f"Windows separator in ZIP member name: {name}")
    require(":" not in name and WINDOWS_DRIVE_RE.match(name) is None, f"Windows drive/stream syntax in ZIP member name: {name}")
    require(not name.startswith(("/", "//")), f"absolute/UNC ZIP member name: {name}")
    pure = PurePosixPath(name)
    require(not pure.is_absolute(), f"absolute ZIP member name: {name}")
    require(pure.as_posix() == name, f"non-canonical ZIP member name: {name}")
    require(all(part not in ("", ".", "..") for part in pure.parts), f"traversal ZIP member name: {name}")
    require(not name.endswith("/"), f"directory ZIP member is forbidden: {name}")
    for part in pure.parts:
        require(not part.endswith((" ", ".")), f"Windows-normalized ZIP member component: {name}")
        require(not any(ord(character) < 32 for character in part), f"control character in ZIP member name: {name!r}")
        require(not WINDOWS_FORBIDDEN_CHARS.intersection(part), f"Windows-forbidden character in ZIP member name: {name}")
        stem = part.split(".", 1)[0].casefold()
        require(stem not in WINDOWS_RESERVED_STEMS, f"Windows-reserved ZIP member component: {name}")
    if expected_root is not None:
        require(pure.parts and pure.parts[0] == expected_root, f"unexpected ZIP root: {name}")
    return pure


def require_under_root(path: Path, root: Path, label: str) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise RuntimeError(f"{label} escapes extraction root: {path}") from error
    require(resolved != resolved_root, f"{label} resolves to extraction root")
    return resolved


def validate_public_topology() -> None:
    require(PUBLIC.is_dir() and not PUBLIC.is_symlink(), "public directory is missing or unsafe")
    entries = sorted(path.name for path in PUBLIC.iterdir())
    require(entries == sorted(PUBLIC_NAMES), f"public directory topology drift: {entries}")
    for name in PUBLIC_NAMES:
        path = PUBLIC / name
        require(path.is_file() and not path.is_symlink(), f"public file is missing or unsafe: {name}")


def validate_public_text_payload(name: str, payload: bytes) -> None:
    lowered_name = name.casefold()
    require(
        not any(fragment in lowered_name for fragment in FORBIDDEN_MEMBER_FRAGMENTS),
        f"forbidden public member: {name}",
    )
    if PurePosixPath(name).suffix.casefold() not in TEXT_SUFFIXES:
        return
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        require(pattern.search(payload) is None, f"secret-like public content: {name}")
    profile = Path.home()
    private_markers = {
        str(profile).encode("utf-8"),
        str(profile).replace("\\", "/").encode("utf-8"),
        profile.name.encode("utf-8"),
    }
    folded_payload = payload.lower()
    for marker in private_markers:
        require(
            not marker or marker.lower() not in folded_payload,
            f"local profile identity in public text payload: {name}",
        )


def parse_top_manifest() -> list[dict[str, Any]]:
    rows = []
    for line in TOP_MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, byte_text, name = line.split("\t")
        require(name in PUBLIC_NAMES[:3], f"unexpected top-manifest target: {name}")
        require(re.fullmatch(r"[0-9A-F]{64}", digest) is not None, f"invalid top-manifest digest: {name}")
        require(re.fullmatch(r"[0-9]+", byte_text) is not None, f"invalid top-manifest byte count: {name}")
        path = PUBLIC / name
        require(path.is_file() and not path.is_symlink(), f"manifest target missing or unsafe: {name}")
        require(path.stat().st_size == int(byte_text), f"manifest byte drift: {name}")
        require(sha256_path(path) == digest, f"manifest hash drift: {name}")
        rows.append({"name": name, "bytes": int(byte_text), "sha256": digest})
    require([row["name"] for row in rows] == list(PUBLIC_NAMES[:3]), "top manifest topology drift")
    return rows


def deterministic_zip_rebuild(path: Path, archive: zipfile.ZipFile, names: list[str]) -> dict[str, Any]:
    with tempfile.TemporaryFile(mode="w+b") as rebuilt:
        with zipfile.ZipFile(
            rebuilt,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as candidate:
            for name in names:
                info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.flag_bits |= 0x800
                candidate.writestr(
                    info,
                    archive.read(name),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
        rebuilt.seek(0, os.SEEK_END)
        rebuilt_bytes = rebuilt.tell()
        rebuilt.seek(0)
        digest = hashlib.sha256()
        with path.open("rb") as frozen:
            while True:
                rebuilt_chunk = rebuilt.read(1024 * 1024)
                frozen_chunk = frozen.read(1024 * 1024)
                require(rebuilt_chunk == frozen_chunk, f"deterministic ZIP byte replay drift: {path}")
                if not rebuilt_chunk:
                    break
                digest.update(rebuilt_chunk)
    require(rebuilt_bytes == path.stat().st_size, f"deterministic ZIP size replay drift: {path}")
    rebuilt_sha256 = digest.hexdigest().upper()
    require(rebuilt_sha256 == sha256_path(path), f"deterministic ZIP hash replay drift: {path}")
    return {
        "rebuilt_bytes": rebuilt_bytes,
        "rebuilt_sha256": rebuilt_sha256,
        "byte_identical_to_frozen_archive": True,
    }


def validate_zip_inventory(path: Path, expected_root: str) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"ZIP is missing or unsafe: {path}")
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        require(names == sorted(names), f"ZIP order drift: {path}")
        require(archive.testzip() is None, f"ZIP CRC failure: {path}")
        require(len(names) == len(set(names)), f"duplicate ZIP members: {path}")
        require(archive.comment == b"", f"unexpected ZIP archive comment: {path}")
        for info in archive.infolist():
            name = info.filename
            validate_member_name(name, expected_root)
            mode = info.external_attr >> 16
            require(info.date_time == FIXED_ZIP_TIME, f"ZIP timestamp drift: {path}: {name}")
            require(info.compress_type == zipfile.ZIP_DEFLATED, f"ZIP compression drift: {path}: {name}")
            require(info.create_system == 3, f"ZIP origin-system drift: {path}: {name}")
            require(stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o644, f"ZIP permission/type drift: {path}: {name}")
            require(not (info.flag_bits & 0x1), f"encrypted ZIP member is forbidden: {path}: {name}")
            validate_public_text_payload(name, archive.read(name))
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
        deterministic_replay = deterministic_zip_rebuild(path, archive, names)
        return {
            "archive": record(path),
            "members": len(names),
            "crc": "PASS",
            "safe_topology": "PASS",
            "zip_policy": {
                "fixed_timestamp": "2026-08-24T00:00:00",
                "compression": "ZIP_DEFLATED level 9",
                "origin_system": "Unix (3)",
                "member_permissions": "regular file 0644",
                "status": "PASS",
            },
            "secret_and_local_identity_scan": "PASS",
            "internal_manifest": manifest_name,
            "internal_manifest_rows": len(observed_members),
            "internal_member_hash_readback": "PASS",
            "deterministic_archive_replay": deterministic_replay,
        }


def extract_safe(archive: zipfile.ZipFile, destination: Path) -> None:
    require(destination.is_dir() and not destination.is_symlink(), f"unsafe extraction root: {destination}")
    for info in archive.infolist():
        pure = validate_member_name(info.filename)
        target = destination.joinpath(*pure.parts)
        require_under_root(target, destination, f"ZIP member {info.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        require_under_root(target.parent, destination, f"ZIP member parent {info.filename}")
        require(not target.exists(), f"refusing to overwrite extracted member: {info.filename}")
        with target.open("xb") as handle:
            handle.write(archive.read(info))


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_payload(raw: bytes, label: str) -> Any:
    require(raw.endswith(b"\n") and b"\r" not in raw, f"JSON transport drift: {label}")
    require(not raw.startswith(b"\xef\xbb\xbf"), f"JSON BOM forbidden: {label}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_json_keys)


def identity(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    return {"bytes": path.stat().st_size, "sha256": sha256_path(path)}


def extracted_file(extracted: Path, relative_name: str, label: str) -> Path:
    require(isinstance(relative_name, str), f"non-string extracted path declaration: {label}")
    pure = validate_member_name(relative_name)
    path = extracted.joinpath(*pure.parts)
    require_under_root(path, extracted, label)
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe extracted file: {label}: {relative_name}")
    return path


def line_tables(text: str) -> tuple[list[int], list[int], list[str]]:
    scalar_starts = [0]
    byte_starts = [0]
    scalar_cursor = 0
    byte_cursor = 0
    physical = text.splitlines(keepends=True)
    for line in physical[:-1]:
        scalar_cursor += len(line)
        byte_cursor += len(line.encode("utf-8"))
        scalar_starts.append(scalar_cursor)
        byte_starts.append(byte_cursor)
    return scalar_starts, byte_starts, text.splitlines()


def locator(text: str, scalar_offset: int, tables: tuple[list[int], list[int], list[str]]) -> dict[str, Any]:
    scalar_starts, byte_starts, lines = tables
    line_index = bisect.bisect_right(scalar_starts, scalar_offset) - 1
    column_zero = scalar_offset - scalar_starts[line_index]
    line = lines[line_index] if line_index < len(lines) else ""
    context = text[max(0, scalar_offset - 80) : min(len(text), scalar_offset + 160)]
    return {
        "line": line_index + 1,
        "column": column_zero + 1,
        "byte_offset": byte_starts[line_index] + len(line[:column_zero].encode("utf-8")),
        "line_sha256": sha256_bytes(line.encode("utf-8")),
        "context_sha256": sha256_bytes(context.encode("utf-8")),
    }


def validate_rebased_role_manifest(extracted: Path, canon: dict[str, Any]) -> dict[str, Any]:
    projection = canon["authority_chain"]["cyrillic_projection"]
    declared = projection["reviewed_role_manifest"]
    path = extracted_file(extracted, declared["path"], "rebased role manifest")
    raw = path.read_bytes()
    require(len(raw) == declared["bytes"] and sha256_bytes(raw) == declared["sha256"], "rebased role-manifest pin drift")
    manifest = strict_json_payload(raw, "rebased role manifest")
    claimed_internal = manifest.pop("inventory_sha256_excluding_this_field")
    require(sha256_bytes(canonical_json(manifest)) == claimed_internal, "rebased role-manifest internal digest drift")
    manifest["inventory_sha256_excluding_this_field"] = claimed_internal
    require(manifest.get("status") == "REBASED_FULLY_REVIEWED_ZERO_AMBIGUITY_BINDING_V021_GATE", "rebased role-manifest status drift")
    require(manifest["scope"]["successor_release"] == "NOETHER-ISV-v021", "rebased role-manifest release drift")
    require(manifest["scope"]["latin_editorial_head"] == "ISV021-EDIT-0012", "rebased role-manifest head drift")
    if "internal_sha256" in declared:
        require(declared["internal_sha256"] == claimed_internal, "canon/role-manifest internal digest drift")
    categories = (
        "unprotected_style_payloads",
        "unprotected_name_candidates",
        "unprotected_foreign_lexicon_hits",
        "visible_one_letter_tokens",
        "additional_protected_spans",
        "v021_roman_identity_spans",
    )
    texts: dict[str, str] = {}
    for row in canon["authority_chain"]["interslavic_canon"]["files"]:
        source_path = extracted_file(extracted, row["path"], "Latin canon source")
        require(source_path.name not in texts, f"duplicate Latin canon basename: {source_path.name}")
        texts[source_path.name] = source_path.read_text(encoding="utf-8")
    tables = {name: line_tables(text) for name, text in texts.items()}
    rows_checked = 0
    protected_rows = 0
    for category in categories:
        seen: set[tuple[str, int, int]] = set()
        for row in manifest[category]:
            filename = row["file"]
            start, end = row["scalar_span"]
            surface = row["surface"]
            require(filename in texts and texts[filename][start:end] == surface, f"manifest surface drift: {category}:{filename}:{start}")
            require(sha256_bytes(surface.encode("utf-8")) == row["surface_sha256"], f"manifest surface hash drift: {category}:{filename}:{start}")
            observed = locator(texts[filename], start, tables[filename])
            for key, value in observed.items():
                require(row[key] == value, f"manifest locator drift: {category}:{filename}:{start}:{key}")
            key = (filename, start, end)
            require(key not in seen, f"duplicate manifest span: {category}:{key}")
            seen.add(key)
            protected_rows += str(row.get("disposition", "")).startswith(("PROTECT", "PRESERVE"))
            rows_checked += 1
    require(rows_checked == 5_290, f"source-bound manifest row drift: {rows_checked}")
    require(protected_rows == 2_702, f"protected-row drift including Roman identities: {protected_rows}")
    return {
        "manifest": {"path": declared["path"], "bytes": len(raw), "sha256": sha256_bytes(raw), "internal_sha256": claimed_internal},
        "rows_replayed": rows_checked,
        "protected_rows_including_roman_identities": protected_rows,
        "locator_surface_and_hash_replay": "PASS",
    }


def validate_portable_derivation_map(extracted: Path, canon: dict[str, Any]) -> dict[str, Any]:
    declaration = canon["_portable_derivation"]
    require(
        declaration.get("schema") == "noether-interslavic-portable-canon-index/1.0",
        "portable canon derivation schema drift",
    )
    path = extracted_file(extracted, declaration["path_binding_manifest"], "portable derivation map")
    mapping = strict_json_payload(path.read_bytes(), "portable derivation map")
    require(mapping.get("release_id") == "NOETHER-ISV-v021", "portable derivation-map release drift")
    require(mapping.get("status") == "PASS_NO_LOCAL_PROFILE_IDENTITY", "portable derivation-map status drift")
    projection = canon["authority_chain"]["cyrillic_projection"]
    replay = projection["portable_replay"]
    mapped_replay = mapping["portable_replay"]
    require(
        mapped_replay["verifier"]
        == {"bytes": replay["independent_verifier"]["bytes"], "sha256": replay["independent_verifier"]["sha256"]},
        "portable derivation-map verifier pin drift",
    )
    require(
        mapped_replay["v2"]
        == {"bytes": replay["v2_authority"]["bytes"], "sha256": replay["v2_authority"]["sha256"]},
        "portable derivation-map v2 pin drift",
    )
    role = projection["reviewed_role_manifest"]
    require(
        mapped_replay["role_manifest"]
        == {"bytes": role["bytes"], "sha256": role["sha256"], "internal_sha256": role["internal_sha256"]},
        "portable derivation-map role-manifest pin drift",
    )
    return {
        "path": declaration["path_binding_manifest"],
        **identity(path),
        "derivatives": len(mapping.get("derivatives", [])),
        "status": "PASS",
    }


def replay_cyrillic_portably(
    extracted: Path,
    temporary_path: Path,
    canon: dict[str, Any],
) -> dict[str, Any]:
    projection = canon["authority_chain"]["cyrillic_projection"]
    declaration = projection["portable_replay"]
    require(
        declaration.get("status") == "RUNNABLE_FAIL_CLOSED_IN_EXTRACTED_SOURCE_ARCHIVE",
        "portable projection declaration is not runnable PASS",
    )
    verifier_declaration = declaration["independent_verifier"]
    v2_declaration = declaration["v2_authority"]
    require(verifier_declaration["path"] == PORTABLE_PROJECTION_VERIFIER, "portable verifier path declaration drift")
    require(v2_declaration["path"] == PORTABLE_V2, "portable v2 path declaration drift")
    require(declaration["expected_outputs"] == projection["files"], "portable expected-output declaration drift")
    verifier_path = extracted_file(extracted, verifier_declaration["path"], "portable projection verifier")
    v2_path = extracted_file(extracted, v2_declaration["path"], "portable v2 projection authority")
    verifier_identity = identity(verifier_path)
    v2_identity = identity(v2_path)
    require(
        verifier_identity == {"bytes": verifier_declaration["bytes"], "sha256": verifier_declaration["sha256"]},
        "portable verifier declared identity drift",
    )
    require(
        v2_identity == {"bytes": v2_declaration["bytes"], "sha256": v2_declaration["sha256"]},
        "portable v2 declared identity drift",
    )
    compile(verifier_path.read_bytes(), str(verifier_path), "exec")

    reconstructed = temporary_path / "independent-cyrillic-reconstruction"
    require(not reconstructed.exists(), "stale independent reconstruction directory")
    environment = {
        key: os.environ[key]
        for key in ("COMSPEC", "PATH", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(verifier_path),
            "--require-live",
            "--write-output-dir",
            str(reconstructed),
        ],
        cwd=extracted,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=300,
    )
    stdout_identity = {"bytes": len(process.stdout), "sha256": sha256_bytes(process.stdout)}
    stderr_identity = {"bytes": len(process.stderr), "sha256": sha256_bytes(process.stderr)}
    require(
        process.returncode == 0,
        f"portable projection verifier failed: rc={process.returncode}, stdout={stdout_identity}, stderr={stderr_identity}",
    )
    require(process.stderr == b"", f"portable projection verifier wrote stderr: {stderr_identity}")
    report = strict_json_payload(process.stdout, "portable projection verifier stdout")
    require(
        report.get("status") == "PASS_INDEPENDENT_RECONSTRUCTION_AND_LIVE_IDENTITY",
        "portable projection verifier did not report live-identity PASS",
    )
    written_output_dir = report.get("written_output_dir")
    require(isinstance(written_output_dir, str), "portable projection verifier omitted output directory")
    require(
        Path(written_output_dir).resolve(strict=True) == reconstructed.resolve(strict=True),
        "portable projection verifier output-directory drift",
    )
    require(report.get("imports_v8") is False, "portable projection replay is not independent of v8")
    claims = report.get("claims", {})
    require(claims.get("source_writes") == 0, "portable projection verifier claims source writes")
    require(claims.get("output_writes") == 4, "portable projection verifier output-write count drift")
    for prohibited in ("git", "network", "build", "render"):
        require(claims.get(prohibited) is False, f"portable projection verifier prohibited claim drift: {prohibited}")

    expected_rows = projection["files"]
    expected = {
        Path(row["path"]).name: (int(row["bytes"]), str(row["sha256"]))
        for row in expected_rows
    }
    require(len(expected) == 4, "portable projection expected-output topology drift")
    reported = {
        row["file"]: (int(row["bytes"]), str(row["sha256"]))
        for row in report.get("output_manifest", [])
    }
    require(len(report.get("output_manifest", [])) == len(reported) == 4, "portable projection report topology drift")
    require(reported == expected, "portable projection verifier output manifest drift")
    require(reconstructed.is_dir() and not reconstructed.is_symlink(), "portable reconstruction directory missing or unsafe")
    reconstructed_names = sorted(path.name for path in reconstructed.iterdir())
    require(reconstructed_names == sorted(expected), f"portable reconstruction topology drift: {reconstructed_names}")

    files: list[dict[str, Any]] = []
    for name in sorted(expected):
        packaged = extracted_file(extracted, f"source_cyrillic/{name}", f"packaged Cyrillic output {name}")
        generated = reconstructed / name
        packaged_identity = identity(packaged)
        generated_identity = identity(generated)
        require(
            (packaged_identity["bytes"], packaged_identity["sha256"]) == expected[name],
            f"packaged Cyrillic pin drift during replay: {name}",
        )
        require(generated_identity == packaged_identity, f"reconstructed/packaged Cyrillic drift: {name}")
        require(generated.read_bytes() == packaged.read_bytes(), f"reconstructed/packaged Cyrillic byte drift: {name}")
        files.append({
            "file": name,
            "packaged": packaged_identity,
            "reconstructed": generated_identity,
            "byte_identical": True,
        })

    authority = report.get("authority", {})
    require(authority.get("v2") == v2_identity, "portable verifier/v2 authority identity drift")
    sanitized_report = dict(report)
    sanitized_report["written_output_dir"] = "<TEMP_RECONSTRUCTION>"
    sanitized_report_raw = canonical_json(sanitized_report)
    return {
        "portable_verifier": {"path": PORTABLE_PROJECTION_VERIFIER, **verifier_identity},
        "portable_v2_authority": {"path": PORTABLE_V2, **v2_identity},
        "reported_status": report["status"],
        "sanitized_subprocess_report": {
            "bytes": len(sanitized_report_raw),
            "sha256": sha256_bytes(sanitized_report_raw),
        },
        "subprocess_stderr_empty": True,
        "four_file_output_manifest": {
            name: {"bytes": pin[0], "sha256": pin[1]}
            for name, pin in sorted(expected.items())
        },
        "files": files,
        "status": "PASS",
    }


def replay_source_archive() -> dict[str, Any]:
    tmp_parent = ROOT / "tmp"
    tmp_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isv021-package-replay-", dir=tmp_parent) as temporary:
        temporary_path = Path(temporary)
        with zipfile.ZipFile(SOURCE_ZIP, "r") as archive:
            extract_safe(archive, temporary_path)
        extracted = temporary_path / "NOETHER_INTERSLAVIC_EDITABLE_SOURCES"
        require(extracted.is_dir(), "extracted source root missing")
        canon_path = extracted_file(extracted, "CANON_INDEX.json", "canon index")
        canon = strict_json_payload(canon_path.read_bytes(), "extracted CANON_INDEX.json")
        require(canon["release_id"] == "NOETHER-ISV-v021", "extracted canon release drift")
        require(canon["edition_scope"]["version_doi"] == "10.5281/zenodo.22077468", "extracted version DOI drift")
        require(canon["authority_chain"]["interslavic_canon"]["editorial_head"] == "ISV021-EDIT-0012", "extracted Latin head drift")
        for surface in ("interslavic_canon", "cyrillic_projection"):
            for declared in canon["authority_chain"][surface]["files"]:
                path = extracted_file(extracted, declared["path"], f"declared {surface} file")
                require(path.stat().st_size == declared["bytes"], f"extracted source byte drift: {path}")
                require(sha256_path(path) == declared["sha256"], f"extracted source hash drift: {path}")
        generator = canon["authority_chain"]["cyrillic_projection"]
        generator_path = extracted_file(extracted, generator["generator"], "declared projector")
        generator_raw = generator_path.read_bytes()
        require(len(generator_raw) == generator["generator_bytes"] and sha256_bytes(generator_raw) == generator["generator_sha256"], "extracted projector pin drift")
        compile(generator_raw, str(generator_path), "exec")
        portable_map = validate_portable_derivation_map(extracted, canon)
        manifest_replay = validate_rebased_role_manifest(extracted, canon)
        projection_replay = replay_cyrillic_portably(extracted, temporary_path, canon)
        return {
            "temporary_tree_removed_after_replay": True,
            "canonical_and_derived_files_authenticated": 8,
            "projector": {"path": generator["generator"], "bytes": len(generator_raw), "sha256": sha256_bytes(generator_raw), "syntax": "PASS"},
            "portable_derivation_map": portable_map,
            "role_manifest": manifest_replay,
            "independent_latin_to_cyrillic_replay": projection_replay,
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
    validate_public_topology()
    public_rows = parse_top_manifest()
    release_manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    require(release_manifest["release_id"] == "NOETHER-ISV-v021", "release identity drift")
    require(release_manifest["version_doi"] == "10.5281/zenodo.22077468", "release DOI drift")
    expected_public = [record(PUBLIC / name) for name in PUBLIC_NAMES]
    require(release_manifest["public_files"] == expected_public, "release manifest/public byte drift")
    source_inventory = validate_zip_inventory(SOURCE_ZIP, "NOETHER_INTERSLAVIC_EDITABLE_SOURCES")
    evidence_inventory = validate_zip_inventory(EVIDENCE_ZIP, "NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE")
    replay = replay_source_archive()
    receipt = {
        "schema": "noether-interslavic-public-package-replay-validation/1.0",
        "release_id": "NOETHER-ISV-v021",
        "generated_at": "2026-08-24T00:00:00Z",
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
