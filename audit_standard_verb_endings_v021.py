#!/usr/bin/env python3
"""Read-only audit for the ISV021 second-conjugation 3pl residual family.

The audit authenticates the exact EDIT-0005 Latin cohort and its local primary
language authorities, enumerates every Unicode word ending in ``-ęt``, retains
the three past-participle ``vzęt`` tokens, projects all finite second-conjugation
3pl forms to official ``-et``, and also projects the two bibliography wrapper
headings from ``Čest IV`` to the already-established ``Čęst IV`` spelling.

It never writes source files.  The projected bytes, exact reverse replay,
visible-text locators, and protected TeX structural signatures are reported so
that a separately frozen transactional applicator can be reviewed before use.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
CORE_PATH = ROOT / "apply_residual_orthography_semantics_v021.py"
CORE_PIN = (
    29_146,
    "C47DBFC4221DC99B2072491034ECDB9FD0C7ADE6D1BD4800333CB82FBAC4EB87",
)

GRAMMAR_PATH = (
    ROOT.parent
    / "00_lane_control"
    / "marginal_intelligibility_20260811"
    / "authority_snapshots"
    / "snapshots"
    / "official_site"
    / "docs"
    / "learn"
    / "grammar"
    / "verbs.md"
)
GRAMMAR_PIN = (
    21_426,
    "3684BE0634F0163DDD4BEC09719280C3C0E1E2367009AA3DAE584C50DD6249AD",
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
PRIOR_DECISION_PATH = (
    ROOT.parent
    / "noether_isv_v019_working"
    / "decision_records"
    / "ISV019-EDIT-0045.json"
)
PRIOR_DECISION_PIN = (
    4_930,
    "0DB148CAA43E014256D239E441EE992664D27B4BEB6BC51D6E55F3688EFDDF71",
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
SOURCE_PINS = {
    "44-book-isv.tex": (
        168_427,
        "D3029CFFB856ACF30E55DEA6086AE3E63F90AA733BBD1B2F0E4DC19D9CB05F88",
    ),
    "45-isv.tex": (
        26_043,
        "403E22F8770C9180ED2A54430CDE0E09F6E3DDF919115413E11A05CFA16B8C11",
    ),
    "base-papers1-43-isv.tex": (
        1_894_621,
        "2EA6BC47DDFFB8190B2865A5DD2138628922A517FF1158EE23A2884725E68CD9",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}

# Python's [^\W\d_] is a Unicode-letter class.  The explicit boundaries keep
# the scanner from treating a suffix embedded in a longer identifier as a word.
ENDING_ET_NASAL_RE = re.compile(r"(?<![^\W\d_])([^\W\d_]+ęt)(?![^\W\d_])")
EXPECTED_TOKEN_COUNTS = {
    "govoręt": 2,
    "gubęt": 1,
    "musęt": 1,
    "nahodęt": 1,
    "odnosęt": 2,
    "prěhodęt": 5,
    "prohodęt": 1,
    "stojęt": 1,
    "tvoręt": 21,
    "vhodęt": 7,
    "vzęt": 3,
    "zavisęt": 9,
}
EXPECTED_REPLACEMENT_COUNTS = {
    "44-book-isv.tex": 17,
    "45-isv.tex": 2,
    "base-papers1-43-isv.tex": 32,
    "bib-isv.tex": 2,
}
EXPECTED_RETAIN_COUNTS = {"vzęt": 3}
BIB_LOCATORS = (
    {
        "file": "bib-isv.tex",
        "line": 25,
        "column": 8,
        "before": "Čest IV",
        "after": "Čęst IV",
        "family": "bibliography_part_wrapper",
    },
    {
        "file": "bib-isv.tex",
        "line": 26,
        "column": 29,
        "before": "Čest IV",
        "after": "Čęst IV",
        "family": "bibliography_part_wrapper",
    },
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


def load_core() -> Any:
    core_bytes = authenticate(CORE_PATH, CORE_PIN, "transaction core")
    module = types.ModuleType("isv021_edit0002_core_for_read_only_audit")
    module.__file__ = str(CORE_PATH)
    module.__package__ = ""
    exec(compile(core_bytes, str(CORE_PATH), "exec"), module.__dict__)
    return module


CORE = load_core()


def authenticate_authorities() -> dict[str, Any]:
    grammar_bytes = authenticate(GRAMMAR_PATH, GRAMMAR_PIN, "official grammar")
    grammar_lines = grammar_bytes.decode("utf-8", errors="strict").splitlines()
    required_grammar = {
        75: "- Second conjugation:",
        76: "  - verbs on `-iti` and most verbs on `-ěti` have the present tense stem `-i-`: :isv[hvaliti] > :isv[hval-i-] „to praise”, :isv[viděti] > :isv[vid-i-] „to see”",
        85: "- Second conjugation (`i` conjugation): **-`ju`, -`iš`, -`i`, -`imo`, -`ite`, -`et`**",
    }
    for line_no, expected in required_grammar.items():
        if grammar_lines[line_no - 1] != expected:
            raise RuntimeError(f"official grammar line {line_no} drifted")
    if "replacing the ending `-t` of the 3rd person plural by `-či`" not in grammar_lines[171]:
        raise RuntimeError("official grammar participle derivation line drifted")

    dictionary_bytes = authenticate(
        DICTIONARY_PATH, DICTIONARY_PIN, "official dictionary snapshot"
    )
    dictionary_text = dictionary_bytes.decode("utf-8-sig", errors="strict")
    if "**tvoret**" not in dictionary_text:
        raise RuntimeError("official dictionary example tvoret is absent")
    if "**naležet**" not in dictionary_text:
        raise RuntimeError("official dictionary example naležet is absent")

    prior_bytes = authenticate(
        PRIOR_DECISION_PATH, PRIOR_DECISION_PIN, "prior Interslavic decision"
    )
    prior = json.loads(prior_bytes.decode("utf-8", errors="strict"))
    if prior.get("decision_id") != "ISV019-EDIT-0045":
        raise RuntimeError("prior decision identity drifted")
    if "official second-conjugation third-person plural is prinaležet" not in str(
        prior.get("alternatives_rejected", [])
    ):
        raise RuntimeError("prior decision no longer states the -et authority")

    return {
        "official_grammar": {
            "path": str(GRAMMAR_PATH),
            **pin(grammar_bytes),
            "lines": [75, 76, 85, 172],
            "finding": "Second-conjugation 3pl ends in -et; present active participles derive from that 3pl -t form.",
        },
        "official_dictionary_snapshot": {
            "path": str(DICTIONARY_PATH),
            **pin(dictionary_bytes),
            "examples": ["tvoret", "naležet"],
        },
        "prior_project_decision": {
            "path": str(PRIOR_DECISION_PATH),
            **pin(prior_bytes),
            "finding": "ISV019-EDIT-0045 independently recorded official 3pl prinaležet.",
        },
    }


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    observed = {name: (len(data), sha256(data)) for name, data in cohort.items()}
    if observed != SOURCE_PINS:
        raise RuntimeError(f"EDIT-0005 source cohort drift: {observed}")
    for name, data in cohort.items():
        data.decode("utf-8", errors="strict")
    return cohort


def line_start_offsets(text: str) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    return starts


def scan_ending_tokens(
    filename: str, data: bytes
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = data.decode("utf-8", errors="strict")
    replacements: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    char_base = 0
    for line_no, line_with_eol in enumerate(text.splitlines(keepends=True), start=1):
        line = line_with_eol.rstrip("\r\n")
        for match in ENDING_ET_NASAL_RE.finditer(line):
            token = match.group(1)
            CORE.assert_visible_text(line, match.start(1), filename, line_no)
            record = {
                "file": filename,
                "line": line_no,
                "column": match.start(1) + 1,
                "char_index0": char_base + match.start(1),
                "byte_offset0": len(
                    text[: char_base + match.start(1)].encode("utf-8")
                ),
                "before": token,
                "context": line,
            }
            if token == "vzęt":
                record.update(
                    {
                        "classification": "retain_past_passive_participle",
                        "lemma": "vzeti",
                        "after": token,
                    }
                )
                retained.append(record)
            else:
                record.update(
                    {
                        "classification": "correct_second_conjugation_3pl",
                        "after": token[:-2] + "et",
                        "family": "second_conjugation_3pl_et",
                    }
                )
                replacements.append(record)
        char_base += len(line_with_eol)
    return replacements, retained


def locate_bibliography(text: str) -> list[dict[str, Any]]:
    starts = line_start_offsets(text)
    located: list[dict[str, Any]] = []
    for frozen in BIB_LOCATORS:
        line_no = int(frozen["line"])
        column = int(frozen["column"])
        start = starts[line_no - 1] + column - 1
        before = str(frozen["before"])
        if text[start : start + len(before)] != before:
            raise RuntimeError(f"bibliography locator drift at {line_no}:{column}")
        line_end = text.find("\n", starts[line_no - 1])
        if line_end == -1:
            line_end = len(text)
        line = text[starts[line_no - 1] : line_end].rstrip("\r")
        CORE.assert_visible_text(line, column - 1, "bib-isv.tex", line_no)
        located.append(
            {
                **frozen,
                "char_index0": start,
                "byte_offset0": len(text[:start].encode("utf-8")),
                "classification": "align_part_wrapper_with_established_Čęst",
                "context": line,
            }
        )
    if text.count("Čest IV") != 2:
        raise RuntimeError("unexpected bibliography Čest IV residue/count")
    return located


def project_one(
    filename: str, data: bytes, locators: list[dict[str, Any]]
) -> tuple[bytes, dict[str, Any]]:
    text = data.decode("utf-8", errors="strict")
    ordered = sorted(locators, key=lambda item: int(item["char_index0"]))
    for left, right in zip(ordered, ordered[1:]):
        if int(left["char_index0"]) + len(str(left["before"])) > int(
            right["char_index0"]
        ):
            raise RuntimeError(f"overlapping locators in {filename}")

    projected = text
    for item in reversed(ordered):
        start = int(item["char_index0"])
        before = str(item["before"])
        after = str(item["after"])
        if projected[start : start + len(before)] != before:
            raise RuntimeError(f"forward locator drift in {filename}")
        projected = projected[:start] + after + projected[start + len(before) :]

    running_delta = 0
    reverse_locators: list[dict[str, Any]] = []
    for item in ordered:
        projected_start = int(item["char_index0"]) + running_delta
        reverse_locators.append({**item, "projected_char_index0": projected_start})
        running_delta += len(str(item["after"])) - len(str(item["before"]))

    reversed_text = projected
    for item in reversed(reverse_locators):
        start = int(item["projected_char_index0"])
        before = str(item["before"])
        after = str(item["after"])
        if reversed_text[start : start + len(after)] != after:
            raise RuntimeError(f"reverse locator drift in {filename}")
        reversed_text = (
            reversed_text[:start] + before + reversed_text[start + len(after) :]
        )
    if reversed_text != text:
        raise RuntimeError(f"exact reverse replay failed in {filename}")

    before_structure = CORE.structural_signature(text)
    after_structure = CORE.structural_signature(projected)
    if before_structure != after_structure:
        raise RuntimeError(f"protected TeX structure changed in {filename}")
    return projected.encode("utf-8"), before_structure


def build_report() -> dict[str, Any]:
    authorities = authenticate_authorities()
    cohort = read_cohort()
    token_locators: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    by_file: dict[str, list[dict[str, Any]]] = {name: [] for name in SOURCE_ORDER}

    for filename in SOURCE_ORDER:
        replace_here, retain_here = scan_ending_tokens(filename, cohort[filename])
        token_locators.extend(replace_here)
        retained.extend(retain_here)
        by_file[filename].extend(replace_here)

    observed_token_counts = Counter(
        item["before"] for item in token_locators + retained
    )
    if dict(sorted(observed_token_counts.items())) != EXPECTED_TOKEN_COUNTS:
        raise RuntimeError(f"ending-token census drift: {observed_token_counts}")
    if Counter(item["before"] for item in retained) != EXPECTED_RETAIN_COUNTS:
        raise RuntimeError("retained participle census drift")

    bib_text = cohort["bib-isv.tex"].decode("utf-8", errors="strict")
    bib_locators = locate_bibliography(bib_text)
    by_file["bib-isv.tex"].extend(bib_locators)
    all_locators = token_locators + bib_locators

    observed_replacement_counts = {
        name: len(by_file[name]) for name in SOURCE_ORDER
    }
    if observed_replacement_counts != EXPECTED_REPLACEMENT_COUNTS:
        raise RuntimeError(
            f"replacement distribution drift: {observed_replacement_counts}"
        )

    outputs: dict[str, bytes] = {}
    structures: dict[str, Any] = {}
    for filename in SOURCE_ORDER:
        outputs[filename], structures[filename] = project_one(
            filename, cohort[filename], by_file[filename]
        )

    projected_ending_tokens: list[str] = []
    for filename, data in outputs.items():
        text = data.decode("utf-8", errors="strict")
        remaining = [m.group(1) for m in ENDING_ET_NASAL_RE.finditer(text)]
        projected_ending_tokens.extend(remaining)
        if filename == "base-papers1-43-isv.tex":
            if remaining != ["vzęt", "vzęt", "vzęt"]:
                raise RuntimeError("projected retained-token sequence drift")
        elif remaining:
            raise RuntimeError(f"unexpected projected -ęt token in {filename}")
    if projected_ending_tokens != ["vzęt", "vzęt", "vzęt"]:
        raise RuntimeError("projected word-final -ęt census is not retained vzęt only")
    if outputs["bib-isv.tex"].decode("utf-8").count("Čest IV") != 0:
        raise RuntimeError("projected bibliography still contains Čest IV")

    locator_manifest = [
        {
            key: item[key]
            for key in ("file", "line", "column", "before", "after", "family")
        }
        for item in all_locators
    ]
    manifest_bytes = canonical_bytes(locator_manifest)
    physical_lines = len(
        {(item["file"], int(item["line"])) for item in all_locators}
    )
    return {
        "schema": "noether-isv-v021-standard-verb-endings-read-only-audit-v1",
        "edit_id": "ISV021-EDIT-0006",
        "status": "PASS_READ_ONLY_PROJECTED_CANDIDATE",
        "predecessor": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "projected_successor": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "coverage": {
            "all_tokens_ending_et_nasal": len(token_locators) + len(retained),
            "second_conjugation_3pl_repairs": len(token_locators),
            "bibliography_wrapper_repairs": len(bib_locators),
            "total_sites": len(all_locators),
            "physical_lines": physical_lines,
            "replacement_distribution": observed_replacement_counts,
            "token_counts": dict(sorted(observed_token_counts.items())),
        },
        "authorities": authorities,
        "adjudication": {
            "change": "Every audited finite second-conjugation 3pl -ęt form becomes official -et.",
            "retain": "Exactly three vzęt tokens are past passive participles of vzeti, not present-tense 3pl forms.",
            "bibliography": "The Part IV source wrapper is aligned to the established Čęst spelling already used in Parts III and elsewhere.",
            "correction_of_edit0003": [
                "45-isv.tex:274 nahodęt reverses to nahodet",
                "45-isv.tex:458 govoręt reverses to govoret",
            ],
            "uncertain_sites": 0,
        },
        "locators": all_locators,
        "retained": retained,
        "locator_manifest": {
            "canonical_bytes": len(manifest_bytes),
            "sha256": sha256(manifest_bytes),
            "value": locator_manifest,
        },
        "validation": {
            "exact_source_authentication": True,
            "strict_utf8": True,
            "visible_text_only": True,
            "exact_reverse_replay": True,
            "protected_tex_structure_equal": True,
            "structural_signatures": structures,
            "projected_nonparticiple_et_nasal_residue": 0,
            "projected_bibliography_old_wrapper_residue": 0,
        },
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
        "core": {"path": str(CORE_PATH), "bytes": CORE_PIN[0], "sha256": CORE_PIN[1]},
        "claims": {
            "applied": False,
            "source_write": False,
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
