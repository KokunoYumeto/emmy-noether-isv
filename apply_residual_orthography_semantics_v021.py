#!/usr/bin/env python3
"""Audit and transactionally apply ISV021-EDIT-0002.

This edit closes five independently bounded residual families across the four
Latin Interslavic sources.  The default mode is read-only.  ``--apply`` is
enabled only after the locator manifest and every successor file pin have been
frozen in this file.
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
EDIT_ID = "ISV021-EDIT-0002"

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

SUCCESSOR: dict[str, tuple[int, str] | None] = {
    "44-book-isv.tex": (168422, "1B7432A5D2D8BF31D286CCDE43D6935BE3619C06D6C3582B60BF680591625A68"),
    "45-isv.tex": (26038, "636E873287E0127A58DCBF014CB3C0343EF9D4545D90C2A6475E9F1E5F8B8ADD"),
    "base-papers1-43-isv.tex": (1894577, "EACFE1473BBF5D82A4B07309C33787A198FE9B111F2228323D4A6076578D389E"),
    "bib-isv.tex": (10019, "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553"),
}

EXPECTED_FAMILY_COUNTS = {
    "pomoč_to_pomoć": 96,
    "celost_to_cělost": 5,
    "imenujuče_to_imenno": 4,
    "vrědnost_noun_to_cěnnost": 125,
    "cěločislovn_to_cěločislov": 5,
}
EXPECTED_SITES_BY_FILE = {
    "44-book-isv.tex": 1,
    "45-isv.tex": 20,
    "base-papers1-43-isv.tex": 214,
    "bib-isv.tex": 0,
}
EXPECTED_LOCATOR_SHA256 = "979566CAC52BD2005F4141681500C7FB364F92AE9686072C520C22AB03A4EF97"

HOLD_PATTERNS = {
    "vrědnostny": re.compile(r"\bvrědnostny\b", re.UNICODE),
    "bare_čislovno": re.compile(r"\bčislovno\b", re.UNICODE),
}
EXPECTED_HOLD_COUNTS = {"vrědnostny": 1, "bare_čislovno": 1}

TOKEN_RE = re.compile(
    r"\b(?:"
    r"(?:pomoč|Pomoč)\w*"
    r"|celost(?:i)?"
    r"|imenujuče"
    r"|(?:vrědnost|Vrědnost)(?!ny\b)\w*"
    r"|cěločislovn\w*"
    r")\b",
    re.UNICODE,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pin(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def replacement(token: str) -> tuple[str, str]:
    if token.startswith("pomoč"):
        return "pomoč_to_pomoć", "pomoć" + token[len("pomoč") :]
    if token.startswith("Pomoč"):
        return "pomoč_to_pomoć", "Pomoć" + token[len("Pomoč") :]
    if token == "celost":
        return "celost_to_cělost", "cělost"
    if token == "celosti":
        return "celost_to_cělost", "cělosti"
    if token == "imenujuče":
        return "imenujuče_to_imenno", "imenno"
    if token.startswith("vrědnost"):
        return "vrědnost_noun_to_cěnnost", "cěnnost" + token[len("vrědnost") :]
    if token.startswith("Vrědnost"):
        return "vrědnost_noun_to_cěnnost", "Cěnnost" + token[len("Vrědnost") :]
    if token.startswith("cěločislovn"):
        return "cěločislovn_to_cěločislov", "cěločislov" + token[len("cěločislovn") :]
    raise RuntimeError(f"unclassified token: {token!r}")


def is_escaped(text: str, index: int) -> bool:
    count = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        count += 1
        cursor -= 1
    return bool(count % 2)


def assert_visible_text(line_text: str, column0: int, filename: str, line_no: int) -> None:
    for match in re.finditer("%", line_text):
        if match.start() < column0 and not is_escaped(line_text, match.start()):
            raise RuntimeError(
                f"target after TeX comment at {filename}:{line_no}:{column0 + 1}"
            )
    prefix = line_text[:column0]
    dollar_count = sum(
        1 for match in re.finditer(r"\$", prefix) if not is_escaped(prefix, match.start())
    )
    if dollar_count % 2:
        raise RuntimeError(
            f"target inside inline math at {filename}:{line_no}:{column0 + 1}"
        )


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
        "math_delimiters_sha256": sha256("\n".join(math_delimiters).encode("utf-8")),
    }


def transform(
    filename: str, data: bytes
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    text = data.decode("utf-8", errors="strict")
    pieces: list[str] = []
    locators: list[dict[str, Any]] = []
    reverse_spans: list[tuple[int, int, str, str]] = []
    output_cursor = 0

    for line_no, line_text in enumerate(text.splitlines(keepends=True), start=1):
        cursor = 0
        for match in TOKEN_RE.finditer(line_text):
            before = match.group(0)
            family, after = replacement(before)
            assert_visible_text(line_text, match.start(), filename, line_no)
            pieces.append(line_text[cursor : match.start()])
            output_cursor += len(line_text[cursor : match.start()])
            start = output_cursor
            pieces.append(after)
            output_cursor += len(after)
            reverse_spans.append((start, output_cursor, before, after))
            locators.append(
                {
                    "file": filename,
                    "line": line_no,
                    "column": match.start() + 1,
                    "family": family,
                    "before": before,
                    "after": after,
                }
            )
            cursor = match.end()
        pieces.append(line_text[cursor:])
        output_cursor += len(line_text[cursor:])

    output_text = "".join(pieces)
    output = output_text.encode("utf-8")

    reversed_pieces: list[str] = []
    cursor = 0
    for start, end, before, after in reverse_spans:
        if output_text[start:end] != after:
            raise RuntimeError(f"reverse span drift in {filename}")
        reversed_pieces.append(output_text[cursor:start])
        reversed_pieces.append(before)
        cursor = end
    reversed_pieces.append(output_text[cursor:])
    if "".join(reversed_pieces).encode("utf-8") != data:
        raise RuntimeError(f"exact reverse replay failed in {filename}")

    before_structure = structural_signature(text)
    after_structure = structural_signature(output_text)
    if before_structure != after_structure:
        raise RuntimeError(f"TeX structural signature changed in {filename}")

    return output, locators, {
        "reverse_replay_exact": True,
        "structural_signature": before_structure,
    }


def read_cohort() -> dict[str, bytes]:
    return {name: (SOURCE_DIR / name).read_bytes() for name in SOURCE_ORDER}


def observed_pins(cohort: dict[str, bytes]) -> dict[str, tuple[int, str]]:
    return {name: (len(data), sha256(data)) for name, data in cohort.items()}


def successors_frozen() -> bool:
    return all(SUCCESSOR[name] is not None for name in SOURCE_ORDER)


def cohort_state(cohort: dict[str, bytes]) -> str:
    observed = observed_pins(cohort)
    if observed == PREDECESSOR:
        return "predecessor"
    if successors_frozen() and observed == SUCCESSOR:
        return "successor"
    details = {
        name: {"bytes": value[0], "sha256": value[1]}
        for name, value in observed.items()
    }
    raise RuntimeError(
        "source cohort is neither the frozen predecessor nor successor: "
        + json.dumps(details, sort_keys=True)
    )


def combined_text(cohort: dict[str, bytes]) -> str:
    return "\n".join(
        cohort[name].decode("utf-8", errors="strict") for name in SOURCE_ORDER
    )


def hold_counts(cohort: dict[str, bytes]) -> dict[str, int]:
    text = combined_text(cohort)
    return {name: len(pattern.findall(text)) for name, pattern in HOLD_PATTERNS.items()}


def root_counts(text: str) -> dict[str, int]:
    return {
        "pomoč": len(re.findall(r"\b(?:pomoč|Pomoč)\w*\b", text, re.UNICODE)),
        "pomoć": len(re.findall(r"\b(?:pomoć|Pomoć)\w*\b", text, re.UNICODE)),
        "celost": len(re.findall(r"\bcelost(?:i)?\b", text, re.UNICODE)),
        "cělost": len(re.findall(r"\bcělost\w*\b", text, re.UNICODE)),
        "imenujuče": len(re.findall(r"\bimenujuče\b", text, re.UNICODE)),
        "imenno": len(re.findall(r"\b(?:imenno|Imenno)\b", text, re.UNICODE)),
        "vrědnost_noun": len(
            re.findall(r"\b(?:vrědnost|Vrědnost)(?!ny\b)\w*\b", text, re.UNICODE)
        ),
        "cěnnost": len(re.findall(r"\b(?:cěnnost|Cěnnost)\w*\b", text, re.UNICODE)),
        "cěločislovn": len(re.findall(r"\bcěločislovn\w*\b", text, re.UNICODE)),
        "cěločislov": len(re.findall(r"\bcěločislov(?!n)\w*\b", text, re.UNICODE)),
    }


def audit_predecessor(
    cohort: dict[str, bytes]
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if observed_pins(cohort) != PREDECESSOR:
        raise RuntimeError("predecessor pins drifted")
    if hold_counts(cohort) != EXPECTED_HOLD_COUNTS:
        raise RuntimeError(f"hold inventory drifted: {hold_counts(cohort)}")

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
        if len(local_locators) != EXPECTED_SITES_BY_FILE[name]:
            raise RuntimeError(
                f"site count mismatch for {name}: {len(local_locators)}"
            )
        if successors_frozen() and (len(output), sha256(output)) != SUCCESSOR[name]:
            raise RuntimeError(f"projected successor pin mismatch for {name}")

    family_counts = Counter(item["family"] for item in locators)
    if dict(family_counts) != EXPECTED_FAMILY_COUNTS:
        raise RuntimeError(f"family count mismatch: {dict(family_counts)}")
    locator_payload = canonical_bytes(locators)
    locator_sha = sha256(locator_payload)
    if (
        EXPECTED_LOCATOR_SHA256 != "TO_BE_FROZEN"
        and locator_sha != EXPECTED_LOCATOR_SHA256
    ):
        raise RuntimeError(f"locator manifest mismatch: {locator_sha}")
    if hold_counts(outputs) != EXPECTED_HOLD_COUNTS:
        raise RuntimeError("explicit holds changed")

    before_roots = root_counts(combined_text(cohort))
    after_roots = root_counts(combined_text(outputs))
    for key in ("pomoč", "celost", "imenujuče", "vrědnost_noun", "cěločislovn"):
        if after_roots[key] != 0:
            raise RuntimeError(f"source-family residue remains for {key}")

    report = {
        "schema": "noether-isv-v021-residual-orthography-semantics-candidate-v1",
        "edit_id": EDIT_ID,
        "recorded_at": "2026-08-22T19:35:00+02:00",
        "status": (
            "FROZEN_UNAPPLIED_HASH_GATED_CANDIDATE"
            if successors_frozen() and EXPECTED_LOCATOR_SHA256 != "TO_BE_FROZEN"
            else "PROJECTION_FOR_PIN_FREEZE_APPLY_DISABLED"
        ),
        "scope": {
            "sites": len(locators),
            "physical_lines": len({(x["file"], x["line"]) for x in locators}),
            "families": dict(family_counts),
            "sites_by_file": EXPECTED_SITES_BY_FILE,
        },
        "authority_and_house_policy": {
            "official_snapshot": {
                "path": "01_methodology/claude_fable_program/data/interslavic_dictionary_official_snapshot_20260816/source_sheet_basic.csv",
                "rows": {
                    "pomoć": "CSV physical line 11615 / dictionary id 3945",
                    "pomoćny": "CSV physical line 11618 / dictionary id 100",
                    "imenno": "CSV physical line 4155 / dictionary id 17486",
                    "cěnnosť": "CSV physical line 1486 / dictionary id 2281",
                    "cělosť": "CSV physical line 1478 / dictionary id 19667",
                },
            },
            "surface_policy": "The edition consistently writes productive -ost noun surfaces without final soft-sign diacritics, hence house cělost/cěnnost while retaining the official roots and meanings.",
            "semantic_boundary": "Only noun vrědnost- in value contexts is changed; adjective vrědnostny is held. Only the five attested cěločislovn- compounds are regularized; unrelated bare čislovno is held.",
        },
        "independent_audit_reconstruction": {
            "disposition": "ACCEPT_EXACT_FIVE_FAMILY_TRANCHE",
            "adverse_evidence": "No claim of native/community certification; current official dictionary headwords and established edition-wide controls are editorial evidence, not a comprehension study.",
        },
        "locators": locators,
        "locator_manifest": {
            "canonical_bytes": len(locator_payload),
            "sha256": locator_sha,
        },
        "sources": per_file,
        "root_counts_before": before_roots,
        "root_counts_after": after_roots,
        "holds": {
            "counts_unchanged": EXPECTED_HOLD_COUNTS,
            "reason": "Different morphology or semantics; excluded from this exact transform.",
        },
        "validation": {
            "strict_utf8": True,
            "targets_after_comments_or_inside_inline_math_rejected": True,
            "exact_reverse_replay": True,
            "tex_command_environment_label_math_brace_line_signatures_unchanged": True,
            "source_residue": 0,
        },
        "tool": {
            "path": Path(__file__).name,
            "bytes": Path(__file__).stat().st_size,
            "sha256": sha256(Path(__file__).read_bytes()),
        },
        "claims": {
            "applied": False,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
        },
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


def identity(path: Path) -> tuple[int, int, int, int]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def assert_owned(
    path: Path,
    expected_identity: tuple[int, int, int, int],
    expected_pin: dict[str, Any],
    role: str,
) -> None:
    if not path.exists():
        raise RuntimeError(f"owned {role} disappeared: {path}")
    if identity(path) != expected_identity:
        raise RuntimeError(f"owned {role} identity drifted: {path}")
    if pin(path.read_bytes()) != expected_pin:
        raise RuntimeError(f"owned {role} payload drifted: {path}")


def apply_transaction(cohort: dict[str, bytes], outputs: dict[str, bytes]) -> None:
    if not successors_frozen() or EXPECTED_LOCATOR_SHA256 == "TO_BE_FROZEN":
        raise RuntimeError("successor pins or locator manifest are not frozen")
    changed = [name for name in SOURCE_ORDER if cohort[name] != outputs[name]]
    lock = ROOT / f".{EDIT_ID}.lock"
    stages = {name: SOURCE_DIR / f".{EDIT_ID}.{name}.stage" for name in changed}
    rollbacks = {
        name: SOURCE_DIR / f".{EDIT_ID}.{name}.rollback" for name in changed
    }
    for residue in [lock, *stages.values(), *rollbacks.values()]:
        if residue.exists():
            raise RuntimeError(f"transaction residue exists: {residue}")

    write_exclusive(lock, canonical_bytes({"edit_id": EDIT_ID, "pid": os.getpid()}))
    lock_identity = identity(lock)
    lock_pin = pin(lock.read_bytes())
    target_identities: dict[str, tuple[int, int, int, int]] = {}
    stage_identities: dict[str, tuple[int, int, int, int]] = {}
    rollback_identities: dict[str, tuple[int, int, int, int]] = {}
    installed_identities: dict[str, tuple[int, int, int, int]] = {}
    installed: list[str] = []
    installed_coherent = False
    lock_removable = False
    try:
        if cohort_state(read_cohort()) != "predecessor":
            raise RuntimeError("source drift after lock acquisition")
        assert_owned(lock, lock_identity, lock_pin, "transaction lock")
        for name in changed:
            target = SOURCE_DIR / name
            target_identities[name] = identity(target)
            if pin(target.read_bytes()) != {
                "bytes": PREDECESSOR[name][0],
                "sha256": PREDECESSOR[name][1],
            }:
                raise RuntimeError(f"target pin drift after lock for {name}")
        for name in changed:
            write_exclusive(rollbacks[name], cohort[name])
            rollback_identities[name] = identity(rollbacks[name])
            assert_owned(
                rollbacks[name],
                rollback_identities[name],
                pin(cohort[name]),
                f"rollback for {name}",
            )
            write_exclusive(stages[name], outputs[name])
            stage_identities[name] = identity(stages[name])
            assert_owned(
                stages[name],
                stage_identities[name],
                pin(outputs[name]),
                f"stage for {name}",
            )
        if cohort_state(read_cohort()) != "predecessor":
            raise RuntimeError("source drift before install")
        for name in changed:
            assert_owned(lock, lock_identity, lock_pin, "transaction lock")
            for installed_name in installed:
                assert_owned(
                    SOURCE_DIR / installed_name,
                    installed_identities[installed_name],
                    {
                        "bytes": SUCCESSOR[installed_name][0],
                        "sha256": SUCCESSOR[installed_name][1],
                    },
                    f"installed target {installed_name}",
                )
            for pending_name in changed:
                if pending_name in installed:
                    continue
                assert_owned(
                    SOURCE_DIR / pending_name,
                    target_identities[pending_name],
                    {
                        "bytes": PREDECESSOR[pending_name][0],
                        "sha256": PREDECESSOR[pending_name][1],
                    },
                    f"pending target {pending_name}",
                )
                assert_owned(
                    stages[pending_name],
                    stage_identities[pending_name],
                    pin(outputs[pending_name]),
                    f"stage for {pending_name}",
                )
                assert_owned(
                    rollbacks[pending_name],
                    rollback_identities[pending_name],
                    pin(cohort[pending_name]),
                    f"rollback for {pending_name}",
                )
            target = SOURCE_DIR / name
            # Repeat the four identities participating in this replacement as
            # the final operations before the atomic install.  The cohort-wide
            # checks above protect cross-file coherence; these checks minimize
            # the per-target check-to-replace window.
            assert_owned(lock, lock_identity, lock_pin, "transaction lock")
            assert_owned(
                target,
                target_identities[name],
                {
                    "bytes": PREDECESSOR[name][0],
                    "sha256": PREDECESSOR[name][1],
                },
                f"pending target {name} immediately before install",
            )
            assert_owned(
                stages[name],
                stage_identities[name],
                pin(outputs[name]),
                f"stage for {name} immediately before install",
            )
            assert_owned(
                rollbacks[name],
                rollback_identities[name],
                pin(cohort[name]),
                f"rollback for {name} immediately before install",
            )
            os.replace(stages[name], target)
            installed.append(name)
            installed_identities[name] = identity(target)
            assert_owned(
                target,
                installed_identities[name],
                pin(outputs[name]),
                f"installed target {name}",
            )
        if cohort_state(read_cohort()) != "successor":
            raise RuntimeError("post-install cohort audit failed")
        installed_coherent = True
        for name in changed:
            assert_owned(lock, lock_identity, lock_pin, "transaction lock")
            assert_owned(
                rollbacks[name],
                rollback_identities[name],
                pin(cohort[name]),
                f"rollback for {name}",
            )
            rollbacks[name].unlink()
        if any(path.exists() for path in [*stages.values(), *rollbacks.values()]):
            raise RuntimeError("transaction residue remains after successor install")
        if cohort_state(read_cohort()) != "successor":
            raise RuntimeError("successor drifted during rollback cleanup")
        assert_owned(lock, lock_identity, lock_pin, "transaction lock")
        lock_removable = True
    except Exception as transaction_error:
        if installed_coherent:
            # The live source cohort reached the exact successor.  A later
            # cleanup failure must never trigger a partial rollback.  Preserve
            # the lock and all remaining evidence for deterministic recovery.
            if cohort_state(read_cohort()) != "successor":
                raise RuntimeError(
                    "coherent successor drifted after install; lock and evidence retained"
                ) from transaction_error
            raise RuntimeError(
                "successor installed but transaction cleanup failed; lock and remaining evidence retained"
            ) from transaction_error

        restoration_safe = True
        for name in reversed(installed):
            target = SOURCE_DIR / name
            rollback = rollbacks[name]
            try:
                assert_owned(
                    target,
                    installed_identities[name],
                    {
                        "bytes": SUCCESSOR[name][0],
                        "sha256": SUCCESSOR[name][1],
                    },
                    f"installed target {name} before restoration",
                )
                assert_owned(
                    rollback,
                    rollback_identities[name],
                    pin(cohort[name]),
                    f"rollback for {name} before restoration",
                )
            except Exception:
                restoration_safe = False
                continue
            os.replace(rollback, target)
            target_identities[name] = identity(target)
            assert_owned(
                target,
                target_identities[name],
                pin(cohort[name]),
                f"restored target {name}",
            )
        if not restoration_safe or cohort_state(read_cohort()) != "predecessor":
            raise RuntimeError(
                "transaction failed and uncertain evidence was preserved; lock retained"
            ) from transaction_error

        for name, path in stages.items():
            if path.exists():
                try:
                    assert_owned(
                        path,
                        stage_identities[name],
                        pin(outputs[name]),
                        f"stage for {name} during recovery cleanup",
                    )
                except Exception as cleanup_error:
                    raise RuntimeError(
                        "recovered predecessor but stage evidence drifted; lock retained"
                    ) from cleanup_error
                path.unlink()
        for name, path in rollbacks.items():
            if path.exists():
                try:
                    assert_owned(
                        path,
                        rollback_identities[name],
                        pin(cohort[name]),
                        f"rollback for {name} during recovery cleanup",
                    )
                except Exception as cleanup_error:
                    raise RuntimeError(
                        "recovered predecessor but rollback evidence drifted; lock retained"
                    ) from cleanup_error
                path.unlink()
        if any(path.exists() for path in [*stages.values(), *rollbacks.values()]):
            raise RuntimeError("recovered predecessor but transaction residue remains")
        assert_owned(lock, lock_identity, lock_pin, "transaction lock")
        lock_removable = True
        raise transaction_error
    finally:
        if lock_removable:
            assert_owned(lock, lock_identity, lock_pin, "transaction lock")
            lock.unlink()


def successor_report(cohort: dict[str, bytes]) -> dict[str, Any]:
    if observed_pins(cohort) != SUCCESSOR:
        raise RuntimeError("live successor pins drifted")
    roots = root_counts(combined_text(cohort))
    for key in ("pomoč", "celost", "imenujuče", "vrědnost_noun", "cěločislovn"):
        if roots[key] != 0:
            raise RuntimeError(f"applied source residue for {key}")
    if hold_counts(cohort) != EXPECTED_HOLD_COUNTS:
        raise RuntimeError("applied hold inventory drifted")
    return {
        "schema": "noether-isv-v021-residual-orthography-semantics-postapply-v1",
        "edit_id": EDIT_ID,
        "status": "APPLIED_AND_HASH_VERIFIED",
        "sources": {name: pin(cohort[name]) for name in SOURCE_ORDER},
        "root_counts": roots,
        "holds": hold_counts(cohort),
        "claims": {
            "applied": True,
            "build": False,
            "render": False,
            "git": False,
            "network": False,
            "publication": False,
        },
    }


def write_receipt(path: Path, report: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite receipt: {path}")
    write_exclusive(
        path, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--write-receipt", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    cohort = read_cohort()
    state = cohort_state(cohort)
    if state == "predecessor":
        outputs, report = audit_predecessor(cohort)
        if args.apply:
            apply_transaction(cohort, outputs)
            report = successor_report(read_cohort())
    else:
        if args.apply:
            raise RuntimeError("edit is already applied")
        report = successor_report(cohort)

    if args.write_receipt:
        write_receipt(args.write_receipt.resolve(), report)
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
