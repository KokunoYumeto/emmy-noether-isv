#!/usr/bin/env python3
"""Independent predecessor/successor verifier for ISV021-EDIT-0007.

This verifier imports neither the audit, applicator, nor transaction core.
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
    ROOT / "decision_records" / "ISV021-EDIT-0007-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    9_761,
    "8F846BBF54C0CB5352934B842B153E2B71A862994C3A965FD7ABFB0DA4AD52D9",
)
ORTHOGRAPHY_PATH = (
    ROOT.parent
    / "00_lane_control"
    / "marginal_intelligibility_20260811"
    / "authority_snapshots"
    / "snapshots"
    / "official_site"
    / "docs"
    / "learn"
    / "orthography.md"
)
ORTHOGRAPHY_PIN = (
    16_443,
    "90C609CC0E8709E8395964E9F20D6D4FB4E31159CBC2B1EA515A29D9D1C72044",
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
PRIOR_FREQUENCY_PATH = (
    ROOT.parent
    / "noether_isv_v019_working"
    / "decision_records"
    / "ISV019-EDIT-0077.json"
)
PRIOR_FREQUENCY_PIN = (
    2_844,
    "0E8E055D7904697ECE0F112A71739956C8B291CEE5E545E10DCB61CC9B548E85",
)
PRIOR_BASIC_PATH = (
    ROOT.parent
    / "noether_isv_v019_working"
    / "decision_records"
    / "ISV019-EDIT-0023.json"
)
PRIOR_BASIC_PIN = (
    2_923,
    "601CD6E7676E6748706224BA7B4CEC46967B1E4E027C719FF08A9D8239E92E64",
)
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
PREDECESSOR = {
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
SUCCESSOR = {
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
EXPECTED_LOCATOR_BYTES = 1_844
EXPECTED_LOCATOR_SHA256 = (
    "CEB7980DC06728F6CBD423FBB2B5AC735A37D0997C062DE47E27549E6CA47379"
)
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
TARGETS = {"Čęst": "Čest", "čęst": "čest", "čęsti": "česti", "čęstično": "čestično"}
PREDECESSOR_CENSUS = Counter(
    {
        "čest": 50,
        "čęst": 2,
        "Čęst": 4,
        "čestěje": 1,
        "česti": 47,
        "Česti": 1,
        "čęsti": 1,
        "čestično": 5,
        "čęstično": 5,
        "čestičny": 1,
        "čestij": 12,
        "čestjah": 7,
        "čestju": 5,
        "čestne": 2,
        "čestnomu": 1,
        "čestny": 2,
        "često": 7,
        "najčestěje": 1,
        "sčestnikov": 1,
        "učestjem": 1,
    }
)


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


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def read_cohort() -> dict[str, bytes]:
    cohort = {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}
    for data in cohort.values():
        data.decode("utf-8", errors="strict")
    return cohort


def load_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt_bytes = authenticate(RECEIPT_PATH, RECEIPT_PIN, "candidate receipt")
    receipt = json.loads(receipt_bytes.decode("utf-8", errors="strict"))
    if receipt.get("status") != "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE":
        raise RuntimeError("candidate receipt status drift")
    manifest = receipt.get("locator_manifest", {}).get("value")
    if not isinstance(manifest, list) or len(manifest) != 12:
        raise RuntimeError("candidate manifest absent or wrong cardinality")
    payload = canonical_bytes(manifest)
    if (len(payload), sha256(payload)) != (
        EXPECTED_LOCATOR_BYTES,
        EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("candidate manifest hash drift")
    if Counter(item["before"] for item in manifest) != Counter(
        {"Čęst": 4, "čęst": 2, "čęsti": 1, "čęstično": 5}
    ):
        raise RuntimeError("candidate form census drift")
    for item in manifest:
        if TARGETS.get(item["before"]) != item["after"]:
            raise RuntimeError("candidate mapping drift")
    return manifest, {"path": str(RECEIPT_PATH), **pin(receipt_bytes)}


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


def transform(
    cohort: dict[str, bytes], manifest: list[dict[str, Any]], forward: bool
) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}
    for filename in SOURCE_ORDER:
        data = cohort[filename]
        items = [item for item in manifest if item["file"] == filename]
        if not forward:
            items = shifted_for_successor(items)
        for item in sorted(items, key=lambda value: value["byte_offset0"], reverse=True):
            old_text = item["before"] if forward else item["after"]
            new_text = item["after"] if forward else item["before"]
            old = old_text.encode("utf-8")
            new = new_text.encode("utf-8")
            offset = item["byte_offset0"]
            if data[offset : offset + len(old)] != old:
                raise RuntimeError(
                    f"payload mismatch at {filename}:{item['line']}:{item['column']}"
                )
            data = data[:offset] + new + data[offset + len(old) :]
        data.decode("utf-8", errors="strict")
        outputs[filename] = data
    return outputs


def census(cohort: dict[str, bytes]) -> Counter[str]:
    result: Counter[str] = Counter()
    for filename in SOURCE_ORDER:
        text = cohort[filename].decode("utf-8", errors="strict")
        for match in WORD_RE.finditer(text):
            token = match.group(0)
            folded = token.casefold()
            if "čest" in folded or "čęst" in folded:
                result[token] += 1
    return result


def expected_successor_census() -> Counter[str]:
    result = PREDECESSOR_CENSUS.copy()
    changes = Counter({"Čęst": 4, "čęst": 2, "čęsti": 1, "čęstično": 5})
    for before, count in changes.items():
        result[before] -= count
        if not result[before]:
            del result[before]
        result[TARGETS[before]] += count
    return result


def verify_authorities() -> dict[str, Any]:
    orthography = authenticate(ORTHOGRAPHY_PATH, ORTHOGRAPHY_PIN, "orthography")
    lines = orthography.decode("utf-8", errors="strict").splitlines()
    checks = {
        69: "optional letters",
        80: "simply leaving out the diacritic",
        102: "refrain from using this orthography in everyday conversations",
        104: "use it consistently",
    }
    for line_no, needle in checks.items():
        if needle not in lines[line_no - 1]:
            raise RuntimeError(f"orthography evidence drift at line {line_no}")
    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    dictionary_text = dictionary.decode("utf-8-sig", errors="strict")
    for needle in (
        "čęsť,,f.,1,part",
        "**čestično**",
        "**najčestěje**",
        "**učestnikov**",
    ):
        if needle not in dictionary_text:
            raise RuntimeError(f"dictionary evidence absent: {needle}")
    frequency_bytes = authenticate(
        PRIOR_FREQUENCY_PATH, PRIOR_FREQUENCY_PIN, "frequency decision"
    )
    frequency = json.loads(frequency_bytes.decode("utf-8", errors="strict"))
    if "project spelling najčestěje" not in str(frequency):
        raise RuntimeError("frequency project-spelling decision drift")
    basic_bytes = authenticate(PRIOR_BASIC_PATH, PRIOR_BASIC_PIN, "basic decision")
    basic = json.loads(basic_bytes.decode("utf-8", errors="strict"))
    if "standard project spelling: pytanje" not in str(basic):
        raise RuntimeError("basic project-spelling decision drift")
    return {
        "orthography": {"path": str(ORTHOGRAPHY_PATH), **pin(orthography)},
        "dictionary": {"path": str(DICTIONARY_PATH), **pin(dictionary)},
        "project_decisions": [
            {"path": str(PRIOR_FREQUENCY_PATH), **pin(frequency_bytes)},
            {"path": str(PRIOR_BASIC_PATH), **pin(basic_bytes)},
        ],
    }


def main() -> int:
    manifest, receipt = load_manifest()
    authorities = verify_authorities()
    live = read_cohort()
    live_pins = observed_pins(live)
    if live_pins == PREDECESSOR:
        if census(live) != PREDECESSOR_CENSUS:
            raise RuntimeError("predecessor family census drift")
        projected = transform(live, manifest, True)
        if observed_pins(projected) != SUCCESSOR:
            raise RuntimeError("independent forward projection mismatch")
        reversed_cohort = transform(projected, manifest, False)
        if reversed_cohort != live:
            raise RuntimeError("independent exact reverse failed")
        state = "PASS_PREDECESSOR"
        predecessor = live
        successor = projected
    elif live_pins == SUCCESSOR:
        if census(live) != expected_successor_census():
            raise RuntimeError("successor family census drift")
        reversed_cohort = transform(live, manifest, False)
        if observed_pins(reversed_cohort) != PREDECESSOR:
            raise RuntimeError("independent reverse projection mismatch")
        replay = transform(reversed_cohort, manifest, True)
        if replay != live:
            raise RuntimeError("independent successor replay failed")
        state = "PASS_SUCCESSOR"
        predecessor = reversed_cohort
        successor = live
    else:
        raise RuntimeError(f"live cohort is neither frozen state: {live_pins}")

    for filename in SOURCE_ORDER:
        if structural_signature(predecessor[filename].decode("utf-8")) != structural_signature(
            successor[filename].decode("utf-8")
        ):
            raise RuntimeError(f"protected TeX structure differs in {filename}")
    report = {
        "schema": "noether-isv-v021-cest-family-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0007",
        "status": state,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authorities": authorities,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "predecessor_census": dict(sorted(census(predecessor).items())),
            "successor_census": dict(sorted(census(successor).items())),
            "successor_target_residue": sum(
                count
                for token, count in census(successor).items()
                if token in TARGETS
            ),
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "utf8": True,
            "protected_tex_structure_equal": True,
            "source_writes": 0,
        },
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
