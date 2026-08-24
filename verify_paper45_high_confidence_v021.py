#!/usr/bin/env python3
"""Independent no-write verifier for ISV021-EDIT-0003 R2."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
EDIT_ID = "ISV021-EDIT-0003"
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
PREDECESSOR = {
    "44-book-isv.tex": (168422, "1B7432A5D2D8BF31D286CCDE43D6935BE3619C06D6C3582B60BF680591625A68"),
    "45-isv.tex": (26038, "636E873287E0127A58DCBF014CB3C0343EF9D4545D90C2A6475E9F1E5F8B8ADD"),
    "base-papers1-43-isv.tex": (1894577, "EACFE1473BBF5D82A4B07309C33787A198FE9B111F2228323D4A6076578D389E"),
    "bib-isv.tex": (10019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}
SUCCESSOR = {
    **PREDECESSOR,
    "45-isv.tex": (26043, "403E22F8770C9180ED2A54430CDE0E09F6E3DDF919115413E11A05CFA16B8C11"),
}
MANIFEST: list[dict[str, Any]] = [
    {"after": "Čęst", "before": "Čest", "column": 8, "family": "P45-NEXT-WRAP-001", "file": "45-isv.tex", "line": 30},
    {"after": "Čęst", "before": "Čest", "column": 29, "family": "P45-NEXT-WRAP-001", "file": "45-isv.tex", "line": 31},
    {"after": "najmenše", "before": "prinajmenje", "column": 54, "family": "P45-NEXT-001", "file": "45-isv.tex", "line": 55},
    {"after": "zadače", "before": "zadači", "column": 13, "family": "P45-NEXT-002", "file": "45-isv.tex", "line": 89},
    {"after": "k prostějšej", "before": "k prostějši", "column": 20, "family": "P45-NEXT-002", "file": "45-isv.tex", "line": 89},
    {"after": "S obzirom na produktny teorem rezultantov", "before": "S urědnjenjem produktnogo teorema rezultantov", "column": 1, "family": "P45-NEXT-003", "file": "45-isv.tex", "line": 213},
    {"after": "vzame v obzir", "before": "urědni", "column": 1, "family": "P45-NEXT-004", "file": "45-isv.tex", "line": 266},
    {"after": "nahodęt", "before": "nahodet", "column": 20, "family": "P45-NEXT-005", "file": "45-isv.tex", "line": 274},
    {"after": "najmenšim", "before": "prinajmenje", "column": 45, "family": "P45-NEXT-006", "file": "45-isv.tex", "line": 278},
    {"after": "takogo", "before": "takoho", "column": 25, "family": "P45-NEXT-006", "file": "45-isv.tex", "line": 279},
    {"after": "jedinym uslovjem", "before": "jedino uslovjem", "column": 44, "family": "P45-NEXT-007", "file": "45-isv.tex", "line": 327},
    {"after": "navedenom", "before": "navednom", "column": 49, "family": "P45-NEXT-008", "file": "45-isv.tex", "line": 361},
    {"after": "jednakogo", "before": "jednakoho", "column": 30, "family": "P45-NEXT-009", "file": "45-isv.tex", "line": 384},
    {"after": "govoręt", "before": "govoret", "column": 34, "family": "P45-NEXT-010", "file": "45-isv.tex", "line": 458},
    {"after": "primarny komponent", "before": "primarna komponenta", "column": 47, "family": "P45-NEXT-011", "file": "45-isv.tex", "line": 489},
    {"after": "taky stepen", "before": "tak stepen", "column": 27, "family": "P45-NEXT-012", "file": "45-isv.tex", "line": 575},
    {"after": "taky stepen", "before": "tako stepen", "column": 39, "family": "P45-NEXT-012", "file": "45-isv.tex", "line": 590},
]
MANIFEST_PIN = (1966, "46D716A8490E90C5514775664E312C1495EC517527645B476CA68393CBDA165A")
APPLICATOR_PIN = (17269, "D45050E5EEA9EEB72ADDD0A11C93BBF66E757BF20AACDFE91C9A0A3CA243A0E8")
CANDIDATE_RECEIPT = ROOT / "decision_records" / "ISV021-EDIT-0003-UNAPPLIED-CANDIDATE-RECEIPT-R2.json"
CANDIDATE_RECEIPT_PIN = (9159, "C7F2AD8E72446B89EA4817523D286FA2464C3A51B25C5A4E852F38754E63A38B")
DICTIONARY = Path(
    r"<WORKSPACE_ROOT>\01_methodology\claude_fable_program"
    r"\data\interslavic_dictionary_official_snapshot_20260816\source_sheet_basic.csv"
)
DICTIONARY_PIN = (8101157, "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561")
GERMAN = Path(
    r"<WORKSPACE_ROOT>\03_projects\noether"
    r"\07_german_canon_control\candidates\ED0015\noether.tex"
)
GERMAN_PIN = (2154017, "51A25101C04877AE740989E72B2AD65A7A7E65B081077C4A518BF1737AD5B907")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": digest(data)}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_cohort() -> dict[str, bytes]:
    return {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), digest(data)) for name, data in cohort.items()}


def starts(text: str) -> list[int]:
    output = [0]
    output.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    return output


def visible(line: str, column0: int) -> bool:
    prefix = line[:column0]
    comment = next((m.start() for m in re.finditer(r"(?<!\\)%", line)), None)
    if comment is not None and comment < column0:
        return False
    return len(re.findall(r"(?<!\\)\$", prefix)) % 2 == 0


def locate(text: str, state: str) -> list[dict[str, Any]]:
    line_starts = starts(text)
    shifts: defaultdict[int, int] = defaultdict(int)
    located: list[dict[str, Any]] = []
    for item in MANIFEST:
        line = int(item["line"])
        base_column = int(item["column"])
        if state == "predecessor":
            column = base_column
            surface = str(item["before"])
        else:
            column = base_column + shifts[line]
            surface = str(item["after"])
        index = line_starts[line - 1] + column - 1
        if text[index : index + len(surface)] != surface:
            raise RuntimeError(f"{state} locator mismatch at {line}:{column}")
        line_end = text.find("\n", line_starts[line - 1])
        if line_end == -1:
            line_end = len(text)
        if not visible(text[line_starts[line - 1] : line_end], column - 1):
            raise RuntimeError(f"non-visible locator at {line}:{column}")
        record = dict(item)
        record["char_index0"] = index
        record["live_column"] = column
        located.append(record)
        if state == "successor":
            shifts[line] += len(str(item["after"])) - len(str(item["before"]))
    ordered = sorted(located, key=lambda item: int(item["char_index0"]))
    for left, right in zip(ordered, ordered[1:]):
        surface = str(left["before"] if state == "predecessor" else left["after"])
        if int(left["char_index0"]) + len(surface) > int(right["char_index0"]):
            raise RuntimeError("locator overlap")
    return located


def replay(text: str, state: str) -> tuple[str, list[dict[str, Any]]]:
    located = locate(text, state)
    output = text
    for item in sorted(located, key=lambda value: int(value["char_index0"]), reverse=True):
        start = int(item["char_index0"])
        old = str(item["before"] if state == "predecessor" else item["after"])
        new = str(item["after"] if state == "predecessor" else item["before"])
        output = output[:start] + new + output[start + len(old) :]
    return output, located


def signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    references = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "lines": text.count("\n") + 1,
        "open_braces": text.count("{"),
        "close_braces": text.count("}"),
        "percents": text.count("%"),
        "commands": [len(commands), digest("\n".join(commands).encode())],
        "environments": [len(environments), digest("\n".join(environments).encode())],
        "references": [len(references), digest("\n".join(references).encode())],
        "math_delimiters": [len(delimiters), digest("\n".join(delimiters).encode())],
    }


def authenticate_receipt() -> dict[str, Any]:
    data = CANDIDATE_RECEIPT.read_bytes()
    if (len(data), digest(data)) != CANDIDATE_RECEIPT_PIN:
        raise RuntimeError("candidate receipt pin drift")
    value = json.loads(data.decode("utf-8"))
    if value.get("edit_id") != EDIT_ID or value.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt identity drift")
    tool = value.get("tool", {})
    if (tool.get("bytes"), tool.get("sha256")) != APPLICATOR_PIN:
        raise RuntimeError("candidate receipt applicator pin drift")
    projected = value.get("projected_successor", {}).get("45-isv.tex", {})
    if (projected.get("bytes"), projected.get("sha256")) != SUCCESSOR["45-isv.tex"]:
        raise RuntimeError("candidate receipt successor drift")
    locator = value.get("audit", {}).get("locator_manifest", {})
    if (locator.get("canonical_bytes"), locator.get("sha256")) != MANIFEST_PIN:
        raise RuntimeError("candidate receipt locator drift")
    return pin(data)


def authenticate_authority() -> dict[str, Any]:
    dictionary_data = DICTIONARY.read_bytes()
    german_data = GERMAN.read_bytes()
    if (len(dictionary_data), digest(dictionary_data)) != DICTIONARY_PIN:
        raise RuntimeError("dictionary pin drift")
    if (len(german_data), digest(german_data)) != GERMAN_PIN:
        raise RuntimeError("German authority pin drift")
    row = None
    with DICTIONARY.open("r", encoding="utf-8", newline="") as handle:
        for candidate in csv.reader(handle):
            if candidate and candidate[0] == "20148":
                row = candidate
                break
    if row is None or row[1] != "komponent" or row[3] != "m.":
        raise RuntimeError("official masculine komponent row drift")
    return {
        "dictionary": pin(dictionary_data),
        "german_ed0015": pin(german_data),
        "dictionary_row_20148": {"isv": row[1], "part_of_speech": row[3]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    manifest_bytes = canonical(MANIFEST)
    if (len(manifest_bytes), digest(manifest_bytes)) != MANIFEST_PIN:
        raise RuntimeError("independent manifest pin mismatch")
    cohort = read_cohort()
    live_pins = observed_pins(cohort)
    if live_pins == PREDECESSOR:
        live_state = "predecessor"
    elif live_pins == SUCCESSOR:
        live_state = "successor"
    else:
        raise RuntimeError(f"live cohort pin drift: {live_pins}")

    live_text = cohort["45-isv.tex"].decode("utf-8", errors="strict")
    opposite_text, located = replay(live_text, live_state)
    opposite_bytes = opposite_text.encode("utf-8")
    expected_opposite = SUCCESSOR if live_state == "predecessor" else PREDECESSOR
    if (len(opposite_bytes), digest(opposite_bytes)) != expected_opposite["45-isv.tex"]:
        raise RuntimeError("opposite-state replay pin mismatch")
    roundtrip_text, _ = replay(
        opposite_text, "successor" if live_state == "predecessor" else "predecessor"
    )
    if roundtrip_text != live_text:
        raise RuntimeError("exact roundtrip replay failed")
    if signature(live_text) != signature(opposite_text):
        raise RuntimeError("protected structural signature changed")

    report = {
        "schema": "noether-isv-v021-edit0003-independent-verification-v1",
        "edit_id": EDIT_ID,
        "status": "PASS_PREDECESSOR" if live_state == "predecessor" else "PASS_SUCCESSOR",
        "live_state": live_state,
        "live_sources": {name: pin(data) for name, data in cohort.items()},
        "opposite_paper45": pin(opposite_bytes),
        "coverage": {
            "sites": len(MANIFEST),
            "physical_lines": len({item["line"] for item in MANIFEST}),
            "families": dict(sorted(Counter(item["family"] for item in MANIFEST).items())),
        },
        "locator_manifest": {"canonical_bytes": len(manifest_bytes), "sha256": digest(manifest_bytes)},
        "replay": {"exact_roundtrip": True, "structure_equal": True, "visible_text_only": True},
        "candidate_receipt": authenticate_receipt(),
        "authority": authenticate_authority(),
        "tool": pin(Path(__file__).read_bytes()),
        "claims": {"files_written": False, "build": False, "render": False, "git": False, "network": False, "publication": False},
    }
    if args.compact:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
