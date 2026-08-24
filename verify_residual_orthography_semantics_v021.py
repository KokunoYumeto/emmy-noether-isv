#!/usr/bin/env python3
"""Independent, read-only verifier for ISV021-EDIT-0002.

This verifier does not import the applicator.  It reconstructs the five-family
transform from the pinned Latin cohort, checks the official dictionary rows and
house-corpus controls, and accepts either the exact predecessor or the exact
projected successor as the live state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
DICTIONARY = Path(
    r"<WORKSPACE_ROOT>\01_methodology\claude_fable_program"
    r"\data\interslavic_dictionary_official_snapshot_20260816\source_sheet_basic.csv"
)
DICTIONARY_PIN = (
    8101157,
    "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561",
)
DICTIONARY_ARCHIVE = Path(
    r"<WORKSPACE_ROOT>\01_methodology\claude_fable_program"
    r"\data\interslavic_dictionary_official_snapshot_20260816"
    r"\upstream_repository_0fab0c5b4463118d46b1cdcd506926d8848052c9.zip"
)
DICTIONARY_ARCHIVE_PIN = (
    11271766,
    "E02AA89235E4A7B536F3D762126293A3E348319CA1B11CBF8D219A65D03172BE",
)
GERMAN_AUTHORITY = Path(
    r"<WORKSPACE_ROOT>\03_projects\noether"
    r"\07_german_canon_control\candidates\ED0015\noether.tex"
)
GERMAN_AUTHORITY_PIN = (
    2154017,
    "51A25101C04877AE740989E72B2AD65A7A7E65B081077C4A518BF1737AD5B907",
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
PREDECESSOR = {
    "44-book-isv.tex": (168422, "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F"),
    "45-isv.tex": (26053, "A52ADE5B028E40677D7C689C5C6E63C9FE7102F543B8BF7FFFCB0E19576A44CF"),
    "base-papers1-43-isv.tex": (1894703, "041FFBA15D5333962D9E1B2DE6925E1372446F5996F3DC2AA57A67F9B9113AA9"),
    "bib-isv.tex": (10019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}
SUCCESSOR = {
    "44-book-isv.tex": (168422, "1B7432A5D2D8BF31D286CCDE43D6935BE3619C06D6C3582B60BF680591625A68"),
    "45-isv.tex": (26038, "636E873287E0127A58DCBF014CB3C0343EF9D4545D90C2A6475E9F1E5F8B8ADD"),
    "base-papers1-43-isv.tex": (1894577, "EACFE1473BBF5D82A4B07309C33787A198FE9B111F2228323D4A6076578D389E"),
    "bib-isv.tex": (10019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}
EXPECTED_LOCATOR_SHA256 = "979566CAC52BD2005F4141681500C7FB364F92AE9686072C520C22AB03A4EF97"
EXPECTED_FAMILIES = {
    "pomoč_to_pomoć": 96,
    "celost_to_cělost": 5,
    "imenujuče_to_imenno": 4,
    "vrědnost_noun_to_cěnnost": 125,
    "cěločislovn_to_cěločislov": 5,
}
EXPECTED_BY_FILE = {
    "44-book-isv.tex": 1,
    "45-isv.tex": 20,
    "base-papers1-43-isv.tex": 214,
    "bib-isv.tex": 0,
}

PATTERNS = {
    "pomoč_to_pomoć": re.compile(r"\b(?:pomoč|Pomoč)\w*\b", re.UNICODE),
    "celost_to_cělost": re.compile(r"\bcelost(?:i)?\b", re.UNICODE),
    "imenujuče_to_imenno": re.compile(r"\bimenujuče\b", re.UNICODE),
    "vrědnost_noun_to_cěnnost": re.compile(
        r"\b(?:vrědnost|Vrědnost)(?!ny\b)\w*\b", re.UNICODE
    ),
    "cěločislovn_to_cěločislov": re.compile(
        r"\bcěločislovn\w*\b", re.UNICODE
    ),
}
HOLD_PATTERNS = {
    "vrědnostny": re.compile(r"\bvrědnostny\b", re.UNICODE),
    "bare_čislovno": re.compile(r"\bčislovno\b", re.UNICODE),
}
EXPECTED_HOLDS = {"vrědnostny": 1, "bare_čislovno": 1}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> tuple[int, str]:
    return len(data), digest(data)


def pin_dict(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": digest(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def replace(family: str, token: str) -> str:
    if family == "pomoč_to_pomoć":
        if token.startswith("Pomoč"):
            return "Pomoć" + token[5:]
        return "pomoć" + token[5:]
    if family == "celost_to_cělost":
        return {"celost": "cělost", "celosti": "cělosti"}[token]
    if family == "imenujuče_to_imenno":
        return "imenno"
    if family == "vrědnost_noun_to_cěnnost":
        if token.startswith("Vrědnost"):
            return "Cěnnost" + token[8:]
        return "cěnnost" + token[8:]
    if family == "cěločislovn_to_cěločislov":
        return "cěločislov" + token[len("cěločislovn") :]
    raise AssertionError(family)


def unescaped(text: str, index: int, character: str) -> bool:
    if text[index] != character:
        return False
    slashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        slashes += 1
        cursor -= 1
    return slashes % 2 == 0


def visible_prose(line: str, start: int) -> bool:
    comment = next(
        (i for i, char in enumerate(line) if char == "%" and unescaped(line, i, "%")),
        None,
    )
    if comment is not None and start > comment:
        return False
    dollar_count = sum(
        1 for i, char in enumerate(line[:start]) if char == "$" and unescaped(line, i, "$")
    )
    return dollar_count % 2 == 0


def structure(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    comments = [
        line[next(i for i, c in enumerate(line) if c == "%" and unescaped(line, i, "%")) :]
        for line in text.splitlines()
        if any(c == "%" and unescaped(line, i, "%") for i, c in enumerate(line))
    ]
    return {
        "line_count": text.count("\n") + 1,
        "terminal_lf": text.endswith("\n"),
        "braces": [text.count("{"), text.count("}")],
        "commands": [len(commands), digest("\n".join(commands).encode("utf-8"))],
        "environments": [
            len(environments),
            digest("\n".join(environments).encode("utf-8")),
        ],
        "labels": [len(labels), digest("\n".join(labels).encode("utf-8"))],
        "math_delimiters": [
            len(delimiters),
            digest("\n".join(delimiters).encode("utf-8")),
        ],
        "comments": [len(comments), digest("\n".join(comments).encode("utf-8"))],
    }


def project_file(name: str, data: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    text = data.decode("utf-8", errors="strict")
    output_parts: list[str] = []
    locators: list[dict[str, Any]] = []
    reverse: list[tuple[int, int, str, str]] = []
    output_cursor = 0

    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        hits: list[tuple[int, int, str, str]] = []
        for family, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                hits.append((match.start(), match.end(), family, match.group(0)))
        hits.sort(key=lambda item: item[0])
        for left, right in zip(hits, hits[1:]):
            if left[1] > right[0]:
                raise RuntimeError(f"overlapping targets in {name}:{line_number}")

        cursor = 0
        for start, end, family, before in hits:
            if not visible_prose(line, start):
                raise RuntimeError(f"non-prose target in {name}:{line_number}:{start + 1}")
            after = replace(family, before)
            unchanged = line[cursor:start]
            output_parts.append(unchanged)
            output_cursor += len(unchanged)
            out_start = output_cursor
            output_parts.append(after)
            output_cursor += len(after)
            reverse.append((out_start, output_cursor, before, after))
            locators.append(
                {
                    "file": name,
                    "line": line_number,
                    "column": start + 1,
                    "family": family,
                    "before": before,
                    "after": after,
                }
            )
            cursor = end
        tail = line[cursor:]
        output_parts.append(tail)
        output_cursor += len(tail)

    output_text = "".join(output_parts)
    reverse_parts: list[str] = []
    cursor = 0
    for start, end, before, after in reverse:
        if output_text[start:end] != after:
            raise RuntimeError(f"reverse locator drift in {name}")
        reverse_parts.extend((output_text[cursor:start], before))
        cursor = end
    reverse_parts.append(output_text[cursor:])
    if "".join(reverse_parts).encode("utf-8") != data:
        raise RuntimeError(f"reverse replay failed in {name}")
    if structure(text) != structure(output_text):
        raise RuntimeError(f"structural stream changed in {name}")
    return output_text.encode("utf-8"), locators


def dictionary_evidence() -> dict[str, Any]:
    csv_bytes = DICTIONARY.read_bytes()
    archive_bytes = DICTIONARY_ARCHIVE.read_bytes()
    german_bytes = GERMAN_AUTHORITY.read_bytes()
    if pin(csv_bytes) != DICTIONARY_PIN:
        raise RuntimeError("official dictionary CSV pin drift")
    if pin(archive_bytes) != DICTIONARY_ARCHIVE_PIN:
        raise RuntimeError("official dictionary archive pin drift")
    if pin(german_bytes) != GERMAN_AUTHORITY_PIN:
        raise RuntimeError("German comparison authority pin drift")
    rows = {row["id"]: row for row in csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig")))}
    expected = {
        "19667": ("cělosť", "entirety", "Gesamtheit"),
        "2281": ("cěnnosť", "value", "Wert"),
        "17486": ("imenno", "namely", "nämlich"),
        "3945": ("pomoć", "help, assistance, aid", "!Hilfe, Hilfe, Hilfe"),
        "100": ("pomoćny", "helpful, auxiliary", "!hilfreich, Hilfs"),
    }
    observed: dict[str, Any] = {}
    for row_id, (isv, english, german) in expected.items():
        row = rows.get(row_id)
        if row is None or (row["isv"], row["en"], row["de"]) != (isv, english, german):
            raise RuntimeError(f"official dictionary row drift: {row_id}")
        observed[row_id] = {"isv": isv, "en": english, "de": german}
    return {
        "dictionary_csv": pin_dict(csv_bytes),
        "dictionary_archive": pin_dict(archive_bytes),
        "german_authority": pin_dict(german_bytes),
        "rows": observed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    live_pins = {name: pin(data) for name, data in cohort.items()}
    if live_pins == PREDECESSOR:
        live_state = "predecessor"
        basis = cohort
    elif live_pins == SUCCESSOR:
        live_state = "successor"
        basis = {}
    else:
        raise RuntimeError(f"live cohort pin drift: {live_pins}")

    locators: list[dict[str, Any]] = []
    projected: dict[str, bytes] = {}
    if live_state == "predecessor":
        for name in SOURCE_ORDER:
            projected[name], local = project_file(name, basis[name])
            locators.extend(local)
        projected_pins = {name: pin(data) for name, data in projected.items()}
        if projected_pins != SUCCESSOR:
            raise RuntimeError(f"independent successor pin mismatch: {projected_pins}")
        family_counts = dict(Counter(item["family"] for item in locators))
        by_file = dict(Counter(item["file"] for item in locators))
        by_file = {name: by_file.get(name, 0) for name in SOURCE_ORDER}
        if family_counts != EXPECTED_FAMILIES or by_file != EXPECTED_BY_FILE:
            raise RuntimeError(f"independent locator count mismatch: {family_counts}, {by_file}")
        locator_bytes = canonical_bytes(locators)
        if digest(locator_bytes) != EXPECTED_LOCATOR_SHA256:
            raise RuntimeError("independent locator manifest mismatch")
    else:
        projected_pins = live_pins
        receipt_path = (
            ROOT
            / "decision_records"
            / "ISV021-EDIT-0002-UNAPPLIED-CANDIDATE-RECEIPT-R2.json"
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        locators = receipt["locators"]
        locator_bytes = canonical_bytes(locators)
        if digest(locator_bytes) != EXPECTED_LOCATOR_SHA256:
            raise RuntimeError("frozen candidate locator manifest drift")
        family_counts = dict(Counter(item["family"] for item in locators))
        by_file_counter = Counter(item["file"] for item in locators)
        by_file = {name: by_file_counter.get(name, 0) for name in SOURCE_ORDER}
        if family_counts != EXPECTED_FAMILIES or by_file != EXPECTED_BY_FILE:
            raise RuntimeError("frozen candidate locator counts drift")

        for name in SOURCE_ORDER:
            lines = cohort[name].decode("utf-8", errors="strict").splitlines(
                keepends=True
            )
            local = [item for item in locators if item["file"] == name]
            by_line: dict[int, list[dict[str, Any]]] = {}
            for item in local:
                by_line.setdefault(item["line"], []).append(item)
            for line_number, items in by_line.items():
                line = lines[line_number - 1]
                spans: list[tuple[int, int, str]] = []
                cumulative_delta = 0
                for item in sorted(items, key=lambda value: value["column"]):
                    start = item["column"] - 1 + cumulative_delta
                    end = start + len(item["after"])
                    if line[start:end] != item["after"]:
                        raise RuntimeError(
                            f"successor reverse locator drift in {name}:{line_number}:{start + 1}"
                        )
                    spans.append((start, end, item["before"]))
                    cumulative_delta += len(item["after"]) - len(item["before"])
                for start, end, before in reversed(spans):
                    line = line[:start] + before + line[end:]
                lines[line_number - 1] = line
            restored = "".join(lines).encode("utf-8")
            if pin(restored) != PREDECESSOR[name]:
                raise RuntimeError(f"exact successor reverse failed for {name}")
            if structure(restored.decode("utf-8")) != structure(
                cohort[name].decode("utf-8")
            ):
                raise RuntimeError(f"successor reverse structure drift in {name}")

    combined = "\n".join(data.decode("utf-8") for data in cohort.values())
    holds = {name: len(pattern.findall(combined)) for name, pattern in HOLD_PATTERNS.items()}
    if holds != EXPECTED_HOLDS:
        raise RuntimeError(f"hold inventory drift: {holds}")
    residue = {
        family: sum(len(pattern.findall(combined)) for pattern in [PATTERNS[family]])
        for family in PATTERNS
    }
    if live_state == "successor" and any(residue.values()):
        raise RuntimeError(f"successor residue: {residue}")

    evidence = dictionary_evidence()
    report = {
        "schema": "noether-isv-v021-edit0002-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0002",
        "status": f"PASS_{live_state.upper()}",
        "live_state": live_state,
        "live_sources": {name: pin_dict(data) for name, data in cohort.items()},
        "projected_successor": {
            name: {"bytes": value[0], "sha256": value[1]}
            for name, value in projected_pins.items()
        },
        "coverage": {
            "sites": sum(EXPECTED_FAMILIES.values()),
            "physical_lines": 191,
            "families": family_counts,
            "sites_by_file": by_file,
            "holds": holds,
            "live_residue": residue,
            "existing_cěločislov_house_precedent_before": 111,
            "cěločislov_house_total_after": 116,
            "imenujuče_exact_lines": [89, 209, 553, 573],
        },
        "locator_manifest": {
            "canonical_bytes": 31440,
            "sha256": EXPECTED_LOCATOR_SHA256,
            "independently_reconstructed_live": live_state == "predecessor",
            "frozen_candidate_authenticated_for_live_reverse": live_state == "successor",
        },
        "replay": {
            "exact_reverse": True,
            "structure_equal": True,
            "strict_utf8": True,
            "visible_prose_only": True,
        },
        "authority": evidence,
        "semantic_disposition": {
            "pomoć": "official headword and adjective; 96 nonstandard č spellings regularized to ć",
            "cělost": "official cělosť root; house edition omits final soft-sign diacritic in productive -ost nouns",
            "imenno": "all four Paper 45 contexts introduce a specification equivalent to namely",
            "cěnnost": "official cěnnosť = mathematical value/Wert; only noun vrědnost- value contexts are included",
            "cěločislov": "five -n- adjective forms join 111 established cěločislov- house forms; bare čislovno remains held",
        },
        "claims": {
            "files_written": False,
            "native_or_community_certification": False,
            "comprehension_study": False,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
        },
        "tool": pin_dict(Path(__file__).read_bytes()),
    }
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=args.compact,
            separators=(",", ":") if args.compact else None,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
