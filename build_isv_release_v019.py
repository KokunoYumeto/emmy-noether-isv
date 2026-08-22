#!/usr/bin/env python3
"""Build the frozen v019 Interslavic Latin and Cyrillic readers.

The build is intentionally bounded to the eight authenticated source files in
this working lane.  XeLaTeX runs serially and without shell escape.  The
Cyrillic files are deterministic projections of the Latin edition, not a
second translation witness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release_v019"
BUILD = ROOT / "tmp" / "pdfs" / "isv_release_v019"
SOURCE_DATE_EPOCH = "1787270400"  # 2026-08-21T00:00:00Z

SOURCE_PINS = {
    "source_latin/44-book-isv.tex": (
        168422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    "source_latin/45-isv.tex": (
        26053,
        "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91",
    ),
    "source_latin/base-papers1-43-isv.tex": (
        1894721,
        "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A",
    ),
    "source_latin/bib-isv.tex": (
        10019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
    "source_cyrillic/44-book-isv-cyrl.tex": (
        230370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "source_cyrillic/45-isv-cyrl.tex": (
        35902,
        "E1568BAB1E389E07816178A2FBDEE3833508C79BF0C7C19DD5120812E24646FE",
    ),
    "source_cyrillic/base-papers1-43-isv-cyrl.tex": (
        2706660,
        "23C242AABD938C605A4B2293ED6E68B723F94DBD23279FD8E75CB50CAEF099F1",
    ),
    "source_cyrillic/bib-isv-cyrl.tex": (
        13255,
        "5A6AE75FF94360BC104CE240E0EC18A2329C5229F68B198F763EDF7E786B816B",
    ),
    "assets/authority_rosette_native_supported_mask.png": (
        797,
        "B2AF3955A8255B4A6D925E174B7B81311C64C669CE21B07E75002494E55F2FF5",
    ),
}

SURFACES = {
    "latn": {
        "script": "Latn",
        "components": (
            ("base-papers1-43", "source_latin/base-papers1-43-isv.tex"),
            ("44-book", "source_latin/44-book-isv.tex"),
            ("45", "source_latin/45-isv.tex"),
            ("bib", "source_latin/bib-isv.tex"),
        ),
        "reader": "emmy-noether-interslavic-latin-v019",
    },
    "cyrl": {
        "script": "Cyrl",
        "components": (
            ("base-papers1-43", "source_cyrillic/base-papers1-43-isv-cyrl.tex"),
            ("44-book", "source_cyrillic/44-book-isv-cyrl.tex"),
            ("45", "source_cyrillic/45-isv-cyrl.tex"),
            ("bib", "source_cyrillic/bib-isv-cyrl.tex"),
        ),
        "reader": "emmy-noether-interslavic-cyrillic-v019",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path, *, relative_to: Path = ROOT) -> dict:
    return {
        "path": path.resolve().relative_to(relative_to.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def authenticate_sources() -> None:
    failures: list[str] = []
    for relative, (expected_bytes, expected_sha) in SOURCE_PINS.items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
            continue
        actual = (path.stat().st_size, sha256(path))
        expected = (expected_bytes, expected_sha)
        if actual != expected:
            failures.append(f"pin mismatch {relative}: expected {expected}, got {actual}")
    if failures:
        raise RuntimeError("\n".join(failures))


def install_exact(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.is_file() and sha256(target) == sha256(source):
            return
        raise FileExistsError(f"refusing to replace non-identical release file: {target}")
    shutil.copy2(source, target)
    if target.read_bytes() != source.read_bytes():
        raise RuntimeError(f"copy verification failed: {target}")


def write_exact(path: Path, text: str) -> None:
    payload = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise FileExistsError(f"refusing to replace non-identical authored file: {path}")
    path.write_bytes(payload)


def prepare_release_sources() -> list[dict]:
    installed: list[dict] = []
    for relative in SOURCE_PINS:
        source = ROOT / relative
        if relative.startswith("source_latin/"):
            target = RELEASE / "source" / "latn" / source.name
        elif relative.startswith("source_cyrillic/"):
            target = RELEASE / "source" / "cyrl" / source.name
        else:
            target = RELEASE / "source" / "assets" / source.name
        install_exact(source, target)
        installed.append(record(target))
    return installed


def warning_summary(log_path: Path) -> dict:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    return {
        "missing_character": lowered.count("missing character:"),
        "undefined_reference": lowered.count("reference")
        if "there were undefined references" in lowered
        else 0,
        "undefined_citation": lowered.count("citation")
        if "there were undefined citations" in lowered
        else 0,
        "overfull_hbox": lowered.count("overfull \\hbox"),
        "overfull_vbox": lowered.count("overfull \\vbox"),
    }


def run_xelatex(source: Path, build_dir: Path, jobname: str) -> tuple[Path, list[dict]]:
    build_dir.mkdir(parents=True, exist_ok=True)
    logs: list[dict] = []
    environment = os.environ.copy()
    environment.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
        }
    )
    for pass_number in (1, 2):
        command = [
            "xelatex",
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-jobname={jobname}",
            f"-output-directory={build_dir.resolve()}",
            str(source.resolve()),
        ]
        completed = subprocess.run(
            command,
            cwd=source.parent,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout_path = build_dir / f"pass{pass_number}.stdout.log"
        stdout_path.write_text(completed.stdout, encoding="utf-8", newline="\n")
        tex_log = build_dir / f"{jobname}.log"
        entry = {
            "pass": pass_number,
            "exit_code": completed.returncode,
            "stdout": record(stdout_path),
        }
        if tex_log.exists():
            entry["tex_log"] = record(tex_log)
            entry["warnings"] = warning_summary(tex_log)
        logs.append(entry)
        if completed.returncode:
            raise RuntimeError(f"XeLaTeX failed for {source}; see {stdout_path}")
    produced = build_dir / f"{jobname}.pdf"
    if not produced.is_file():
        raise FileNotFoundError(produced)
    final_warnings = logs[-1].get("warnings", {})
    for key in ("missing_character", "undefined_reference", "undefined_citation"):
        if final_warnings.get(key):
            raise RuntimeError(f"release-blocking {key} in {build_dir / (jobname + '.log')}")
    return produced, logs


def page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def install_generated(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".new")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(source, temporary)
    if temporary.read_bytes() != source.read_bytes():
        raise RuntimeError(f"generated copy verification failed: {target}")
    os.replace(temporary, target)


def cumulative_recipe(surface: str, component_pdfs: list[Path]) -> Path:
    reader = SURFACES[surface]["reader"]
    recipe = RELEASE / "source" / f"{reader}.tex"
    lines = [
        "% Portable cumulative reader recipe; component hashes are in evidence/build-manifest.json.",
        r"\documentclass{article}",
        r"\usepackage{pdfpages}",
        r"\begin{document}",
    ]
    for component in component_pdfs:
        relative = Path("..") / "pdf" / "components" / component.name
        lines.append(r"\includepdf[pages=-]{" + relative.as_posix() + "}")
    lines.append(r"\end{document}")
    write_exact(recipe, "\n".join(lines) + "\n")
    return recipe


def build_release() -> dict:
    source_records = prepare_release_sources()
    (RELEASE / "pdf" / "components").mkdir(parents=True, exist_ok=True)
    (RELEASE / "evidence").mkdir(parents=True, exist_ok=True)
    surface_records: dict[str, dict] = {}

    for surface, spec in SURFACES.items():
        components: list[dict] = []
        component_outputs: list[Path] = []
        for stem, relative in spec["components"]:
            source_dir = "latn" if surface == "latn" else "cyrl"
            source = RELEASE / "source" / source_dir / Path(relative).name
            jobname = f"{stem}-isv-{surface}"
            produced, logs = run_xelatex(
                source,
                BUILD / "components" / surface / stem,
                jobname,
            )
            output = RELEASE / "pdf" / "components" / f"{jobname}.pdf"
            install_generated(produced, output)
            component_outputs.append(output)
            components.append(
                {
                    "component": stem,
                    "source": record(source),
                    "pdf": {**record(output), "pages": page_count(output)},
                    "build_logs": logs,
                }
            )

        recipe = cumulative_recipe(surface, component_outputs)
        reader_name = spec["reader"]
        produced, logs = run_xelatex(
            recipe,
            BUILD / "readers" / surface,
            reader_name,
        )
        reader_output = RELEASE / "pdf" / f"{reader_name}.pdf"
        install_generated(produced, reader_output)
        expected_pages = sum(item["pdf"]["pages"] for item in components)
        actual_pages = page_count(reader_output)
        if actual_pages != expected_pages:
            raise RuntimeError(
                f"cumulative page mismatch {surface}: {actual_pages} != {expected_pages}"
            )
        surface_records[surface] = {
            "language": "Interslavic",
            "language_tag": f"isv-{spec['script']}",
            "witness_role": "canonical Latin edition"
            if surface == "latn"
            else "deterministic script projection; not an independent translation witness",
            "components": components,
            "cumulative_recipe": record(recipe),
            "reader_pdf": {**record(reader_output), "pages": actual_pages},
            "build_logs": logs,
        }

    manifest = {
        "schema": "noether-interslavic-build-manifest/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-21T00:00:00Z",
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "build_policy": {
            "engine": "XeLaTeX",
            "passes_per_document": 2,
            "serial": True,
            "shell_escape": False,
            "release_blockers": [
                "nonzero engine exit",
                "missing glyph",
                "undefined reference",
                "undefined citation",
                "cumulative page mismatch",
            ],
        },
        "authenticated_inputs": {
            relative: {"bytes": size, "sha256": digest}
            for relative, (size, digest) in SOURCE_PINS.items()
        },
        "installed_release_sources": source_records,
        "surfaces": surface_records,
    }
    manifest_path = RELEASE / "evidence" / "build-manifest.json"
    payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(payload)
    reread = json.loads(manifest_path.read_text(encoding="utf-8"))
    if reread != manifest:
        raise RuntimeError("build manifest readback mismatch")
    return {**manifest, "manifest": record(manifest_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="authenticate inputs and install exact release source copies only",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="run the complete serial two-script build",
    )
    args = parser.parse_args()
    if args.prepare_only == args.build:
        parser.error("select exactly one of --prepare-only or --build")
    authenticate_sources()
    if args.prepare_only:
        installed = prepare_release_sources()
        print(json.dumps({"status": "PASS", "installed": installed}, indent=2))
        return 0
    result = build_release()
    print(
        json.dumps(
            {
                "status": "PASS",
                "manifest": result["manifest"],
                "readers": {
                    surface: data["reader_pdf"]
                    for surface, data in result["surfaces"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
