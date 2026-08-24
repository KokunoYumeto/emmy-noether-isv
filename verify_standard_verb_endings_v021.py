#!/usr/bin/env python3
"""Independent predecessor/successor verifier for ISV021-EDIT-0006.

This verifier deliberately imports neither the audit, the applicator, nor the
transaction core.  It authenticates the frozen candidate receipt, independently
replays its canonical locator manifest in both directions, checks exact cohort
pins and protected TeX structure, and rechecks the pinned language authorities.
"""

from __future__ import annotations

from collections import Counter
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
RECEIPT_PATH = (
    ROOT
    / "decision_records"
    / "ISV021-EDIT-0006-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    69_344,
    "DE3986DB5A0EA5F96EFE17EEB70A013E550E1C2BD8F55CBF1FD6F930A93CB1F8",
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
PREDECESSOR = {
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
SUCCESSOR = {
    "44-book-isv.tex": (
        168_410,
        "77A0DA8AE3385520C12D91795CE645944AE7CE60F7F7831D3A7CE47BC76A27F5",
    ),
    "45-isv.tex": (
        26_041,
        "90825271429A2D3156FE752E8925D8D43DC34B5B962234DFA2EFD5D425A23FE8",
    ),
    "base-papers1-43-isv.tex": (
        1_894_589,
        "F84470C69F8D54103F7BB0DB38CCBA43D632F3113BBA17FA9E66D450A9384FC2",
    ),
    "bib-isv.tex": (
        10_021,
        "01DDAB0D12E697DDE422B8871CC5587E5AC5A69B66AB8B9E868A998E16CC982C",
    ),
}
EXPECTED_LOCATOR_BYTES = 6_900
EXPECTED_LOCATOR_SHA256 = (
    "EFC90C292CEEE0DB9148BFA7EE53ED7DBB631A6378960BF23B73EBB7275D9E51"
)
ENDING_ET_NASAL_RE = re.compile(r"(?<![^\W\d_])([^\W\d_]+ęt)(?![^\W\d_])")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    observed = (len(data), sha256(data))
    if observed != expected:
        raise RuntimeError(f"{label} pin drift: {observed}")
    return data


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


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


def escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return bool(backslashes % 2)


def assert_visible(line: str, column0: int, label: str) -> None:
    for match in re.finditer("%", line):
        if match.start() < column0 and not escaped(line, match.start()):
            raise RuntimeError(f"locator after comment at {label}")
    prefix = line[:column0]
    dollars = sum(
        1
        for match in re.finditer(r"\$", prefix)
        if not escaped(prefix, match.start())
    )
    if dollars % 2:
        raise RuntimeError(f"locator inside inline math at {label}")


def line_starts(text: str) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    return starts


def authenticate_authorities() -> dict[str, Any]:
    grammar = authenticate(GRAMMAR_PATH, GRAMMAR_PIN, "grammar")
    grammar_lines = grammar.decode("utf-8", errors="strict").splitlines()
    if grammar_lines[84] != "- Second conjugation (`i` conjugation): **-`ju`, -`iš`, -`i`, -`imo`, -`ite`, -`et`**":
        raise RuntimeError("grammar -et statement drift")
    if "replacing the ending `-t` of the 3rd person plural by `-či`" not in grammar_lines[171]:
        raise RuntimeError("grammar 3pl/participle statement drift")
    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    dictionary_text = dictionary.decode("utf-8-sig", errors="strict")
    for expected in ("**tvoret**", "**naležet**"):
        if expected not in dictionary_text:
            raise RuntimeError(f"dictionary example absent: {expected}")
    prior = authenticate(PRIOR_DECISION_PATH, PRIOR_DECISION_PIN, "prior decision")
    prior_value = json.loads(prior.decode("utf-8", errors="strict"))
    if "official second-conjugation third-person plural is prinaležet" not in str(
        prior_value.get("alternatives_rejected", [])
    ):
        raise RuntimeError("prior -et adjudication drift")
    return {
        "grammar": {"path": str(GRAMMAR_PATH), **pin(grammar)},
        "dictionary": {"path": str(DICTIONARY_PATH), **pin(dictionary)},
        "prior_decision": {"path": str(PRIOR_DECISION_PATH), **pin(prior)},
    }


def load_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt status drift")
    block = receipt.get("locator_manifest", {})
    manifest = block.get("value")
    if not isinstance(manifest, list):
        raise RuntimeError("candidate locator manifest absent")
    payload = canonical_bytes(manifest)
    if (len(payload), sha256(payload)) != (
        EXPECTED_LOCATOR_BYTES,
        EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("canonical locator manifest drift")
    if len(manifest) != 53:
        raise RuntimeError("locator site count drift")
    if len({(item["file"], item["line"]) for item in manifest}) != 49:
        raise RuntimeError("locator physical-line count drift")
    return manifest, {"path": str(RECEIPT_PATH), **pin(receipt_bytes)}


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    for data in cohort.values():
        data.decode("utf-8", errors="strict")
    return cohort


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def transform_direction(
    cohort: dict[str, bytes], manifest: list[dict[str, Any]], forward: bool
) -> tuple[dict[str, bytes], dict[str, Any]]:
    by_file: dict[str, list[dict[str, Any]]] = {name: [] for name in SOURCE_ORDER}
    for item in manifest:
        by_file[str(item["file"])].append(item)
    outputs: dict[str, bytes] = {}
    structures: dict[str, Any] = {}

    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        starts = line_starts(text)
        located: list[tuple[int, str, str, dict[str, Any]]] = []
        for item in by_file[filename]:
            line_no = int(item["line"])
            column = int(item["column"])
            source_value = str(item["before"] if forward else item["after"])
            target_value = str(item["after"] if forward else item["before"])
            start = starts[line_no - 1] + column - 1
            if text[start : start + len(source_value)] != source_value:
                raise RuntimeError(
                    f"locator mismatch {filename}:{line_no}:{column}: {source_value!r}"
                )
            line_end = text.find("\n", starts[line_no - 1])
            if line_end == -1:
                line_end = len(text)
            line = text[starts[line_no - 1] : line_end].rstrip("\r")
            assert_visible(line, column - 1, f"{filename}:{line_no}:{column}")
            located.append((start, source_value, target_value, item))

        projected = text
        for start, source_value, target_value, _ in reversed(
            sorted(located, key=lambda value: value[0])
        ):
            projected = (
                projected[:start]
                + target_value
                + projected[start + len(source_value) :]
            )
        before_structure = structural_signature(text)
        after_structure = structural_signature(projected)
        if before_structure != after_structure:
            raise RuntimeError(f"protected structure changed in {filename}")
        outputs[filename] = projected.encode("utf-8")
        structures[filename] = before_structure
    return outputs, structures


def residue(cohort: dict[str, bytes], state: str) -> dict[str, Any]:
    tokens: list[str] = []
    for name in SOURCE_ORDER:
        text = cohort[name].decode("utf-8", errors="strict")
        tokens.extend(match.group(1) for match in ENDING_ET_NASAL_RE.finditer(text))
    counts = Counter(tokens)
    bib = cohort["bib-isv.tex"].decode("utf-8", errors="strict")
    if state == "predecessor":
        if sum(counts.values()) != 54 or counts.get("vzęt") != 3:
            raise RuntimeError("predecessor word-final -ęt census drift")
        if bib.count("Čest IV") != 2:
            raise RuntimeError("predecessor bibliography wrapper census drift")
    else:
        if counts != Counter({"vzęt": 3}):
            raise RuntimeError("successor word-final -ęt residue drift")
        if bib.count("Čest IV") != 0 or bib.count("Čęst IV") != 2:
            raise RuntimeError("successor bibliography wrapper census drift")
    return {
        "word_final_et_nasal": dict(sorted(counts.items())),
        "Čest_IV": bib.count("Čest IV"),
        "Čęst_IV": bib.count("Čęst IV"),
    }


def main() -> int:
    authorities = authenticate_authorities()
    manifest, receipt = load_manifest()
    cohort = read_cohort()
    pins = observed_pins(cohort)
    if pins == PREDECESSOR:
        state = "predecessor"
        outputs, structures = transform_direction(cohort, manifest, True)
        if observed_pins(outputs) != SUCCESSOR:
            raise RuntimeError("independent forward successor mismatch")
        reversed_outputs, _ = transform_direction(outputs, manifest, False)
        if reversed_outputs != cohort:
            raise RuntimeError("independent reverse did not restore predecessor")
    elif pins == SUCCESSOR:
        state = "successor"
        outputs, structures = transform_direction(cohort, manifest, False)
        if observed_pins(outputs) != PREDECESSOR:
            raise RuntimeError("independent reverse predecessor mismatch")
        forward_outputs, _ = transform_direction(outputs, manifest, True)
        if forward_outputs != cohort:
            raise RuntimeError("independent forward did not restore successor")
    else:
        raise RuntimeError(f"live cohort is neither frozen state: {pins}")

    report = {
        "schema": "noether-isv-v021-edit0006-independent-verifier-v1",
        "status": f"PASS_{state.upper()}",
        "state": state,
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "opposite_state": {name: pin(outputs[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "locator_manifest": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "canonical_bytes": EXPECTED_LOCATOR_BYTES,
            "sha256": EXPECTED_LOCATOR_SHA256,
        },
        "authorities": authorities,
        "residue": residue(cohort, state),
        "validation": {
            "strict_utf8": True,
            "locator_visible_text": True,
            "exact_bidirectional_replay": True,
            "protected_structure_equal": True,
            "structural_signatures": structures,
            "imports_applicator_audit_or_core": False,
            "writes": 0,
        },
        "tool": {"path": str(Path(__file__).resolve()), **pin(Path(__file__).read_bytes())},
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
