#!/usr/bin/env python3
"""Build and independently validate the four public NOETHER-ISV-v021 files."""

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
RELEASE = ROOT / "release_v021"
PUBLIC = RELEASE / "public"
EVIDENCE = RELEASE / "evidence"
FIXED_ZIP_TIME = (2026, 8, 24, 0, 0, 0)
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
METHODS = EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v021.pdf"
V020_COMPARATOR = ROOT / "comparison" / "v020-linked-reader.pdf"
VISUAL_QA = EVIDENCE / "visual-qa-receipt.json"
LOCAL_V2_AUTHORITY = (
    ROOT.parent
    / "noether_isv_v020_working"
    / "predecessor_v019"
    / "project_isv_cyrillic_v2.py"
)
PORTABLE_V2_AUTHORITY = ROOT / "comparison" / "predecessor_v019" / "project_isv_cyrillic_v2.py"
V2_AUTHORITY = PORTABLE_V2_AUTHORITY if PORTABLE_V2_AUTHORITY.is_file() else LOCAL_V2_AUTHORITY

PINS = {
    READER: (6_878_076, "C296AFCAB42B68E228B4438B11D6BBF6B6054DC48683B13BFC31EB4132C8E8D1"),
    METHODS: (182_587, "931C14ED6AF93B7B59FC538D6A68BB986B016E018F37BDC920BAB63C973675DC"),
    V020_COMPARATOR: (6_885_841, "7DCB4C852BF3CCE5928921E13F73FA34E80EA4FEB2A82F967FEE29657150AE20"),
    ROOT / "decision_records" / "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json": (
        4_177_431,
        "BE0A9902DAC546350227C048777A78AC300647D5FB514895F7CB91EC3D900970",
    ),
    ROOT / "project_isv_cyrillic_v8.py": (
        34_267,
        "06CC1640E253513EFF64918E6CC3BCE583913D3E64B2F93F1B77C3734BABDC8C",
    ),
    ROOT / "decision_records" / "ISV021-LATIN-FREEZE-PROJECTION-FRONTIER-R2.json": (
        360_147,
        "C0584834AF4A2638E763BCEEEA92D0A5C43F40380BC97B36A98BC4D25D6B686B",
    ),
    RELEASE / "source" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex": (
        11_404,
        "90EDD51E6335903AB6CEE34B6C4D0CD619BD123FD2BFA061A6FB249C516385FC",
    ),
    ROOT / "docs" / "METHODS_AI_INTERSLAVIC_NOETHER_v021.tex": (
        45_237,
        "5B66C12C7C0F181D9FFB285E830D6774D4FBCC304B98B268657576AEE6CC4FB1",
    ),
    EVIDENCE / "build-manifest.json": (
        25_875,
        "1A962C74A355F892A6CA821520F009BDFD865C4C6028EF084E465C6E77B097A2",
    ),
    EVIDENCE / "qa-report.json": (
        59_492,
        "72D99E734DB4BA412E17737653957D070A0BF5DF88DA74184E268A138925D035",
    ),
    EVIDENCE / "linked-reader-build.json": (
        3_122,
        "8BE6F344ABB1F47594E7105B1E84E381977754D1F533DA7568BC3FC373D255DA",
    ),
    EVIDENCE / "methods" / "AI_INTERSLAVIC_NOETHER_METHODS_v021.build.json": (
        6_147,
        "0D55376D6D20CEDE731064A60539180C0F7EED51FF0A925E2CB22CE81EACCEA1",
    ),
    EVIDENCE / "linked-reader-visual-assets.json": (
        14_286,
        "20A752FA51B9B9D7A059662851C00508640D7B46A1F23FFC0D8ED899B80167AD",
    ),
    EVIDENCE / "methods-visual-assets.json": (
        2_033,
        "E32C34FCA6C7560EBBD6FAD9BE8C698F3494DED784199A9188856B70728FF112",
    ),
    VISUAL_QA: (
        19_409,
        "D70F9DD6FF1466158C51835C8FCDA1A612B7E32B8CB2F07AA59E55E206935B18",
    ),
    ROOT / "source_latin" / "44-book-isv.tex": (
        168_384,
        "FFEAE898972515A69D9BCD4930ECEEF2C91DD7114E0CA0B0F64E2157ED32E698",
    ),
    ROOT / "source_latin" / "45-isv.tex": (
        26_036,
        "E49033F3C3004F921CD234610425905FF1D46405107D8EB99BC431864BB4473D",
    ),
    ROOT / "source_latin" / "base-papers1-43-isv.tex": (
        1_893_083,
        "237FFE1460816EAF8CCD6E00F9500F816A285830CE62E28E49CECB94685B16E9",
    ),
    ROOT / "source_latin" / "bib-isv.tex": (
        10_016,
        "D14F600C71E911F49F0A81B85B2C476F7BED490D597E2045AC55744774D201B1",
    ),
    ROOT / "source_cyrillic" / "44-book-isv-cyrl.tex": (
        230_381,
        "0DD9907518035924993A0041B14BCAEA10D7C213DAB8DF422F6B25E7DDED9D63",
    ),
    ROOT / "source_cyrillic" / "45-isv-cyrl.tex": (
        35_874,
        "40870377323594B3153A1F25D6BC2FB34899B6E6FDD388837388E9D12D147140",
    ),
    ROOT / "source_cyrillic" / "base-papers1-43-isv-cyrl.tex": (
        2_706_234,
        "E9C7AEC849C4B2D2B6E528AFB1B62236B9CFFBAD686FA4923749C9359EB2824C",
    ),
    ROOT / "source_cyrillic" / "bib-isv-cyrl.tex": (
        13_206,
        "37FFF904BB16B2B460923AE2BF801BF783803FD0B78B94AF83D21FF43B81AB47",
    ),
}

