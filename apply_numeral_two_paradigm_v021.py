#!/usr/bin/env python3
"""Audit and atomically apply ISV021-EDIT-0001.

The edit closes a bounded inherited numeral-two paradigm family.  The default
mode is read-only.  ``--apply`` is accepted only at the exact v020 Latin source
cohort and installs the two changed successors transactionally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
EDIT_ID = "ISV021-EDIT-0001"

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)

PREDECESSOR = {
    "44-book-isv.tex": (168422, "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F"),
    "45-isv.tex": (26053, "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91"),
    "base-papers1-43-isv.tex": (1894721, "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A"),
    "bib-isv.tex": (10019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}

SUCCESSOR = {
    "44-book-isv.tex": (168422, "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F"),
    "45-isv.tex": (26053, "A52ADE5B028E40677D7C689C5C6E63C9FE7102F543B8BF7FFFCB0E19576A44CF"),
    "base-papers1-43-isv.tex": (1894703, "041FFBA15D5333962D9E1B2DE6925E1372446F5996F3DC2AA57A67F9B9113AA9"),
    "bib-isv.tex": (10019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}

SOURCE_FORMS = ("dvuh", "dveh", "dvěh", "dvaju", "dvěma", "dvije")
SOURCE_COUNTS = {"dvuh": 64, "dveh": 13, "dvěh": 1, "dvaju": 3, "dvěma": 8, "dvije": 5}
TARGET_COUNTS_BEFORE = {"dvoh": 116, "dvom": 2, "dvoma": 17, "dvě": 69}
TARGET_COUNTS_AFTER = {"dvoh": 197, "dvom": 3, "dvoma": 24, "dvě": 74}
CASE_INSENSITIVE_DVE_BEFORE = 76
CASE_INSENSITIVE_DVE_AFTER = 81
HOLD_COUNTS = {"obadvuh": 1, "dvoju": 1, "dvojim": 1}
EXPECTED_SITES_BY_FILE = {"44-book-isv.tex": 0, "45-isv.tex": 5, "base-papers1-43-isv.tex": 89, "bib-isv.tex": 0}

# Filled after an independent locator enumeration; canonical JSON is UTF-8,
# ensure_ascii=False, sort_keys=True, separators=(",", ":").
EXPECTED_LOCATOR_SHA256 = "1079B25C7B758FBC19D1CDDA7415B709904FB3AAD24F8BC34EA171B32E9449D2"

TOKEN_RE = re.compile(r"\b(?:dvuh|dveh|dvěh|dvaju|dvěma|dvije)\b", re.UNICODE)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def whole_count(text: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", text, flags=re.UNICODE))


def whole_count_casefold(text: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", text, flags=re.UNICODE | re.IGNORECASE))


def replacement_for(filename: str, line: int, column: int, source: str) -> str:
    if source in {"dvuh", "dveh", "dvěh", "dvaju"}:
        return "dvoh"
    if source == "dvije":
        return "dvě"
    if source == "dvěma":
        if filename == "base-papers1-43-isv.tex" and line == 19457 and column == 56:
            return "dvom"
        return "dvoma"
    raise AssertionError(source)


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return bool(backslashes % 2)


def assert_visible_text(line_text: str, column0: int, filename: str, line_no: int) -> None:
    for match in re.finditer("%", line_text):
        if match.start() < column0 and not is_escaped(line_text, match.start()):
            raise RuntimeError(f"target after TeX comment at {filename}:{line_no}:{column0 + 1}")
    unescaped_dollars = sum(1 for m in re.finditer(r"\$", line_text[:column0]) if not is_escaped(line_text, m.start()))
    if unescaped_dollars % 2:
        raise RuntimeError(f"target inside inline math at {filename}:{line_no}:{column0 + 1}")


def structural_signature(text: str) -> dict[str, Any]:
    commands = re.findall(r"\\(?:[A-Za-z@]+|.)", text)
    math_delimiters = re.findall(r"(?<!\\)(?:\$\$|\$)|\\\[|\\\]|\\\(|\\\)", text)
    return {
        "line_count": text.count("\n") + 1,
        "open_braces": text.count("{"),
        "close_braces": text.count("}"),
        "commands_sha256": sha256("\n".join(commands).encode("utf-8")),
        "commands_count": len(commands),
        "math_delimiters_sha256": sha256("\n".join(math_delimiters).encode("utf-8")),
        "math_delimiters_count": len(math_delimiters),
    }


def transform(filename: str, data: bytes) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    text = data.decode("utf-8", errors="strict")
    pieces: list[str] = []
    locators: list[dict[str, Any]] = []
    reverse_spans: list[tuple[int, int, str, str]] = []
    output_cursor = 0

    for line_no, line_text in enumerate(text.splitlines(keepends=True), start=1):
        cursor = 0
        for match in TOKEN_RE.finditer(line_text):
            column = match.start() + 1
            source = match.group(0)
            target = replacement_for(filename, line_no, column, source)
            assert_visible_text(line_text, match.start(), filename, line_no)
            pieces.append(line_text[cursor:match.start()])
            output_cursor += len(line_text[cursor:match.start()])
            out_start = output_cursor
            pieces.append(target)
            output_cursor += len(target)
            reverse_spans.append((out_start, output_cursor, source, target))
            locators.append({
                "file": filename,
                "line": line_no,
                "column": column,
                "before": source,
                "after": target,
            })
            cursor = match.end()
        pieces.append(line_text[cursor:])
        output_cursor += len(line_text[cursor:])

    output_text = "".join(pieces)
    output = output_text.encode("utf-8")

    # Exact in-memory reverse replay at the transformed spans.
    reversed_pieces: list[str] = []
    cursor = 0
    for start, end, source, target in reverse_spans:
        if output_text[start:end] != target:
            raise RuntimeError(f"reverse span drift in {filename}")
        reversed_pieces.append(output_text[cursor:start])
        reversed_pieces.append(source)
        cursor = end
    reversed_pieces.append(output_text[cursor:])
    if "".join(reversed_pieces).encode("utf-8") != data:
        raise RuntimeError(f"reverse replay failed in {filename}")

    before_structure = structural_signature(text)
    after_structure = structural_signature(output_text)
    if before_structure != after_structure:
        raise RuntimeError(f"TeX structure changed in {filename}")

    return output, locators, {
        "reverse_replay_exact": True,
        "structural_signature": before_structure,
    }


def read_cohort() -> dict[str, bytes]:
    return {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}


def cohort_state(cohort: dict[str, bytes]) -> str:
    observed = {name: (len(data), sha256(data)) for name, data in cohort.items()}
    if observed == PREDECESSOR:
        return "predecessor"
    if observed == SUCCESSOR:
        return "successor"
    details = {name: {"bytes": value[0], "sha256": value[1]} for name, value in observed.items()}
    raise RuntimeError("source cohort is neither the frozen predecessor nor successor: " + json.dumps(details, sort_keys=True))


def token_counts(cohort: dict[str, bytes], tokens: tuple[str, ...] | list[str]) -> dict[str, int]:
    combined = "\n".join(cohort[name].decode("utf-8", errors="strict") for name in SOURCE_ORDER)
    return {token: whole_count(combined, token) for token in tokens}


def audit_predecessor(cohort: dict[str, bytes]) -> tuple[dict[str, bytes], dict[str, Any]]:
    outputs: dict[str, bytes] = {}
    locators: list[dict[str, Any]] = []
    per_file: dict[str, Any] = {}
    for name in SOURCE_ORDER:
        output, local_locators, safeguards = transform(name, cohort[name])
        outputs[name] = output
        locators.extend(local_locators)
        per_file[name] = {
            "input": pin(cohort[name]),
            "output": pin(output),
            "sites": len(local_locators),
            "safeguards": safeguards,
        }
        if (len(output), sha256(output)) != SUCCESSOR[name]:
            raise RuntimeError(f"projected successor pin mismatch for {name}")
        if len(local_locators) != EXPECTED_SITES_BY_FILE[name]:
            raise RuntimeError(f"site count mismatch for {name}")

    source_counts = Counter(item["before"] for item in locators)
    if dict(source_counts) != SOURCE_COUNTS:
        raise RuntimeError(f"source-form count mismatch: {dict(source_counts)}")
    locator_sha = sha256(canonical_bytes(locators))
    if EXPECTED_LOCATOR_SHA256 != "TO_BE_FROZEN" and locator_sha != EXPECTED_LOCATOR_SHA256:
        raise RuntimeError(f"locator manifest mismatch: {locator_sha}")
    if token_counts(cohort, list(TARGET_COUNTS_BEFORE)) != TARGET_COUNTS_BEFORE:
        raise RuntimeError("predecessor target control counts drifted")
    if token_counts(outputs, list(TARGET_COUNTS_AFTER)) != TARGET_COUNTS_AFTER:
        raise RuntimeError("successor target control counts drifted")
    predecessor_combined = "\n".join(cohort[name].decode("utf-8", errors="strict") for name in SOURCE_ORDER)
    successor_combined = "\n".join(outputs[name].decode("utf-8", errors="strict") for name in SOURCE_ORDER)
    if whole_count_casefold(predecessor_combined, "dvě") != CASE_INSENSITIVE_DVE_BEFORE:
        raise RuntimeError("predecessor case-insensitive dvě control count drifted")
    if whole_count_casefold(successor_combined, "dvě") != CASE_INSENSITIVE_DVE_AFTER:
        raise RuntimeError("successor case-insensitive dvě control count drifted")
    if token_counts(outputs, list(SOURCE_FORMS)) != {token: 0 for token in SOURCE_FORMS}:
        raise RuntimeError("source-form residue remains")
    if token_counts(cohort, list(HOLD_COUNTS)) != HOLD_COUNTS or token_counts(outputs, list(HOLD_COUNTS)) != HOLD_COUNTS:
        raise RuntimeError("explicit hold inventory drifted")

    report = {
        "schema": "noether-isv-v021-numeral-two-paradigm-candidate-v1",
        "edit_id": EDIT_ID,
        "recorded_at": "2026-08-22T18:23:34+02:00",
        "status": "UNAPPLIED_HASH_GATED_CANDIDATE_ACCEPTED_FOR_APPLICATION",
        "predecessor_release": {
            "local_root": str(ROOT.parent / "noether_isv_v020_working"),
            "zenodo_version_doi": "10.5281/zenodo.22058530",
            "latin_head": "ISV019-EDIT-0171",
        },
        "scope": {
            "sites": len(locators),
            "physical_lines": len({(item["file"], item["line"]) for item in locators}),
            "mapping": {
                "genitive_or_locative": {"dvuh|dveh|dvěh|dvaju": "dvoh", "sites": 81},
                "instrumental": {"dvěma": "dvoma", "sites": 7},
                "dative": {"dvěma": "dvom", "sites": 1, "locator": "base-papers1-43-isv.tex:19457:56"},
                "feminine_nominative_or_accusative": {"dvije": "dvě", "sites": 5},
            },
            "sites_by_file": EXPECTED_SITES_BY_FILE,
        },
        "authority": {
            "official_grammar_snapshot": {
                "archive": "01_methodology/claude_fable_program/data/interslavic_dictionary_official_snapshot_20260816/upstream_repository_0fab0c5b4463118d46b1cdcd506926d8848052c9.zip",
                "archive_bytes": 11271766,
                "archive_sha256": "E02AA89235E4A7B536F3D762126293A3E348319CA1B11CBF8D219A65D03172BE",
                "member": "interslavic-0fab0c5b4463118d46b1cdcd506926d8848052c9/src/components/Pages/Grammar/Grammar.tsx",
                "member_bytes": 19048,
                "member_sha256": "BDDB61D02CFA93876485271012014CAF5D6855C93D7489CB0511F842A4211C60",
                "lines": "218-222: dva, dvoh, dvom, dvoma",
            },
            "official_table_snapshot": "tables.json lines 1473-1488: tableNumbers row 2 gives dva/dvě/dvě",
            "current_official_page": "https://interslavic.fun/learn/grammar/numerals/",
            "prior_ledger": "ISV019-EDIT-0112 already establishes official inflected-cardinal closure; ISV019-EDIT-0059 mentions dvaju only as a nonverb guard, not a morphology acceptance",
        },
        "independent_review": {
            "agent_task": "/root/isv021_residual_audit",
            "disposition": "ACCEPT_WITH_ONE_CASE_REFINEMENT",
            "finding": "All 94 contexts inspected; 81 genitive/locative, 7 instrumental, 1 dative, 5 feminine nominative/accusative; all editable prose and none protected",
            "independent_locator_serialization": {
                "format": "filename<TAB>line<TAB>column<TAB>old<TAB>new<LF>; file order base/44/45/bib and scan order within file",
                "bytes": 4007,
                "sha256": "F9FC43567A4E71E456E7F563F48B89A09152ADDF48B09D117DB5998381585C93",
            },
        },
        "locators": locators,
        "locator_manifest": {"canonical_bytes": len(canonical_bytes(locators)), "sha256": locator_sha},
        "sources": per_file,
        "counts": {
            "source_before": SOURCE_COUNTS,
            "source_after": {token: 0 for token in SOURCE_FORMS},
            "targets_before": TARGET_COUNTS_BEFORE,
            "targets_after": TARGET_COUNTS_AFTER,
            "case_insensitive_dvě_before_after": [CASE_INSENSITIVE_DVE_BEFORE, CASE_INSENSITIVE_DVE_AFTER],
        },
        "holds": {
            "counts_unchanged": HOLD_COUNTS,
            "reason": "Compound/collective forms require separate exact paradigm evidence and are outside this edit.",
        },
        "validation": {
            "strict_utf8": True,
            "comments_rejected": True,
            "inline_math_rejected": True,
            "whole_token_only": True,
            "exact_reverse_replay": True,
            "tex_command_math_delimiter_brace_and_line_signatures_unchanged": True,
            "unresolved_items_inside_scope": 0,
        },
        "tool": {
            "path": Path(__file__).name,
            "bytes": Path(__file__).stat().st_size,
            "sha256": sha256(Path(__file__).read_bytes()),
        },
        "claims": {"applied": False, "build": False, "render": False, "git": False, "network": False, "publication": False},
    }
    return outputs, report


def write_exclusive(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def apply_transaction(cohort: dict[str, bytes], outputs: dict[str, bytes]) -> None:
    changed = [name for name in SOURCE_ORDER if cohort[name] != outputs[name]]
    lock = ROOT / f".{EDIT_ID}.lock"
    stages = {name: SOURCE_DIR / f".{EDIT_ID}.{name}.stage" for name in changed}
    rollbacks = {name: SOURCE_DIR / f".{EDIT_ID}.{name}.rollback" for name in changed}
    for residue in [lock, *stages.values(), *rollbacks.values()]:
        if residue.exists():
            raise RuntimeError(f"transaction residue exists: {residue}")

    write_exclusive(lock, canonical_bytes({"edit_id": EDIT_ID, "pid": os.getpid()}))
    installed: list[str] = []
    coherent = False
    try:
        if cohort_state(read_cohort()) != "predecessor":
            raise RuntimeError("source drift after lock acquisition")
        for name in changed:
            write_exclusive(rollbacks[name], cohort[name])
            write_exclusive(stages[name], outputs[name])
            if pin(rollbacks[name].read_bytes()) != pin(cohort[name]):
                raise RuntimeError(f"rollback verification failed for {name}")
            if pin(stages[name].read_bytes()) != pin(outputs[name]):
                raise RuntimeError(f"stage verification failed for {name}")
        if cohort_state(read_cohort()) != "predecessor":
            raise RuntimeError("source drift before install")
        for name in changed:
            os.replace(stages[name], SOURCE_DIR / name)
            installed.append(name)
        if cohort_state(read_cohort()) != "successor":
            raise RuntimeError("post-install cohort audit failed")
        coherent = True
        for name in changed:
            rollbacks[name].unlink()
    except Exception:
        restoration_safe = True
        for name in reversed(installed):
            target = SOURCE_DIR / name
            rollback = rollbacks[name]
            if not rollback.exists() or (len(rollback.read_bytes()), sha256(rollback.read_bytes())) != PREDECESSOR[name]:
                restoration_safe = False
                continue
            current = target.read_bytes()
            if (len(current), sha256(current)) != SUCCESSOR[name]:
                restoration_safe = False
                continue
            os.replace(rollback, target)
        if restoration_safe and cohort_state(read_cohort()) == "predecessor":
            for path in [*stages.values(), *rollbacks.values()]:
                if path.exists():
                    path.unlink()
        else:
            raise RuntimeError("transaction failed and uncertain evidence was preserved; lock retained")
        raise
    finally:
        if coherent or (lock.exists() and cohort_state(read_cohort()) == "predecessor"):
            try:
                lock.unlink()
            except FileNotFoundError:
                pass


def write_receipt(path: Path, report: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite receipt: {path}")
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    write_exclusive(path, payload)


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    source_counts = token_counts(cohort, list(SOURCE_FORMS))
    target_counts = token_counts(cohort, list(TARGET_COUNTS_AFTER))
    hold_counts = token_counts(cohort, list(HOLD_COUNTS))
    if source_counts != {token: 0 for token in SOURCE_FORMS}:
        raise RuntimeError("applied cohort has source residue")
    if target_counts != TARGET_COUNTS_AFTER or hold_counts != HOLD_COUNTS:
        raise RuntimeError("applied cohort count audit failed")
    combined = "\n".join(cohort[name].decode("utf-8", errors="strict") for name in SOURCE_ORDER)
    if whole_count_casefold(combined, "dvě") != CASE_INSENSITIVE_DVE_AFTER:
        raise RuntimeError("applied cohort case-insensitive dvě count audit failed")
    return {
        "schema": "noether-isv-v021-numeral-two-paradigm-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "counts": {"source_forms": source_counts, "targets": target_counts, "holds": hold_counts},
        "claims": {"applied": True, "build": False, "render": False, "git": False, "network": False, "publication": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="atomically install the frozen successor")
    parser.add_argument("--write-receipt", type=Path, help="write the current audit receipt without overwrite")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    cohort = read_cohort()
    state = cohort_state(cohort)
    if state == "predecessor":
        outputs, report = audit_predecessor(cohort)
        if args.apply:
            if EXPECTED_LOCATOR_SHA256 == "TO_BE_FROZEN":
                raise RuntimeError("locator manifest is not frozen; refusing apply")
            apply_transaction(cohort, outputs)
            report = successor_report(read_cohort())
    else:
        if args.apply:
            raise RuntimeError("edit is already applied")
        report = successor_report(cohort)

    if args.write_receipt:
        write_receipt(args.write_receipt.resolve(), report)
    if args.compact:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
