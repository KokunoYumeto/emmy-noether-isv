#!/usr/bin/env python3
"""Build and validate the bilingual NOETHER-ISV-v020 methods paper."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from pypdf import PdfReader


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs" / "METHODS_AI_INTERSLAVIC_NOETHER_v020.tex"
BUILD = ROOT / "tmp" / "pdfs" / "isv_release_v020" / "methods"
OUTPUT_DIR = ROOT / "release_v020" / "evidence" / "methods"
OUTPUT = OUTPUT_DIR / "AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf"
PUBLIC_COPY = ROOT / "docs" / "AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf"
EXTRACTED_TEXT = OUTPUT_DIR / "AI_INTERSLAVIC_NOETHER_METHODS_v020.txt"
RECEIPT = OUTPUT_DIR / "AI_INTERSLAVIC_NOETHER_METHODS_v020.build.json"
JOBNAME = "AI_INTERSLAVIC_NOETHER_METHODS_v020"
SOURCE_DATE_EPOCH = "1787356800"
SOURCE_PIN = (
    42_931,
    "3D374F31126EE2C6BC5523768399491E310E37EB94CE102D9E71611A1B534119",
)
MIN_PAGES = 12
MAX_PAGES = 45

REQUIRED_SOURCE_TOKENS = (
    "NOETHER-ISV-v020",
    "\\part*{Čest I - Polny medžuslovjansky tekst}",
    "\\part*{Part II - Complete English counterpart}",
    "4\\,560",
    "364 klasifikacij",
    "372 efektov",
    "125 linij",
    "309 linij",
    "10.5281/zenodo.22058530",
    "10.5281/zenodo.21926382",
    "B27278EA138724ED258CFE5089CABA70A79C640D0B71CCD9836CA3C8CB8BCD13",
    "4AE9847672AB53F1D5B54468ED9B202D45EF5969C7A34B1CE380B28C6516DB29",
    "CC0",
    "\\end{document}",
)
REQUIRED_PDF_TEXT = (
    "NOETHER-ISV-v020",
    "Čest I - Polny medžuslovjansky tekst",
    "Part II - Complete English counterpart",
    "4,560",
    "372",
    "125",
    "309",
    "10.5281/zenodo.22058530",
    "10.5281/zenodo.21926382",
    "native-speaker certification",
    "CC0",
)
REQUIRED_OUTLINE_TITLES = (
    "Predmet, cělj i čitatelji",
    "Arhitektura avtoriteta i kustodije",
    "Ograničenja, ljudsky pregled i odgovorne tvrdženja",
    "Object, purpose, and readership",
    "Authority and custody architecture",
    "Limitations, human review, and responsible claims",
)
REQUIRED_URIS = (
    "https://doi.org/10.5281/zenodo.22058530",
    "https://doi.org/10.5281/zenodo.21926382",
    "https://github.com/KokunoYumeto/emmy-noether-isv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def dereference(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def authenticate_source() -> dict[str, Any]:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    actual = (SOURCE.stat().st_size, sha256(SOURCE))
    if actual != SOURCE_PIN:
        raise RuntimeError(f"methods TeX pin drift: expected {SOURCE_PIN}, got {actual}")
    source_bytes = SOURCE.read_bytes()
    if b"\r" in source_bytes:
        raise RuntimeError("methods TeX must use LF line endings")
    source_text = source_bytes.decode("utf-8")
    missing = [token for token in REQUIRED_SOURCE_TOKENS if token not in source_text]
    if missing:
        raise RuntimeError(f"methods TeX required-token drift: {missing}")
    if source_text.count("\\begin{document}") != 1 or source_text.count("\\end{document}") != 1:
        raise RuntimeError("methods TeX document-boundary drift")
    unicode_dashes = sorted({character for character in source_text if "\u2010" <= character <= "\u2015"})
    if unicode_dashes:
        raise RuntimeError(f"methods TeX contains non-ASCII dash characters: {unicode_dashes}")
    return record(SOURCE)


def executable(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"required executable not found: {name}")
    return resolved


def log_blockers(text: str, pass_number: int) -> list[str]:
    always_fatal = (
        "Missing character:",
        "Undefined control sequence",
        "Fatal error",
        "Emergency stop",
        "! LaTeX Error:",
        "Overfull \\hbox",
        "Overfull \\vbox",
    )
    final_pass_fatal = (
        "There were undefined references",
        "There were undefined citations",
        "Label(s) may have changed",
        "Rerun to get cross-references right",
    )
    folded = text.casefold()
    blockers = [token for token in always_fatal if token.casefold() in folded]
    if pass_number == 2:
        blockers.extend(token for token in final_pass_fatal if token.casefold() in folded)
    return blockers


def run_xelatex() -> tuple[list[dict[str, Any]], str]:
    xelatex = executable("xelatex")
    BUILD.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
        }
    )
    logs: list[dict[str, Any]] = []
    for pass_number in (1, 2):
        authenticate_source()
        command = [
            xelatex,
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-jobname={JOBNAME}",
            f"-output-directory={BUILD.resolve()}",
            str(SOURCE.resolve()),
        ]
        completed = subprocess.run(
            command,
            cwd=SOURCE.parent,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout = BUILD / f"pass{pass_number}.stdout.log"
        stdout.write_text(completed.stdout, encoding="utf-8", newline="\n")
        generated_log = BUILD / f"{JOBNAME}.log"
        if completed.returncode:
            raise RuntimeError(f"XeLaTeX methods pass {pass_number} failed; see {stdout}")
        if not generated_log.is_file():
            raise FileNotFoundError(generated_log)
        pass_log = BUILD / f"pass{pass_number}.tex.log"
        shutil.copy2(generated_log, pass_log)
        text = pass_log.read_text(encoding="utf-8", errors="replace")
        blockers = log_blockers(text, pass_number)
        if blockers:
            raise RuntimeError(f"methods TeX log blocker on pass {pass_number}: {blockers}")
        authenticate_source()
        logs.append(
            {
                "pass": pass_number,
                "exit_code": completed.returncode,
                "stdout": record(stdout),
                "tex_log": record(pass_log),
            }
        )
    return logs, Path(xelatex).name


def outline_titles(items: Any) -> list[str]:
    titles: list[str] = []
    for item in items:
        if isinstance(item, list):
            titles.extend(outline_titles(item))
            continue
        title = getattr(item, "title", None)
        if title:
            titles.append(str(title))
    return titles


def font_inventory(reader: PdfReader) -> list[dict[str, Any]]:
    inventory: dict[tuple[str, str], dict[str, Any]] = {}
    for page_number, page in enumerate(reader.pages, start=1):
        resources = dereference(page.get("/Resources", {})) or {}
        fonts = dereference(resources.get("/Font", {})) or {}
        for resource_name, reference in fonts.items():
            font = dereference(reference)
            base_font = str(font.get("/BaseFont", resource_name))
            subtype = str(font.get("/Subtype", ""))
            descriptors: list[Any] = []
            direct_descriptor = font.get("/FontDescriptor")
            if direct_descriptor is not None:
                descriptors.append(dereference(direct_descriptor))
            descendants = dereference(font.get("/DescendantFonts", [])) or []
            for descendant_reference in descendants:
                descendant = dereference(descendant_reference)
                descriptor = descendant.get("/FontDescriptor")
                if descriptor is not None:
                    descriptors.append(dereference(descriptor))
            embedded = any(
                any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))
                for descriptor in descriptors
            )
            key = (base_font, subtype)
            row = inventory.setdefault(
                key,
                {
                    "base_font": base_font,
                    "subtype": subtype,
                    "embedded": embedded,
                    "pages": [],
                },
            )
            row["embedded"] = bool(row["embedded"] or embedded)
            row["pages"].append(page_number)
    rows = []
    for row in inventory.values():
        row["pages"] = sorted(set(row["pages"]))
        rows.append(row)
    rows.sort(key=lambda item: (item["base_font"], item["subtype"]))
    if not rows:
        raise RuntimeError("methods PDF contains no fonts")
    unembedded = [row["base_font"] for row in rows if not row["embedded"]]
    if unembedded:
        raise RuntimeError(f"methods PDF has unembedded fonts: {unembedded}")
    return rows


def navigation_inventory(reader: PdfReader) -> dict[str, Any]:
    titles = outline_titles(reader.outline)
    missing_titles = [title for title in REQUIRED_OUTLINE_TITLES if title not in titles]
    if missing_titles:
        raise RuntimeError(f"methods PDF outline drift: missing {missing_titles}")
    annotations = 0
    uris: set[str] = set()
    for page in reader.pages:
        page_annotations = dereference(page.get("/Annots", [])) or []
        for annotation_reference in page_annotations:
            annotation = dereference(annotation_reference)
            annotations += 1
            action = dereference(annotation.get("/A", {})) or {}
            uri = action.get("/URI")
            if uri:
                uris.add(str(uri))
    missing_uris = [uri for uri in REQUIRED_URIS if uri not in uris]
    if annotations < 6 or missing_uris:
        raise RuntimeError(
            f"methods PDF navigation drift: annotations={annotations}, missing URIs={missing_uris}"
        )
    return {
        "outline_titles": titles,
        "link_annotations": annotations,
        "external_uris": sorted(uris),
    }


def extract_and_validate_text() -> dict[str, Any]:
    pdftotext = executable("pdftotext")
    completed = subprocess.run(
        [pdftotext, "-layout", str(OUTPUT.resolve()), str(EXTRACTED_TEXT.resolve())],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(f"methods PDF text extraction failed: {completed.stderr}")
    text = EXTRACTED_TEXT.read_text(encoding="utf-8", errors="replace")
    missing = [token for token in REQUIRED_PDF_TEXT if token not in text]
    if "\ufffd" in text or missing:
        raise RuntimeError(
            f"methods PDF text gate failed: replacements={text.count(chr(0xFFFD))}, missing={missing}"
        )
    primary_position = text.find("Čest I - Polny medžuslovjansky tekst")
    english_position = text.find("Part II - Complete English counterpart")
    if primary_position < 0 or english_position <= primary_position:
        raise RuntimeError("methods PDF bilingual ordering drift")
    if len(text) < 30_000:
        raise RuntimeError(f"methods PDF extracted text unexpectedly short: {len(text)} characters")
    return {
        **record(EXTRACTED_TEXT),
        "characters": len(text),
        "replacement_characters": text.count("\ufffd"),
        "required_tokens": list(REQUIRED_PDF_TEXT),
        "interslavic_precedes_english": True,
    }


def install_and_validate() -> dict[str, Any]:
    produced = BUILD / f"{JOBNAME}.pdf"
    if not produced.is_file():
        raise FileNotFoundError(produced)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    staged = OUTPUT.with_suffix(".pdf.new")
    if staged.exists():
        staged.unlink()
    shutil.copy2(produced, staged)
    if staged.read_bytes() != produced.read_bytes():
        raise RuntimeError("methods PDF stage mismatch")
    os.replace(staged, OUTPUT)
    if OUTPUT.read_bytes() != produced.read_bytes():
        raise RuntimeError("methods PDF installed readback mismatch")
    public_staged = PUBLIC_COPY.with_suffix(".pdf.new")
    if public_staged.exists():
        public_staged.unlink()
    shutil.copy2(OUTPUT, public_staged)
    if public_staged.read_bytes() != OUTPUT.read_bytes():
        raise RuntimeError("methods public-copy stage mismatch")
    os.replace(public_staged, PUBLIC_COPY)
    if PUBLIC_COPY.read_bytes() != OUTPUT.read_bytes():
        raise RuntimeError("methods public-copy installed readback mismatch")

    reader = PdfReader(str(OUTPUT))
    pages = len(reader.pages)
    if not MIN_PAGES <= pages <= MAX_PAGES:
        raise RuntimeError(f"methods PDF page count outside expected bounds: {pages}")
    metadata = reader.metadata or {}
    title = str(metadata.get("/Title", ""))
    author = str(metadata.get("/Author", ""))
    if "Od jezyčnogo kanona" not in title or "Emmy Noether" not in title:
        raise RuntimeError(f"methods PDF title metadata drift: {title!r}")
    if author != "Machine-assisted Interslavic editorial project":
        raise RuntimeError(f"methods PDF author metadata drift: {author!r}")
    navigation = navigation_inventory(reader)
    fonts = font_inventory(reader)
    extracted = extract_and_validate_text()
    return {
        **record(OUTPUT),
        "pages": pages,
        "metadata": {"title": title, "author": author},
        "navigation": navigation,
        "fonts": fonts,
        "extracted_text": extracted,
        "declared_public_copy": record(PUBLIC_COPY),
    }


def write_receipt(receipt: dict[str, Any]) -> None:
    staged = RECEIPT.with_suffix(".json.new")
    if staged.exists():
        staged.unlink()
    staged.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if json.loads(staged.read_text(encoding="utf-8")) != receipt:
        raise RuntimeError("methods build receipt staged readback mismatch")
    os.replace(staged, RECEIPT)
    if json.loads(RECEIPT.read_text(encoding="utf-8")) != receipt:
        raise RuntimeError("methods build receipt installed readback mismatch")


def main() -> int:
    source = authenticate_source()
    logs, engine = run_xelatex()
    authenticate_source()
    output = install_and_validate()
    receipt = {
        "schema": "noether-interslavic-methods-build/1.0",
        "release_id": "NOETHER-ISV-v020",
        "generated_at": "2026-08-22T00:00:00Z",
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "source": source,
        "build": {
            "engine": engine,
            "passes": 2,
            "serial": True,
            "shell_escape": False,
            "logs": logs,
        },
        "output": output,
        "claim_boundary": (
            "Methods and reproducibility report; not native-speaker, community, "
            "official-standard, or independent scholarly-peer-review certification."
        ),
        "status": "PASS",
    }
    write_receipt(receipt)
    print(
        json.dumps(
            {"status": "PASS", "output": output, "receipt": record(RECEIPT)},
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