CURRENT_TOOL_PREFIXES = (
    "analyze_",
    "apply_",
    "audit_",
    "build_",
    "project_",
    "qa_",
    "rebase_",
    "render_",
    "seal_",
    "test_",
    "verify_",
)
CURRENT_TOOL_COUNT = 59
CURRENT_TOOL_NAME_INVENTORY_SHA256 = "FA0EF4A068ECA1D310F0A8B4CB2CEC4A7D9BBAB1906D2A1DB6114B7CB67D9B9A"
DECISION_RECORD_COUNT = 66
DECISION_RECORD_NAME_INVENTORY_SHA256 = "AC97656068D1A31091CC745C4410CDE85CBF52A3867034A754B0DC41A344C482"
ROLE_MANIFEST_NAME = "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json"
INDEPENDENT_VERIFIER_NAME = "verify_cyrillic_v8_independent.py"
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
EXCLUDED_EVIDENCE_NAMES = {
    "SOURCE_ARCHIVE_VALIDATION.json",
    "EVIDENCE_ARCHIVE_VALIDATION.json",
    "PACKAGE_VALIDATION.json",
    "PUBLICATION_RECEIPT.json",
    "PUBLICATION_READBACK.json",
    "PUBLIC_PACKAGE_REPLAY_VALIDATION.json",
}

