#!/usr/bin/env python3
"""Read-only audit for the v021 mathematical ``sumand`` family.

The audit authenticates the EDIT-0007 cohort, replaces the isolated lexical
misrendering ``sčestnikov`` with the locally established genitive plural
``sumandov``, and normalizes seven double-m ``summand`` variants to the
edition-wide single-m house spelling.  It never writes source files.
"""

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
SOURCE_PINS = {
    "44-book-isv.tex": (
        168_410,
        "77A0DA8AE3385520C12D91795CE645944AE7CE60F7F7831D3A7CE47BC76A27F5",
    ),
    "45-isv.tex": (
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_581,
        "C33CF08D12E98E198C6BCAB122567930DD2466F2A5115E450A4C16274CED44C8",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
GERMAN_PATH = Path(
    r"<WORKSPACE_ROOT>\03_projects\noether"
    r"\07_german_canon_control\candidates\ED0015\noether.tex"
)
GERMAN_PIN = (
    2_154_017,
    "51A25101C04877AE740989E72B2AD65A7A7E65B081077C4A518BF1737AD5B907",
)
DICTIONARY_PATH = Path(
    r"<WORKSPACE_ROOT>\01_methodology"
    r"\claude_fable_program\data"
    r"\interslavic_dictionary_official_snapshot_20260816"
    r"\source_sheet_basic.csv"
)
DICTIONARY_PIN = (
    8_101_157,
    "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561",
)

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
EXPECTED_TOKEN_COUNTS = Counter(
    {
        "sumand": 16,
        "sumandami": 1,
        "sumandov": 2,
        "sumandy": 7,
        "summand": 4,
        "summandov": 2,
        "summandy": 1,
        "sčestnikov": 1,
    }
)
EXPECTED_REPLACEMENT_COUNTS = Counter(
    {"summand": 4, "summandov": 2, "summandy": 1, "sčestnikov": 1}
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"{label} pin drift: {observed}")
    return data


def read_cohort() -> dict[str, bytes]:
    cohort: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        data = authenticate(SOURCE_DIR / filename, SOURCE_PINS[filename], filename)
        data.decode("utf-8", errors="strict")
        cohort[filename] = data
    return cohort


def replacement(token: str) -> str | None:
    if token == "sčestnikov":
        return "sumandov"
    if token.startswith("summand"):
        return "sumand" + token[len("summand") :]
    return None


def relevant(token: str) -> bool:
    return token == "sčestnikov" or token.startswith(("sumand", "summand"))


def escaped(text: str, index: int) -> bool:
    count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        count += 1
        cursor -= 1
    return bool(count % 2)


def assert_visible(line: str, column0: int, label: str) -> None:
    for match in re.finditer("%", line):
        if match.start() < column0 and not escaped(line, match.start()):
            raise RuntimeError(f"target follows TeX comment at {label}")
    prefix = line[:column0]
    dollars = sum(
        1 for match in re.finditer(r"\$", prefix) if not escaped(prefix, match.start())
    )
    if dollars % 2:
        raise RuntimeError(f"target is inside inline math at {label}")


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    math_delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "line_count": text.count("\n") + 1,
        "open_braces": text.count("{"),
        "close_braces": text.count("}"),
        "percent_count": text.count("%"),
        "commands_count": len(commands),
        "commands_sha256": sha256("\n".join(commands).encode("utf-8")),
        "environments_count": len(environments),
        "environments_sha256": sha256("\n".join(environments).encode("utf-8")),
        "labels_count": len(labels),
        "labels_sha256": sha256("\n".join(labels).encode("utf-8")),
        "math_delimiters_count": len(math_delimiters),
        "math_delimiters_sha256": sha256(
            "\n".join(math_delimiters).encode("utf-8")
        ),
    }


def scan(cohort: dict[str, bytes]) -> tuple[list[dict[str, Any]], Counter[str]]:
    manifest: list[dict[str, Any]] = []
    census: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        byte_line_start = 0
        for line_no, line_with_eol in enumerate(text.splitlines(keepends=True), start=1):
            line = line_with_eol.rstrip("\r\n")
            for match in WORD_RE.finditer(line):
                token = match.group(0)
                if not relevant(token):
                    continue
                census[token] += 1
                after = replacement(token)
                if after is None:
                    continue
                assert_visible(line, match.start(), f"{filename}:{line_no}")
                byte_offset0 = byte_line_start + len(
                    line[: match.start()].encode("utf-8")
                )
                manifest.append(
                    {
                        "file": filename,
                        "line": line_no,
                        "column": match.start() + 1,
                        "byte_offset0": byte_offset0,
                        "before": token,
                        "after": after,
                        "family": (
                            "german_aligned_summand_lexeme"
                            if token == "sčestnikov"
                            else "single_m_sumand_house_spelling"
                        ),
                    }
                )
            byte_line_start += len(line_with_eol.encode("utf-8"))
    return manifest, census


def transform_one(data: bytes, items: list[dict[str, Any]], forward: bool) -> bytes:
    output = data
    for item in sorted(items, key=lambda value: value["byte_offset0"], reverse=True):
        old_text = item["before"] if forward else item["after"]
        new_text = item["after"] if forward else item["before"]
        old = old_text.encode("utf-8")
        new = new_text.encode("utf-8")
        offset = item["byte_offset0"]
        if output[offset : offset + len(old)] != old:
            raise RuntimeError(
                f"payload drift at {item['file']}:{item['line']}:{item['column']}"
            )
        output = output[:offset] + new + output[offset + len(old) :]
    output.decode("utf-8", errors="strict")
    return output


def shifted_for_successor(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    shrink = 0
    for item in sorted(items, key=lambda value: value["byte_offset0"]):
        adjusted = dict(item)
        adjusted["byte_offset0"] = item["byte_offset0"] - shrink
        result.append(adjusted)
        shrink += len(item["before"].encode("utf-8")) - len(
            item["after"].encode("utf-8")
        )
    return result


def project(
    cohort: dict[str, bytes], manifest: list[dict[str, Any]]
) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        items = [item for item in manifest if item["file"] == filename]
        outputs[filename] = transform_one(cohort[filename], items, True)
        reversed_bytes = transform_one(
            outputs[filename], shifted_for_successor(items), False
        )
        if reversed_bytes != cohort[filename]:
            raise RuntimeError(f"exact reverse failed for {filename}")
        if structural_signature(cohort[filename].decode("utf-8")) != structural_signature(
            outputs[filename].decode("utf-8")
        ):
            raise RuntimeError(f"protected TeX structure changed in {filename}")
    return outputs


def projected_census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        for match in WORD_RE.finditer(text):
            token = match.group(0)
            if relevant(token):
                result[token] += 1
    return result


def authenticate_authorities(cohort: dict[str, bytes]) -> dict[str, Any]:
    german = authenticate(GERMAN_PATH, GERMAN_PIN, "German authority")
    german_lines = german.decode("utf-8", errors="strict").splitlines()
    german_line = german_lines[10128]
    required_german = (
        "additiven Zerlegung der Restgruppe",
        "immer nur \\emph{endlich} viele Summanden auftreten",
    )
    for needle in required_german:
        if needle not in german_line:
            raise RuntimeError(f"German line 10129 evidence drift: {needle}")

    base_lines = cohort["base-papers1-43-isv.tex"].decode("utf-8").splitlines()
    controls = {
        10959: "konečno mnogo sčestnikov",
        11321: "za dva sumandy",
        11350: "sogrupujemo sumandy",
        11352: "v \\(k\\) sumandov",
    }
    for line_no, needle in controls.items():
        if needle not in base_lines[line_no - 1]:
            raise RuntimeError(f"local terminology control drift at line {line_no}")

    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    dictionary_text = dictionary.decode("utf-8-sig", errors="strict")
    if ",suma,,f.,1,sum," not in dictionary_text:
        raise RuntimeError("official suma headword absent")
    for absent in (",sčestnik,", ",sumand,", ",summand,"):
        if absent in dictionary_text:
            raise RuntimeError(f"dictionary-silence premise drift: {absent}")

    return {
        "german_ed0015": {
            "path": str(GERMAN_PATH),
            **pin(german),
            "line": 10129,
            "finding": "The aligned source says finitely many Summanden.",
        },
        "local_interslavic_controls": {
            "file": "base-papers1-43-isv.tex",
            "lines": [10959, 11321, 11350, 11352],
            "finding": "The same paper uses single-m sumandy/sumandov for the exact aligned concept; mnogo governs genitive plural sumandov.",
        },
        "official_dictionary": {
            "path": str(DICTIONARY_PATH),
            **pin(dictionary),
            "finding": "Official suma is present; the exact technical nouns sčestnik, sumand, and summand are absent, so direct aligned usage controls the technical term.",
        },
    }


def build_report() -> dict[str, Any]:
    cohort = read_cohort()
    authorities = authenticate_authorities(cohort)
    manifest, census = scan(cohort)
    if census != EXPECTED_TOKEN_COUNTS:
        raise RuntimeError(f"sumand-family census drift: {dict(census)}")
    replacement_counts = Counter(item["before"] for item in manifest)
    if replacement_counts != EXPECTED_REPLACEMENT_COUNTS:
        raise RuntimeError(f"replacement census drift: {dict(replacement_counts)}")
    if len(manifest) != 8 or len({(i["file"], i["line"]) for i in manifest}) != 8:
        raise RuntimeError("site or physical-line cardinality drift")
    if {item["file"] for item in manifest} != {"base-papers1-43-isv.tex"}:
        raise RuntimeError("target escaped base source")

    outputs = project(cohort, manifest)
    after_census = projected_census(outputs)
    expected_after = Counter(
        {"sumand": 20, "sumandami": 1, "sumandov": 5, "sumandy": 8}
    )
    if after_census != expected_after:
        raise RuntimeError(f"projected census drift: {dict(after_census)}")
    manifest_bytes = canonical_bytes(manifest)
    return {
        "schema": "noether-isv-v021-sumand-family-audit-v1",
        "edit_id": "ISV021-EDIT-0008",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "coverage": {
            "family_tokens_including_sčestnikov": sum(census.values()),
            "sites": len(manifest),
            "physical_lines": 8,
            "lexical_repairs": 1,
            "double_m_normalizations": 7,
            "predecessor_census": dict(sorted(census.items())),
            "projected_census": dict(sorted(after_census.items())),
        },
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": manifest,
        },
        "authorities": authorities,
        "adverse_evidence": [
            "The official dictionary has no exact sumand or summand headword.",
            "Seven double-m tokens form a local repeated cluster rather than a single keystroke, but they have no semantic, grammatical, quotation, or protected-identity distinction and every inflection has an exact single-m control.",
        ],
        "validation": {
            "exact_reverse": True,
            "utf8": True,
            "visible_prose_only": True,
            "protected_tex_structure_equal": True,
            "source_writes": 0,
        },
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
