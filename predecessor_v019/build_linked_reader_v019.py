#!/usr/bin/env python3
"""Build and validate the bilingual, two-script NOETHER-ISV-v019 reader."""

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
RELEASE = ROOT / "release_v019"
SOURCE = RELEASE / "source" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.tex"
BUILD = ROOT / "tmp" / "pdfs" / "isv_release_v019" / "linked-reader"
OUTPUT = RELEASE / "public" / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
RECEIPT = RELEASE / "evidence" / "linked-reader-build.json"
SOURCE_DATE_EPOCH = "1787356800"
SOURCE_PIN = (
    10_267,
    "BE720AEE4ED8825C9F47590E28EB8DBC284DD95CECFA7348DF08467D447268E1",
)
INPUTS = {
    "release_v019/pdf/emmy-noether-interslavic-latin-v019.pdf": (
        3_000_508,
        "5FCC44BF0D25C3DA0C14C8542CDFEB48419EE924ADD197227F70008FF076FF4F",
        565,
    ),
    "release_v019/pdf/emmy-noether-interslavic-cyrillic-v019.pdf": (
        3_300_454,
        "578AAB7224B4192006096B231FD67A3AFEE6E22DFF0C94264102B6D192687B75",
        588,
    ),
}
EXPECTED_FRONT_AND_DIVIDER_PAGES = 6
EXPECTED_TOTAL_PAGES = 1_159


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


def authenticate() -> list[dict[str, Any]]:
    if (SOURCE.stat().st_size, sha256(SOURCE)) != SOURCE_PIN:
        raise RuntimeError("linked-reader TeX pin drift")
    rows = []
    for relative, (size, digest, pages) in INPUTS.items():
        path = ROOT / relative
        reader = PdfReader(str(path))
        actual = (path.stat().st_size, sha256(path), len(reader.pages))
        expected = (size, digest, pages)
        if actual != expected:
            raise RuntimeError(f"reader input pin drift: {relative}: {actual}")
        rows.append({**record(path), "pages": pages})
    return rows


def run_xelatex() -> list[dict[str, Any]]:
    BUILD.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({"SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH, "FORCE_SOURCE_DATE": "1", "TZ": "UTC"})
    logs = []
    for pass_number in (1, 2):
        command = [
            "xelatex",
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "-jobname=00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER",
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
        if completed.returncode:
            raise RuntimeError(f"XeLaTeX linked-reader pass {pass_number} failed; see {stdout}")
        tex_log = BUILD / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.log"
        text = tex_log.read_text(encoding="utf-8", errors="replace")
        always_fatal = [
            token
            for token in (
                "Missing character:",
                "Undefined control sequence",
                "Fatal error",
            )
            if token.casefold() in text.casefold()
        ]
        final_pass_fatal = [
            token
            for token in (
                "There were undefined references",
                "There were undefined citations",
            )
            if pass_number == 2 and token.casefold() in text.casefold()
        ]
        fatal = always_fatal + final_pass_fatal
        if fatal:
            raise RuntimeError(f"linked-reader log blocker: {fatal}")
        logs.append({"pass": pass_number, "exit_code": completed.returncode, "stdout": record(stdout), "tex_log": record(tex_log)})
    return logs


def outline_titles(items: Any) -> list[str]:
    titles: list[str] = []
    for item in items:
        if isinstance(item, list):
            titles.extend(outline_titles(item))
        else:
            title = getattr(item, "title", None)
            if title:
                titles.append(str(title))
    return titles


def main() -> int:
    inputs = authenticate()
    logs = run_xelatex()
    produced = BUILD / "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf"
    if not produced.is_file():
        raise FileNotFoundError(produced)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".pdf.new")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(produced, temporary)
    if temporary.read_bytes() != produced.read_bytes():
        raise RuntimeError("linked-reader stage mismatch")
    os.replace(temporary, OUTPUT)

    reader = PdfReader(str(OUTPUT))
    pages = len(reader.pages)
    input_pages = sum(row["pages"] for row in inputs)
    if pages != EXPECTED_TOTAL_PAGES or pages - input_pages != EXPECTED_FRONT_AND_DIVIDER_PAGES:
        raise RuntimeError(f"linked-reader page topology drift: {pages}, inputs {input_pages}")
    annotations = 0
    for page in reader.pages[:6]:
        annots = page.get("/Annots", [])
        if hasattr(annots, "get_object"):
            annots = annots.get_object()
        annotations += len(annots)
    titles = outline_titles(reader.outline)
    required_titles = (
        "Naslov / Title",
        "Kako čitati izdanje",
        "How to read this edition",
        "Sodržanje / Contents",
        "Čest A: Latinica / Part A: Latin script",
        "Čest B: Kirilica / Part B: Cyrillic script",
    )
    if not all(title in titles for title in required_titles):
        raise RuntimeError(f"linked-reader outline drift: {titles}")
    if annotations < 8:
        raise RuntimeError(f"linked-reader link annotation count too small: {annotations}")

    front_text_path = RELEASE / "evidence" / "linked-reader-frontmatter.txt"
    completed = subprocess.run(
        ["pdftotext", "-f", "1", "-l", "6", "-layout", str(OUTPUT.resolve()), str(front_text_path.resolve())],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(f"frontmatter extraction failed: {completed.stderr}")
    front_text = front_text_path.read_text(encoding="utf-8", errors="replace")
    required_text = (
        "Polno medžuslovjansko",
        "Complete Interslavic Corpus Edition",
        "10.5281/zenodo.22050935",
        "10.5281/zenodo.21926382",
        "Kako čitati tuto izdanje",
        "How to read this edition",
        "isv-Latn",
        "isv-Cyrl",
    )
    if "\ufffd" in front_text or not all(token in front_text for token in required_text):
        raise RuntimeError("linked-reader frontmatter text gate failed")

    receipt = {
        "schema": "noether-interslavic-linked-reader-build/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-22T00:00:00Z",
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "source": record(SOURCE),
        "inputs": inputs,
        "build": {"engine": "XeLaTeX", "passes": 2, "serial": True, "shell_escape": False, "logs": logs},
        "output": {**record(OUTPUT), "pages": pages},
        "page_topology": {"front_and_divider_pages": pages - input_pages, "embedded_reader_pages": input_pages},
        "navigation": {"outline_titles": titles, "frontmatter_link_annotations": annotations},
        "frontmatter_text": {**record(front_text_path), "required_tokens": list(required_text), "replacement_characters": front_text.count("\ufffd")},
        "status": "PASS",
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if json.loads(RECEIPT.read_text(encoding="utf-8")) != receipt:
        raise RuntimeError("linked-reader receipt readback mismatch")
    print(json.dumps({"status": "PASS", "output": receipt["output"], "receipt": record(RECEIPT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