EVIDENCE_README = """# Dokazy i pohođenje / Evidence and provenance

## Medžuslovjansky

Tutoj arhiv dokazuje, kako bylo stvorjeno izdanje `NOETHER-ISV-v021`. Latiničny tekst jest jediny redagovateljny jezyčny kanon; kirilica jest fail-closed deterministična projekcija, ne samostojny prěklad. Kontrolne iztočniki sut `CANON_INDEX.json`, 12 dodavajemyh rěšenij v021 s 4 053 lokalizovanymi popravkami, rebazovany manifest 5 290 iztočnikovo vezanyh zapisov, v8 projektor, build/QA potvrđenja i 13-stranična publikacijska metodologija.

Novy agent trěba najprvo čitati `PUBLIC_RELEASE_README.md` i `CANON_INDEX.json`. Arhiv ne sodrživaje credentialy, task-transkripty, Git-katalog, operacijne sesijne statusy ili nerazrěšene privatne source-scan fajly. Javny v020 čitateljnik jest ohranjen kako sravnjivateljny prědhodnik. Publikacijska potvrda se piše poslě javnogo čitanja nazad i zato naměrno ne jest članom samogo arhiva.

## English

This archive proves how `NOETHER-ISV-v021` was produced. Latin is the sole editable language canon; Cyrillic is a fail-closed deterministic projection, not an independent translation. Controlling evidence includes `CANON_INDEX.json`, 12 append-only v021 decisions with 4,053 localized corrections, the rebased 5,290-record source-bound role manifest, the v8 projector, build/QA receipts, and the 13-page publication-style methods paper.

A future agent should read `PUBLIC_RELEASE_README.md` and `CANON_INDEX.json` first. Credentials, task transcripts, Git internals, operational session state, and unresolved private source scans are excluded. The public v020 reader is retained as the predecessor comparator. The post-publication receipt is created only after public readback and is therefore intentionally not a member of this archive.
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def name_inventory_sha256(names: Iterable[str]) -> str:
    return sha256_bytes(("\n".join(names) + "\n").encode("utf-8"))


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


def current_tool_files() -> tuple[str, ...]:
    names = tuple(
        sorted(
            path.name
            for path in ROOT.glob("*.py")
            if path.is_file()
            and not path.is_symlink()
            and path.name.startswith(CURRENT_TOOL_PREFIXES)
        )
    )
    require(len(names) == CURRENT_TOOL_COUNT, f"tool inventory count drift: {len(names)}")
    require(
        name_inventory_sha256(names) == CURRENT_TOOL_NAME_INVENTORY_SHA256,
        "tool name inventory drift",
    )
    require("project_isv_cyrillic_v8.py" in names, "projector missing from tool inventory")
    require("test_cyrillic_v8_install_transaction.py" in names, "projector transaction test missing")
    require("verify_cyrillic_v8_independent.py" in names, "independent projector verifier missing")
    require("build_release_packages_v021.py" in names, "packager missing from tool inventory")
    require("verify_release_packages_v021.py" in names, "package verifier missing")
    require(not any(name.startswith("reserve_") for name in names), "credential-aware publication tool leaked into archive")
    return names


def current_decision_files() -> tuple[Path, ...]:
    directory = ROOT / "decision_records"
    require(directory.is_dir() and not directory.is_symlink(), "decision-record directory is missing or unsafe")
    files = tuple(sorted((path for path in directory.iterdir() if path.is_file() and not path.is_symlink()), key=lambda path: path.name))
    names = tuple(path.name for path in files)
    require(len(names) == DECISION_RECORD_COUNT, f"decision-record inventory count drift: {len(names)}")
    require(
        name_inventory_sha256(names) == DECISION_RECORD_NAME_INVENTORY_SHA256,
        "decision-record name inventory drift",
    )
    return files


def validate_visual_qa() -> dict[str, Any]:
    require(VISUAL_QA.is_file() and not VISUAL_QA.is_symlink(), "sealed visual-QA receipt is missing")
    raw = VISUAL_QA.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw, "visual-QA receipt transport drift")
    receipt = json.loads(raw.decode("utf-8"))
    require(receipt.get("release_id") == "NOETHER-ISV-v021", "visual-QA release identity drift")
    require(
        receipt.get("status") == "PASS" or receipt.get("pass") is True,
        "visual-QA receipt is not sealed PASS",
    )
    return {"receipt": file_record(VISUAL_QA), "status": "PASS", "value": receipt}


def validate_public_metadata() -> dict[str, Any]:
    json_paths = [
        ROOT / "CANON_INDEX.json",
        ROOT / "metadata" / "DATACITE_RELATIONS.json",
        ROOT / "metadata" / "RELEASE_SCOPE.json",
        ROOT / "metadata" / "SOURCE_AUTHORITY.json",
        ROOT / "metadata" / "zenodo-metadata.json",
    ]
    require(all(path.is_file() and not path.is_symlink() for path in json_paths), "public metadata set is incomplete or unsafe")
    parsed = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in json_paths}
    cff = yaml.safe_load((ROOT / "metadata" / "CITATION.cff").read_text(encoding="utf-8"))
    require(isinstance(cff, dict), "CITATION.cff did not parse as a mapping")
    for path in (ROOT / "PUBLIC_RELEASE_README.md", ROOT / "GITHUB_README_v021.md"):
        text = path.read_text(encoding="utf-8")
        require(text.startswith("# "), f"missing heading: {path}")
        require("## English" in text or "# English" in text, f"missing English counterpart: {path}")
        english = text.find("English")
        require(english > 0, f"English must follow Interslavic: {path}")
    canon = parsed["CANON_INDEX.json"]
    scope = parsed["RELEASE_SCOPE.json"]
    authority = parsed["SOURCE_AUTHORITY.json"]
    zenodo = parsed["zenodo-metadata.json"]
    require(canon["release_id"] == "NOETHER-ISV-v021", "canon release drift")
    require(canon["edition_scope"]["version_doi"] == "10.5281/zenodo.22077468", "version DOI drift")
    require(canon["edition_scope"]["concept_doi"] == "10.5281/zenodo.21926382", "concept DOI drift")
    require(canon["authority_chain"]["interslavic_canon"]["editorial_head"] == "ISV021-EDIT-0012", "Latin head drift")
    require(canon["authority_chain"]["cyrillic_projection"]["generator"] == "project_isv_cyrillic_v8.py", "projector identity drift")
    for surface in ("interslavic_canon", "cyrillic_projection"):
        for declaration in canon["authority_chain"][surface]["files"]:
            path = ROOT / declaration["path"]
            require(path in PINS, f"canon declares an unpinned release source: {path}")
            require(
                (declaration["bytes"], declaration["sha256"]) == PINS[path],
                f"canon source declaration drift: {declaration['path']}",
            )
    projection = canon["authority_chain"]["cyrillic_projection"]
    require(
        (projection["generator_bytes"], projection["generator_sha256"])
        == PINS[ROOT / "project_isv_cyrillic_v8.py"],
        "canon projector pin drift",
    )
    role = projection["reviewed_role_manifest"]
    role_path = ROOT / role["path"]
    require(role_path in PINS and (role["bytes"], role["sha256"]) == PINS[role_path], "canon role-manifest pin drift")
    require(authority["release_id"] == "NOETHER-ISV-v021", "source-authority release drift")
    require(authority["interslavic"]["editorial_head"] == "ISV021-EDIT-0012", "source-authority Latin head drift")
    require(scope["public_files"] == [
        "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf",
        "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip",
        "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip",
        "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt",
    ], "public-file topology drift")
    correction = scope["v021_correction"]
    expected_correction = {
        "latin_head": "ISV021-EDIT-0012",
        "sealed_decisions": 12,
        "localized_sites_changed": 4053,
        "byte_delta_from_predecessor": -1696,
        "non_roman_projection_blockers": 0,
        "protected_foreign_e_grave_spellings": 4,
        "generic_diacritic_stripping": False,
    }
    require(
        all(correction.get(key) == value for key, value in expected_correction.items()),
        "v021 correction metrics drift",
    )
    require(zenodo["version"] == "2026.08.24-v021", "Zenodo version drift")
    require(zenodo.get("upload_type") == "publication", "Zenodo upload type drift")
    require(zenodo.get("publication_type") == "book", "Zenodo publication type drift")
    require(zenodo.get("license") == "cc-zero", "Zenodo license drift")
    require("resource_type" not in zenodo, "legacy Zenodo deposition API rejects object resource_type")
    require("language" not in zenodo, "Zenodo deposition vocabulary currently rejects isv; language must remain explicit in title, description, keywords, and canon index")
    require("10.5281/zenodo.22077468" in zenodo.get("description", ""), "Zenodo description version DOI drift")
    require(cff.get("version") == "NOETHER-ISV-v021", "CFF version drift")
    require(cff.get("doi") == "10.5281/zenodo.22077468", "CFF DOI drift")
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


def add_bytes(members: dict[str, bytes], archive_name: str, payload: bytes) -> None:
    name = PurePosixPath(archive_name).as_posix()
    require(not name.startswith("/") and ".." not in PurePosixPath(name).parts, f"unsafe archive name: {name}")
    require(name not in members, f"duplicate archive member: {name}")
    scan_payload(name, payload)
    members[name] = payload


def add_file(members: dict[str, bytes], archive_name: str, source: Path) -> None:
    require(source.is_file() and not source.is_symlink(), f"unsafe or missing member source: {source}")
    add_bytes(members, archive_name, source.read_bytes())


def relative_source_locator(source: Path) -> str:
    resolved = source.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        require(resolved == V2_AUTHORITY.resolve(), f"unregistered external portable input: {source}")
        return "comparison/predecessor_v019/project_isv_cyrillic_v2.py"


def sanitize_portable_text(payload: bytes) -> tuple[bytes, dict[str, int]]:
    workspace_root = ROOT.parents[3]
    profile = Path.home()
    replacements: list[tuple[bytes, bytes, str]] = []
    for path, label, key in (
        (ROOT, b"<TASK_ROOT>", "task_root"),
        (workspace_root, b"<WORKSPACE_ROOT>", "workspace_root"),
        (profile, b"<USER_PROFILE>", "user_profile"),
    ):
        for surface in {
            str(path),
            str(path).replace("\\", "/"),
            str(path).replace("\\", "\\\\"),
        }:
            replacements.append((surface.encode("utf-8"), label, key))
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    counts: dict[str, int] = {}
    rendered = payload
    for before, after, key in replacements:
        rendered, count = re.subn(re.escape(before), after, rendered, flags=re.I)
        if count:
            counts[key] = counts.get(key, 0) + count
    local_name = profile.name.encode("utf-8")
    if local_name:
        rendered, count = re.subn(re.escape(local_name), b"<LOCAL_USER>", rendered, flags=re.I)
        if count:
            counts["local_user_name"] = counts.get("local_user_name", 0) + count
    return rendered, counts


def rename_invalidated_self_digests(value: Any, renamed: list[str], pointer: str = "$") -> Any:
    if isinstance(value, list):
        return [rename_invalidated_self_digests(item, renamed, f"{pointer}[{index}]") for index, item in enumerate(value)]
    if not isinstance(value, dict):
        return value
    transformed = {
        key: rename_invalidated_self_digests(item, renamed, f"{pointer}.{key}")
        for key, item in value.items()
    }
    for key in ("report_sha256_excluding_this_field", "inventory_sha256_excluding_this_field"):
        if key not in transformed:
            continue
        replacement = f"source_local_{key}"
        require(replacement not in transformed, f"portable self-digest key collision at {pointer}")
        transformed[replacement] = transformed.pop(key)
        renamed.append(f"{pointer}.{key}")
    return transformed


def make_portable_payload(source: Path) -> tuple[bytes, dict[str, Any] | None]:
    raw = source.read_bytes()
    sanitized, substitutions = sanitize_portable_text(raw)
    if not substitutions:
        return raw, None
    locator = relative_source_locator(source)
    record: dict[str, Any] = {
        "source_path": locator,
        "source": {"bytes": len(raw), "sha256": sha256_bytes(raw)},
        "substitutions": substitutions,
    }
    if source.suffix.casefold() == ".json":
        value = json.loads(sanitized.decode("utf-8"))
        if source.name == ROLE_MANIFEST_NAME:
            require(isinstance(value, dict), "role manifest must be a JSON object")
            original_internal = value.pop("inventory_sha256_excluding_this_field")
            value["_portable_derivation"] = {
                "schema": "noether-interslavic-portable-derivative/1.0",
                "source_bytes": len(raw),
                "source_sha256": sha256_bytes(raw),
                "source_internal_sha256": original_internal,
                "path_placeholders": sorted(substitutions),
            }
            portable_internal = sha256_bytes(canonical_json(value))
            value["inventory_sha256_excluding_this_field"] = portable_internal
            sanitized = canonical_json(value)
            record["self_digest_disposition"] = {
                "source_internal_sha256_preserved_in": "_portable_derivation.source_internal_sha256",
                "portable_internal_sha256": portable_internal,
                "algorithm": "SHA-256 of canonical JSON excluding inventory_sha256_excluding_this_field",
            }
        else:
            renamed: list[str] = []
            value = rename_invalidated_self_digests(value, renamed)
            if isinstance(value, dict):
                value["_portable_derivation"] = {
                    "schema": "noether-interslavic-portable-derivative/1.0",
                    "source_bytes": len(raw),
                    "source_sha256": sha256_bytes(raw),
                    "path_placeholders": sorted(substitutions),
                    "invalidated_local_self_digest_fields_renamed": renamed,
                }
                value["_portable_sha256_excluding_this_field"] = sha256_bytes(canonical_json(value))
                record["self_digest_disposition"] = {
                    "invalidated_local_fields_renamed": renamed,
                    "portable_field": "_portable_sha256_excluding_this_field",
                }
            sanitized = canonical_json(value)
    record["portable"] = {"bytes": len(sanitized), "sha256": sha256_bytes(sanitized)}
    return sanitized, record


def patch_portable_independent_verifier(raw: bytes, manifest_raw: bytes) -> bytes:
    manifest = json.loads(manifest_raw.decode("utf-8"))
    internal = manifest["inventory_sha256_excluding_this_field"]
    rendered = raw.decode("utf-8")
    rendered, v2_count = re.subn(
        r'^V2_PATH = .*$',
        'V2_PATH = ROOT / "comparison" / "predecessor_v019" / "project_isv_cyrillic_v2.py"',
        rendered,
        count=1,
        flags=re.M,
    )
    rendered, pin_count = re.subn(
        r'MANIFEST_PIN = \(\n\s*[0-9_]+,\n\s*"[A-F0-9]+",\n\)',
        f'MANIFEST_PIN = (\n    {len(manifest_raw):_},\n    "{sha256_bytes(manifest_raw)}",\n)',
        rendered,
        count=1,
    )
    rendered, internal_count = re.subn(
        r'MANIFEST_INTERNAL = "[A-F0-9]+"',
        f'MANIFEST_INTERNAL = "{internal}"',
        rendered,
        count=1,
    )
    require((v2_count, pin_count, internal_count) == (1, 1, 1), "portable verifier patch topology drift")
    payload = rendered.encode("utf-8")
    scan_payload(INDEPENDENT_VERIFIER_NAME, payload)
    return payload


def make_portable_canon_index(manifest_raw: bytes, verifier_raw: bytes) -> bytes:
    canon_source = ROOT / "CANON_INDEX.json"
    canon = json.loads(canon_source.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_raw.decode("utf-8"))
    projection = canon["authority_chain"]["cyrillic_projection"]
    projection["reviewed_role_manifest"].update({
        "bytes": len(manifest_raw),
        "sha256": sha256_bytes(manifest_raw),
        "internal_sha256": manifest["inventory_sha256_excluding_this_field"],
        "portable_derivative": True,
    })
    projection["portable_replay"] = {
        "status": "RUNNABLE_FAIL_CLOSED_IN_EXTRACTED_SOURCE_ARCHIVE",
        "command": "python -B verify_cyrillic_v8_independent.py --require-live --write-output-dir reconstructed-cyrillic",
        "independent_verifier": {
            "path": INDEPENDENT_VERIFIER_NAME,
            "bytes": len(verifier_raw),
            "sha256": sha256_bytes(verifier_raw),
        },
        "v2_authority": {
            "path": "comparison/predecessor_v019/project_isv_cyrillic_v2.py",
            "bytes": V2_AUTHORITY.stat().st_size,
            "sha256": sha256_path(V2_AUTHORITY),
        },
        "expected_outputs": projection["files"],
        "note": "The v8 producer is retained as sealed local provenance; this independent portable replay reconstructs and byte-compares all four Cyrillic files without importing v8.",
    }
    canon["_portable_derivation"] = {
        "schema": "noether-interslavic-portable-canon-index/1.0",
        "source": {"bytes": canon_source.stat().st_size, "sha256": sha256_path(canon_source)},
        "path_binding_manifest": "manifests/PORTABLE_DERIVATION_MAP.json",
    }
    return json.dumps(canon, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def build_portable_context() -> dict[str, Any]:
    require(V2_AUTHORITY.is_file() and not V2_AUTHORITY.is_symlink(), "portable v2 authority is missing or unsafe")
    require(
        (V2_AUTHORITY.stat().st_size, sha256_path(V2_AUTHORITY))
        == (74_914, "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2"),
        "portable v2 authority pin drift",
    )
    records: list[dict[str, Any]] = []
    decisions: dict[str, bytes] = {}
    for source in current_decision_files():
        payload, record = make_portable_payload(source)
        decisions[source.name] = payload
        if record is not None:
            records.append(record)
    manifest_raw = decisions[ROLE_MANIFEST_NAME]
    tools: dict[str, bytes] = {}
    for name in current_tool_files():
        source = ROOT / name
        payload, record = make_portable_payload(source)
        tools[name] = payload
        if record is not None:
            records.append(record)
    original_verifier = tools[INDEPENDENT_VERIFIER_NAME]
    portable_verifier = patch_portable_independent_verifier(original_verifier, manifest_raw)
    if portable_verifier != original_verifier:
        tools[INDEPENDENT_VERIFIER_NAME] = portable_verifier
        source = ROOT / INDEPENDENT_VERIFIER_NAME
        records.append({
            "source_path": INDEPENDENT_VERIFIER_NAME,
            "source": {"bytes": source.stat().st_size, "sha256": sha256_path(source)},
            "transformation": "portable replay dependency paths and role-manifest pins",
            "portable": {"bytes": len(portable_verifier), "sha256": sha256_bytes(portable_verifier)},
        })
    portable_canon = make_portable_canon_index(manifest_raw, portable_verifier)
    canon_source = ROOT / "CANON_INDEX.json"
    records.append({
        "source_path": "CANON_INDEX.json",
        "source": {"bytes": canon_source.stat().st_size, "sha256": sha256_path(canon_source)},
        "transformation": "portable role-manifest and replay authority pins",
        "portable": {"bytes": len(portable_canon), "sha256": sha256_bytes(portable_canon)},
    })
    mapping = {
        "schema": "noether-interslavic-portable-derivation-map/1.0",
        "release_id": "NOETHER-ISV-v021",
        "status": "PASS_NO_LOCAL_PROFILE_IDENTITY",
        "placeholders": {
            "<TASK_ROOT>": "root of the extracted v021 source/evidence tree",
            "<WORKSPACE_ROOT>": "workspace root containing 03_projects",
            "<USER_PROFILE>": "local operating-system user profile",
            "<LOCAL_USER>": "local operating-system account name",
        },
        "source_authority_rule": "Original local hashes remain provenance; portable hashes authenticate public derivatives. The portable role manifest has a recomputed internal digest. Invalidated compact-report digests are renamed and a derivative digest is added instead of making a false original-report claim.",
        "portable_replay": {
            "verifier": {"bytes": len(portable_verifier), "sha256": sha256_bytes(portable_verifier)},
            "v2": {"bytes": V2_AUTHORITY.stat().st_size, "sha256": sha256_path(V2_AUTHORITY)},
            "role_manifest": {
                "bytes": len(manifest_raw),
                "sha256": sha256_bytes(manifest_raw),
                "internal_sha256": json.loads(manifest_raw.decode("utf-8"))["inventory_sha256_excluding_this_field"],
            },
        },
        "derivatives": sorted(records, key=lambda item: (item["source_path"], item.get("transformation", ""))),
    }
    mapping_raw = json.dumps(mapping, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    scan_payload("PORTABLE_DERIVATION_MAP.json", mapping_raw)
    return {
        "decisions": decisions,
        "tools": tools,
        "canon": portable_canon,
        "mapping": mapping_raw,
        "manifest": manifest_raw,
        "verifier": portable_verifier,
    }


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
    profile = Path.home()
    replacements = (
        (str(ROOT).encode("utf-8"), b"<TASK_ROOT>"),
        (str(ROOT).replace("\\", "/").encode("utf-8"), b"<TASK_ROOT>"),
        (str(profile).encode("utf-8"), b"<USER_PROFILE>"),
        (str(profile).replace("\\", "/").encode("utf-8"), b"<USER_PROFILE>"),
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
        "release_id": "NOETHER-ISV-v021",
        "archive_role": archive_role,
        "fixed_member_timestamp": "2026-08-24T00:00:00",
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


def source_members(portable: Mapping[str, Any]) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    add_file(members, f"{SOURCE_ROOT}/README.md", ROOT / "GITHUB_README_v021.md")
    add_file(members, f"{SOURCE_ROOT}/PUBLIC_RELEASE_README.md", ROOT / "PUBLIC_RELEASE_README.md")
    add_bytes(members, f"{SOURCE_ROOT}/CANON_INDEX.json", portable["canon"])
    add_tree(members, f"{SOURCE_ROOT}/LICENSES", ROOT / "LICENSES")
    add_tree(members, f"{SOURCE_ROOT}/metadata", ROOT / "metadata")
    add_tree(members, f"{SOURCE_ROOT}/source_latin", ROOT / "source_latin")
    add_tree(members, f"{SOURCE_ROOT}/source_cyrillic", ROOT / "source_cyrillic")
    add_tree(members, f"{SOURCE_ROOT}/assets", ROOT / "assets")
    add_file(
        members,
        f"{SOURCE_ROOT}/docs/METHODS_AI_INTERSLAVIC_NOETHER_v021.tex",
        ROOT / "docs" / "METHODS_AI_INTERSLAVIC_NOETHER_v021.tex",
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/docs/AI_INTERSLAVIC_NOETHER_METHODS_v021.pdf",
        METHODS,
    )
    add_file(
        members,
        f"{SOURCE_ROOT}/release_v021/source/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex",
        RELEASE / "source" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex",
    )
    for name, payload in sorted(portable["decisions"].items()):
        add_bytes(members, f"{SOURCE_ROOT}/decision_records/{name}", payload)
    for name, payload in sorted(portable["tools"].items()):
        add_bytes(members, f"{SOURCE_ROOT}/{name}", payload)
    add_file(members, f"{SOURCE_ROOT}/comparison/v020-linked-reader.pdf", V020_COMPARATOR)
    add_file(
        members,
        f"{SOURCE_ROOT}/comparison/predecessor_v019/project_isv_cyrillic_v2.py",
        V2_AUTHORITY,
    )
    add_bytes(members, f"{SOURCE_ROOT}/manifests/PORTABLE_DERIVATION_MAP.json", portable["mapping"])
    return with_internal_manifest(members, SOURCE_ROOT, "SOURCE_MEMBER_SHA256.tsv", "editable_sources")


def evidence_members(portable: Mapping[str, Any]) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    add_bytes(members, f"{EVIDENCE_ROOT}/00_README_EVIDENCE.md", EVIDENCE_README.encode("utf-8"))
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/PUBLIC_RELEASE_README.md", ROOT / "PUBLIC_RELEASE_README.md")
    add_file(members, f"{EVIDENCE_ROOT}/01_release_identity/REPRODUCIBLE_BUILD.md", ROOT / "GITHUB_README_v021.md")
    add_bytes(members, f"{EVIDENCE_ROOT}/01_release_identity/CANON_INDEX.json", portable["canon"])
    add_tree(members, f"{EVIDENCE_ROOT}/01_release_identity/metadata", ROOT / "metadata")
    add_tree(members, f"{EVIDENCE_ROOT}/02_rights/LICENSES", ROOT / "LICENSES")
    for name, payload in sorted(portable["decisions"].items()):
        add_bytes(members, f"{EVIDENCE_ROOT}/03_v021_review/decision_records/{name}", payload)
    for name, payload in sorted(portable["tools"].items()):
        add_bytes(members, f"{EVIDENCE_ROOT}/03_v021_review/tools/{name}", payload)
    add_file(
        members,
        f"{EVIDENCE_ROOT}/03_v021_review/comparison/predecessor_v019/project_isv_cyrillic_v2.py",
        V2_AUTHORITY,
    )
    add_bytes(
        members,
        f"{EVIDENCE_ROOT}/03_v021_review/PORTABLE_DERIVATION_MAP.json",
        portable["mapping"],
    )
    add_file(
        members,
        f"{EVIDENCE_ROOT}/04_public_predecessor_v020/v020-linked-reader.pdf",
        V020_COMPARATOR,
    )
    add_tree(
        members,
        f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/evidence",
        EVIDENCE,
        exclude_names=EXCLUDED_EVIDENCE_NAMES,
    )
    add_file(
        members,
        f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/methods/METHODS_AI_INTERSLAVIC_NOETHER_v021.tex",
        ROOT / "docs" / "METHODS_AI_INTERSLAVIC_NOETHER_v021.tex",
    )
    for manifest_name in ("linked-reader-visual-assets.json", "methods-visual-assets.json"):
        manifest = json.loads((EVIDENCE / manifest_name).read_text(encoding="utf-8"))
        for declaration in manifest["contact_sheets"]:
            source = ROOT / declaration["path"]
            require(source.is_file() and not source.is_symlink(), f"missing or unsafe contact sheet: {source}")
            require(
                (source.stat().st_size, sha256_path(source))
                == (declaration["bytes"], declaration["sha256"]),
                f"contact-sheet pin drift: {source}",
            )
            add_file(
                members,
                f"{EVIDENCE_ROOT}/05_build_render_and_content_qa/visual/{source.parent.name}/{source.name}",
                source,
            )
    log_root = ROOT / "tmp" / "pdfs" / "isv_release_v021"
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
    visual_validation = validate_visual_qa()
    metadata_validation = validate_public_metadata()
    portable = build_portable_context()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    expected_public_names = {
        "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf",
        "01_NOETHER_INTERSLAVIC_EDITABLE_SOURCES.zip",
        "02_NOETHER_INTERSLAVIC_EVIDENCE_AND_PROVENANCE.zip",
        "03_NOETHER_INTERSLAVIC_SHA256_MANIFEST.txt",
    }
    observed_public_names = {
        path.name for path in PUBLIC.iterdir() if path.is_file() and not path.is_symlink()
    }
    require(READER.name in observed_public_names, "public reader is missing")
    require(
        observed_public_names <= expected_public_names,
        f"unexpected public-file topology before packaging: {sorted(observed_public_names - expected_public_names)}",
    )

    source = build_one_zip(SOURCE_ZIP, source_members(portable))
    source_receipt = {
        "schema": "noether-interslavic-source-archive-validation/1.0",
        "release_id": "NOETHER-ISV-v021",
        "generated_at": "2026-08-24T00:00:00Z",
        "status": "PASS",
        "metadata_validation": metadata_validation,
        **source,
    }
    write_json_exact(SOURCE_VALIDATION, source_receipt)

    evidence = build_one_zip(EVIDENCE_ZIP, evidence_members(portable))
    evidence_receipt = {
        "schema": "noether-interslavic-evidence-archive-validation/1.0",
        "release_id": "NOETHER-ISV-v021",
        "generated_at": "2026-08-24T00:00:00Z",
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
    observed_public_names = {
        path.name for path in PUBLIC.iterdir() if path.is_file() and not path.is_symlink()
    }
    require(observed_public_names == expected_public_names, "exact four-file public topology failed")

    release_manifest = {
        "schema": "noether-interslavic-release-manifest/1.0",
        "release_id": "NOETHER-ISV-v021",
        "publication_date": "2026-08-24",
        "language": "isv",
        "scripts": ["isv-Latn", "isv-Cyrl"],
        "concept_doi": "10.5281/zenodo.21926382",
        "version_doi": "10.5281/zenodo.22077468",
        "global_catalogue_concept_doi": "10.5281/zenodo.20412587",
        "repository": "https://github.com/KokunoYumeto/emmy-noether-isv",
        "latin_editorial_head": "ISV021-EDIT-0012",
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
        "v021_correction": {
            "latin_source_files_changed": 4,
            "latin_total_byte_delta_from_v020": -1696,
            "localized_corrections": 4053,
            "decisions_added": 12,
            "lexical_morphology_sites": 656,
            "basic_consonant_sites": 1599,
            "other_optional_letter_sites": 1798,
            "protected_foreign_e_grave": 4,
            "inherited_role_rows_rebased": 4568,
            "total_source_bound_role_rows": 5290,
            "protected_role_rows": 1980,
            "roman_identity_rows": 722,
            "non_roman_projection_blockers": 0,
        },
        "qa": {
            "release_report": file_record(EVIDENCE / "qa-report.json"),
            "visual_receipt": visual_validation["receipt"],
            "visual_status": visual_validation["status"],
            "projection_v8_tool": file_record(ROOT / "project_isv_cyrillic_v8.py"),
            "projection_role_manifest": file_record(ROOT / "decision_records" / "ISV021-REBASED-PROJECTION-ROLE-MANIFEST.json"),
            "latin_freeze_receipt": file_record(ROOT / "decision_records" / "ISV021-LATIN-FREEZE-PROJECTION-FRONTIER-R2.json"),
            "release_checks": 38,
            "release_errors": 0,
        },
        "review_and_claim_boundary": "Machine-assisted scholarly working edition. No independent native-speaker, community, official-standard, or scholarly-peer-review certification is claimed. Cyrillic is a deterministic representation, not an independent witness.",
        "repository_identity_note": "The immutable release tag and commit are recorded after public push in PUBLICATION_RECEIPT.json to avoid a self-referential file/commit hash cycle.",
    }
    write_json_exact(RELEASE_MANIFEST, release_manifest)

    with zipfile.ZipFile(SOURCE_ZIP) as source_archive, zipfile.ZipFile(EVIDENCE_ZIP) as evidence_archive:
        package_receipt = {
            "schema": "noether-interslavic-package-validation/1.0",
            "release_id": "NOETHER-ISV-v021",
            "generated_at": "2026-08-24T00:00:00Z",
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
            "operational_session_state_included": False,
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
