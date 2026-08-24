#!/usr/bin/env python3
"""Independent predecessor/successor verifier for ISV021-EDIT-0009.

This verifier imports neither the audit, applicator, nor transaction core.
"""

from __future__ import annotations

from collections import Counter
import csv
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
    ROOT / "decision_records" / "ISV021-EDIT-0009-UNAPPLIED-CANDIDATE-RECEIPT.json"
)
RECEIPT_PIN = (
    42_803,
    "93B324FA5EA72692C2029FE025DC885E2EDD1E98953B430A1BEBA98906101CE5",
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
        26_039,
        "E578FC6A58094F2B1F22BCC3CC40B9521A23F8A324FB66F84CC582583E6A9990",
    ),
    "base-papers1-43-isv.tex": (
        1_894_571,
        "66399487B71DBA6FB8FC8DE8D91FC95F415D9974D602373D9F5E5C4E1EE401B1",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
SUCCESSOR = {
    "44-book-isv.tex": (
        168_427,
        "39FC522BFABDCA4F61A08ED5654224122AC0C64299F078FB16D31A90F3662415",
    ),
    "45-isv.tex": PREDECESSOR["45-isv.tex"],
    "base-papers1-43-isv.tex": (
        1_894_613,
        "C1B9BAC6DC890F8544A8661712B0B87FFC854871BFB52792FD11FAFA82358719",
    ),
    "bib-isv.tex": (
        10_020,
        "7A45365DC7C9408CF3D50FDAA4C35081E032CC6F07D73A9954D3B1DDF18C9EC7",
    ),
}
EXPECTED_LOCATOR_BYTES = 17_301
EXPECTED_LOCATOR_SHA256 = (
    "83A94BB35B3D977455F92441FCD462CDD2B98B1DB78C0BFCAA4BF3DFF8EB5333"
)
VISIBLE_ROLES = {"visible_prose", "visible_math_text", "visible_metadata"}
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
WORD_MAP = {
    "iměnno": "imenno",
    "izsledovali": "izslědovali",
    "nekoliko": "několiko",
    "nekoje": "někoje",
    "neku": "něku",
    "posle": "poslě",
    "tesno": "těsno",
    "trebuje": "trěbuje",
    "trebujut": "trěbujut",
    "upotrebjena": "upotrěbjena",
    "upotrebjene": "upotrěbjene",
    "upotrebljen": "upotrěbljen",
    "vsěgda": "vsegda",
    "delitelj": "dělitelj",
    "jedinicnogo": "jediničnogo",
    "jedinicny": "jediničny",
    "pomocju": "pomoćju",
    "pomocnyh": "pomoćnyh",
    "pomocna": "pomoćna",
    "pomocnoj": "pomoćnoj",
    "cela": "cěla",
    "celo": "cělo",
    "celu": "cělu",
    "celyh": "cělyh",
    "celom": "cělom",
    "matricny": "matričny",
    "matricnogo": "matričnogo",
    "matricnyh": "matričnyh",
    "dopusča": "dopušća",
    "dopusća": "dopušća",
    "isčezaje": "izčezaje",
    "isčezajut": "izčezajut",
    "iščezajut": "izčezajut",
    "celkovy": "cěly",
    "celkovogo": "cělogo",
}
PHRASE_MAP = {
    "Jest celěsoobrazno": "Korisno jest",
    "Za tu cěl": "Za toj cělj",
}
EXPECTED_BEFORE = Counter(
    {
        "cela": 4,
        "celkovogo": 1,
        "celkovy": 1,
        "celo": 3,
        "celom": 1,
        "celu": 2,
        "celyh": 1,
        "delitelj": 1,
        "dopusča": 4,
        "dopusća": 1,
        "iměnno": 2,
        "isčezaje": 3,
        "isčezajut": 2,
        "iščezajut": 1,
        "izsledovali": 1,
        "jedinicnogo": 1,
        "jedinicny": 2,
        "matricnogo": 2,
        "matricny": 10,
        "matricnyh": 3,
        "nekoliko": 10,
        "nekoje": 14,
        "neku": 2,
        "pomocju": 1,
        "pomocna": 6,
        "pomocnoj": 2,
        "pomocnyh": 1,
        "posle": 2,
        "tesno": 1,
        "trebuje": 1,
        "trebujut": 1,
        "upotrebjena": 1,
        "upotrebjene": 1,
        "upotrebljen": 1,
        "vsěgda": 8,
    }
)
EXPECTED_SUCCESSOR = Counter(
    {
        "cěla": 101,
        "cělo": 82,
        "cělogo": 18,
        "cělom": 7,
        "cělu": 37,
        "cěly": 58,
        "cělyh": 152,
        "dopušća": 26,
        "dělitelj": 229,
        "imenno": 166,
        "izslědovali": 2,
        "izčezaje": 86,
        "izčezajut": 39,
        "jediničnogo": 58,
        "jediničny": 88,
        "matričnogo": 9,
        "matričny": 27,
        "matričnyh": 19,
        "někoje": 24,
        "několiko": 36,
        "něku": 3,
        "pomoćju": 26,
        "pomoćna": 42,
        "pomoćnoj": 21,
        "pomoćnyh": 9,
        "poslě": 29,
        "trěbuje": 4,
        "trěbujut": 4,
        "těsno": 3,
        "upotrěbjena": 1,
        "upotrěbjene": 4,
        "upotrěbljen": 3,
        "vsegda": 198,
    }
)
SUCCESSOR_LINE_PINS = {
    4906: (674, "37F65DBB10BDE0E5B8B481BBB762D62C27B31BFD1088572BB415D3CAE53AEDB2"),
    4910: (413, "4EDC5D40EFB45319E9ECE74E28D8B0AA208230C9D76D4A115CE79214CEA71069"),
    5130: (585, "96B3AB0E13378CB8E267E6CD4E9734FDA890E646E115FAEC12642945C78F813A"),
    11993: (133, "9161C611D2F8B9F55299CC97C3F2723BF7125B6261FB719EF64BDC85DAA451BC"),
}
AUTHORITY_IDS = {
    "100": "pomoćny",
    "421": "cělj",
    "780": "vsegda, vsegdy",
    "1027": "cěly",
    "1267": "s pomoćjų",
    "1754": "děliti",
    "1942": "trěbovati",
    "2396": "několiko",
    "2893": "tȯj",
    "3092": "upotrěbiti",
    "3550": "izčezati",
    "3894": "těsno",
    "3945": "pomoć",
    "4143": "cělkovity",
    "5174": "jedinica",
    "5696": "někoj",
    "6271": "koristny",
    "7208": "dopušćati",
    "10975": "poslě",
    "17486": "imenno",
    "20859": "dopušćati",
    "21308": "izslědovati",
    "25182": "dělba",
    "30950": "uměstno",
    "35975": "matrica",
    "37582": "uličny",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def authenticate(path: Path, expected: tuple[int, str], label: str) -> bytes:
    data = path.read_bytes()
    if (len(data), sha256(data)) != expected:
        raise RuntimeError(f"{label} pin drift")
    return data


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


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
    if not isinstance(manifest, list) or len(manifest) != 100:
        raise RuntimeError("candidate manifest cardinality drift")
    payload = canonical_bytes(manifest)
    if (len(payload), sha256(payload)) != (
        EXPECTED_LOCATOR_BYTES,
        EXPECTED_LOCATOR_SHA256,
    ):
        raise RuntimeError("candidate manifest hash drift")
    counts: Counter[str] = Counter()
    for item in manifest:
        before = item["before"]
        after = item["after"]
        if before in PHRASE_MAP:
            if after != PHRASE_MAP[before]:
                raise RuntimeError("phrase mapping drift")
            counts[before] += 1
        else:
            folded = before.casefold()
            if folded not in WORD_MAP or after.casefold() != WORD_MAP[folded]:
                raise RuntimeError("word mapping drift")
            counts[folded] += 1
        if item.get("role") not in VISIBLE_ROLES:
            raise RuntimeError("non-visible manifest role")
    expected = EXPECTED_BEFORE + Counter({key: 1 for key in PHRASE_MAP})
    if counts != expected:
        raise RuntimeError(f"candidate before census drift: {dict(counts)}")
    return manifest, {"path": str(RECEIPT_PATH), **pin(receipt_bytes)}


def shifted_for_successor(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    delta = 0
    for item in sorted(items, key=lambda value: value["byte_offset0"]):
        adjusted = dict(item)
        adjusted["byte_offset0"] = item["byte_offset0"] + delta
        result.append(adjusted)
        delta += len(item["after"].encode("utf-8")) - len(
            item["before"].encode("utf-8")
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


def census(cohort: dict[str, bytes], forms: set[str]) -> Counter[str]:
    result: Counter[str] = Counter()
    for data in cohort.values():
        for token in WORD_RE.findall(data.decode("utf-8", errors="strict")):
            folded = token.casefold()
            if folded in forms:
                result[folded] += 1
    return result


def escaped(text: str, index: int) -> bool:
    count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        count += 1
        cursor -= 1
    return bool(count % 2)


def verify_locations(predecessor: dict[str, bytes], manifest: list[dict[str, Any]]) -> None:
    for item in manifest:
        data = predecessor[item["file"]]
        text = data.decode("utf-8", errors="strict")
        lines = text.splitlines(keepends=True)
        line = lines[item["line"] - 1].rstrip("\r\n")
        column0 = item["column"] - 1
        if line[column0 : column0 + len(item["before"])] != item["before"]:
            raise RuntimeError("independent line/column locator mismatch")
        line_start = sum(
            len(value.encode("utf-8")) for value in lines[: item["line"] - 1]
        )
        offset = line_start + len(line[:column0].encode("utf-8"))
        if offset != item["byte_offset0"]:
            raise RuntimeError("independent byte locator mismatch")
        for match in re.finditer("%", line):
            if match.start() < column0 and not escaped(line, match.start()):
                raise RuntimeError("target follows a TeX comment")
        prefix = line[:column0]
        dollars = sum(
            1 for match in re.finditer(r"\$", prefix) if not escaped(prefix, match.start())
        )
        if dollars % 2:
            raise RuntimeError("target lies inside inline math")


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    environments = re.findall(r"\\(?:begin|end)\{[^{}]+\}", text)
    labels = re.findall(r"\\(?:label|ref|eqref)\{[^{}]*\}", text)
    math_delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "lines": text.count("\n") + 1,
        "braces": (text.count("{"), text.count("}")),
        "percent": text.count("%"),
        "commands": (len(commands), sha256("\n".join(commands).encode("utf-8"))),
        "environments": (
            len(environments),
            sha256("\n".join(environments).encode("utf-8")),
        ),
        "labels": (len(labels), sha256("\n".join(labels).encode("utf-8"))),
        "math": (
            len(math_delimiters),
            sha256("\n".join(math_delimiters).encode("utf-8")),
        ),
    }


def verify_authorities(predecessor: dict[str, bytes]) -> dict[str, Any]:
    dictionary = authenticate(DICTIONARY_PATH, DICTIONARY_PIN, "dictionary")
    found: dict[str, str] = {}
    with DICTIONARY_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in AUTHORITY_IDS:
                found[row["id"]] = row["isv"]
    if found != AUTHORITY_IDS:
        raise RuntimeError("official authority row drift")
    lines = predecessor["base-papers1-43-isv.tex"].decode("utf-8").splitlines()
    controls = {
        126: "cěly ręd form",
        547: "cělogo ręda form",
        553: "cěly ręd form",
        1082: "cěly ręd form",
        4906: "Korisno jest mysliti",
        4912: "cěly ręd form",
        15623: "Za toj dokaz",
    }
    for line_number, needle in controls.items():
        if needle not in lines[line_number - 1]:
            raise RuntimeError(f"local authority drift at line {line_number}")
    return {
        "official_dictionary": {"path": str(DICTIONARY_PATH), **pin(dictionary)},
        "official_rows": AUTHORITY_IDS,
        "local_control_lines": sorted(controls),
    }


def main() -> int:
    manifest, receipt = load_manifest()
    live = read_cohort()
    live_pins = observed_pins(live)
    if live_pins == PREDECESSOR:
        predecessor = live
        successor = transform(live, manifest, True)
        if observed_pins(successor) != SUCCESSOR:
            raise RuntimeError("independent forward projection mismatch")
        if transform(successor, manifest, False) != predecessor:
            raise RuntimeError("independent exact reverse failed")
        status = "PASS_PREDECESSOR"
    elif live_pins == SUCCESSOR:
        successor = live
        predecessor = transform(live, manifest, False)
        if observed_pins(predecessor) != PREDECESSOR:
            raise RuntimeError("independent reverse projection mismatch")
        if transform(predecessor, manifest, True) != successor:
            raise RuntimeError("independent successor replay failed")
        status = "PASS_SUCCESSOR"
    else:
        raise RuntimeError(f"live cohort is neither frozen state: {live_pins}")

    old_census = census(predecessor, set(WORD_MAP))
    if old_census != EXPECTED_BEFORE:
        raise RuntimeError(f"predecessor target census drift: {dict(old_census)}")
    if census(successor, set(WORD_MAP)):
        raise RuntimeError("successor old-word residue")
    new_census = census(successor, set(WORD_MAP.values()))
    if new_census != EXPECTED_SUCCESSOR:
        raise RuntimeError(f"successor relevant census drift: {dict(new_census)}")
    pre_texts = [data.decode("utf-8") for data in predecessor.values()]
    post_texts = [data.decode("utf-8") for data in successor.values()]
    for old, new in PHRASE_MAP.items():
        if sum(text.count(old) for text in pre_texts) != 1:
            raise RuntimeError("predecessor phrase census drift")
        if sum(text.count(old) for text in post_texts) != 0:
            raise RuntimeError("successor old-phrase residue")
        expected_new = 2 if new == "Korisno jest" else 1
        if sum(text.count(new) for text in post_texts) != expected_new:
            raise RuntimeError("successor new-phrase census drift")
    verify_locations(predecessor, manifest)
    authorities = verify_authorities(predecessor)
    for filename in SOURCE_ORDER:
        if structural_signature(predecessor[filename].decode("utf-8")) != structural_signature(
            successor[filename].decode("utf-8")
        ):
            raise RuntimeError(f"protected TeX structure differs in {filename}")
    base_lines = successor["base-papers1-43-isv.tex"].decode("utf-8").splitlines()
    for line_number, expected in SUCCESSOR_LINE_PINS.items():
        data = base_lines[line_number - 1].encode("utf-8")
        if (len(data), sha256(data)) != expected:
            raise RuntimeError(f"successor lexical line drift at {line_number}")

    report = {
        "schema": "noether-isv-v021-residual-reader-consistency-independent-verification-v1",
        "edit_id": "ISV021-EDIT-0009",
        "status": status,
        "live_sources": {name: pin(live[name]) for name in SOURCE_ORDER},
        "candidate_receipt": receipt,
        "authorities": authorities,
        "coverage": {
            "sites": len(manifest),
            "physical_lines": len({(item["file"], item["line"]) for item in manifest}),
            "predecessor_target_census": dict(sorted(old_census.items())),
            "successor_relevant_census": dict(sorted(new_census.items())),
            "successor_target_residue": 0,
            "successor_lexical_line_pins": SUCCESSOR_LINE_PINS,
        },
        "validation": {
            "independent_forward": True,
            "independent_reverse": True,
            "exact_byte_replay": True,
            "line_column_byte_locators": True,
            "visible_roles_and_comment_math_boundaries": True,
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
