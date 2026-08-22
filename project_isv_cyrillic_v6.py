#!/usr/bin/env python3
"""Hardened ISV019 Cyrillic projector with an explicit TeX-dimension grammar.

Version 6 preserves the TeX units in dimensions such as ``24em`` and ``5pt``.
The v5 linguistic/identity role manifest remains authoritative; this successor
adds only a syntax-level protection rule for TeX dimensions that the first
build exposed.  Default execution is read-only.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
V5_PATH = ROOT / "project_isv_cyrillic_v5.py"
V5_PIN = (
    26_612,
    "723BD60F6CFE7C2E1192610215591C8D59BDECEAC778423FDEB4E105C831CFCB",
)
V5_OUTPUT_PINS = {
    "44-book-isv-cyrl.tex": (
        230_370,
        "13E2391567A522038C3F959C22FA2FAC164D032F82DA811C6447560F5680C9F0",
    ),
    "45-isv-cyrl.tex": (
        35_902,
        "E1568BAB1E389E07816178A2FBDEE3833508C79BF0C7C19DD5120812E24646FE",
    ),
    "base-papers1-43-isv-cyrl.tex": (
        2_707_554,
        "A9B016AA323C656063467393A3F0949D5CAAA611B8FDCE23172AF2D189D4B930",
    ),
    "bib-isv-cyrl.tex": (
        13_255,
        "5A6AE75FF94360BC104CE240E0EC18A2329C5229F68B198F763EDF7E786B816B",
    ),
}

# TeXbook dimensions and infinite glue orders.  The lookbehind prevents a
# normal word such as "em" from being classified as syntax.
TEX_DIMENSION_RE = re.compile(
    r"(?i)(?<=[0-9])(?:true[ \t]*)?"
    r"(?:filll|fill|fil|pt|pc|in|bp|cm|mm|dd|cc|sp|em|ex|mu)\b"
)
CYRILLIC_DIMENSION_RE = re.compile(
    r"(?i)(?<=[0-9])(?:труе[ \t]*)?"
    r"(?:филлл|филл|фил|пт|пц|ин|бп|цм|мм|дд|цц|сп|ем|екс|му)\b"
)
EXPECTED_NEW_VISIBLE_DIMENSION_OCCURRENCES = 447
EXPECTED_NEW_VISIBLE_DIMENSION_SURFACES = {"em": 219, "pt": 228}


class ProjectionV6Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProjectionV6Error(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def describe(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def load_v5() -> Any:
    raw = V5_PATH.read_bytes()
    require((len(raw), sha256(raw)) == V5_PIN, "v5 predecessor pin drift")
    spec = importlib.util.spec_from_file_location("isv019_cyr_v5_for_v6", V5_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v5 predecessor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def dimension_inventory(v5: Any, v2: Any, texts: Mapping[str, str]) -> tuple[dict, dict]:
    ranges: dict[str, list[tuple[int, int, str]]] = {
        name: [] for name in v5.SOURCE_ORDER
    }
    rows: list[dict[str, Any]] = []
    surfaces: Counter[str] = Counter()
    for filename in v5.SOURCE_ORDER:
        text = texts[filename]
        scalar_starts, byte_starts, lines = v2.line_tables(text)
        for segment in v2.TexSegmenter(text).segment():
            if segment.role not in v5.VISIBLE_ROLES:
                continue
            chunk = text[segment.start : segment.end]
            for match in TEX_DIMENSION_RE.finditer(chunk):
                start = segment.start + match.start()
                end = segment.start + match.end()
                surface = text[start:end]
                ranges[filename].append((start, end, "v6:tex_dimension_unit"))
                surfaces[surface.lower()] += 1
                rows.append(
                    {
                        "file": filename,
                        "scalar_span": [start, end],
                        "surface": surface,
                        "surface_sha256": sha256(surface.encode("utf-8")),
                        "role": segment.role,
                        **v2.locator(
                            text, start, scalar_starts, byte_starts, lines
                        ),
                    }
                )
    require(
        len(rows) == EXPECTED_NEW_VISIBLE_DIMENSION_OCCURRENCES,
        f"TeX dimension occurrence drift: {len(rows)}",
    )
    require(
        dict(sorted(surfaces.items())) == EXPECTED_NEW_VISIBLE_DIMENSION_SURFACES,
        f"TeX dimension surface drift: {dict(surfaces)}",
    )
    raw = canonical_json(rows)
    return ranges, {
        "grammar": TEX_DIMENSION_RE.pattern,
        "scope": "numeric TeX dimension units classified as visible by the predecessor segmenter",
        "occurrences": len(rows),
        "by_surface": dict(sorted(surfaces.items())),
        "inventory": describe(raw),
        "disposition": "preserve as TeX syntax; never transliterate",
    }


def project_raws(raws: Mapping[str, bytes]) -> tuple[dict[str, Any], dict[str, bytes]]:
    v5 = load_v5()
    captured: dict[str, Any] = {}
    predecessor_selector = v5.selected_manifest_ranges

    def augmented_selector(v2: Any, manifest: dict, texts: Mapping[str, str]):
        selected, selection = predecessor_selector(v2, manifest, texts)
        dimensions, evidence = dimension_inventory(v5, v2, texts)
        for filename in v5.SOURCE_ORDER:
            selected[filename].extend(dimensions[filename])
        selection = copy.deepcopy(selection)
        selection["tex_dimension_units"] = evidence
        selection["selected_occurrences_before_union"] += evidence["occurrences"]
        captured.update(evidence)
        return selected, selection

    v5.selected_manifest_ranges = augmented_selector
    report, projected = v5.project_raws(raws)
    require(captured, "TeX dimension evidence was not consumed")

    source_dimension_census: dict[str, dict[str, int]] = {}
    output_dimension_census: dict[str, dict[str, int]] = {}
    for filename in v5.SOURCE_ORDER:
        source_text = raws[filename].decode("utf-8")
        output_text = projected[filename].decode("utf-8")
        source_counts = Counter(match.group(0).lower() for match in TEX_DIMENSION_RE.finditer(source_text))
        output_counts = Counter(match.group(0).lower() for match in TEX_DIMENSION_RE.finditer(output_text))
        require(source_counts == output_counts, f"TeX dimension census drift: {filename}")
        require(not CYRILLIC_DIMENSION_RE.search(output_text), f"Cyrillic TeX dimension remains: {filename}")
        source_dimension_census[filename] = dict(sorted(source_counts.items()))
        output_dimension_census[filename] = dict(sorted(output_counts.items()))

    report.pop("report_sha256_excluding_this_field", None)
    report["schema"] = "noether-isv-cyrillic-projection-v6-report-v1"
    report["dependencies"] = {
        "v5_predecessor": {
            "path": V5_PATH.name,
            "bytes": V5_PIN[0],
            "sha256": V5_PIN[1],
            "disposition": "superseded after build exposed transliterated TeX dimensions",
        },
        **report["dependencies"],
    }
    report["tex_dimension_policy"] = {
        **captured,
        "source_census": source_dimension_census,
        "output_census": output_dimension_census,
        "cyrillic_dimension_residuals": 0,
    }
    report["limitations"] = [
        "The Latin source vector is authenticated but not frozen by this projector.",
        "The projector must still pass complete TeX build, text, math, font, link, and visual QA.",
        "No native-speaker, community, or external peer-review certification is claimed.",
    ]
    report["report_sha256_excluding_this_field"] = sha256(canonical_json(report))
    return report, projected


def project_corpus(source_dir: Path | None = None) -> tuple[dict[str, Any], dict[str, bytes]]:
    v5 = load_v5()
    raws = v5.source_raws(v5.SOURCE_DIR if source_dir is None else source_dir)
    return project_raws(raws)


def write_new_outputs(output_dir: Path, projected: Mapping[str, bytes]) -> list[dict[str, Any]]:
    v5 = load_v5()
    return v5.write_outputs(output_dir, projected)


def replace_v5_outputs(output_dir: Path, projected: Mapping[str, bytes]) -> list[dict[str, Any]]:
    require(output_dir.resolve() == (ROOT / "source_cyrillic").resolve(), "replacement target must be source_cyrillic")
    require(output_dir.is_dir() and not output_dir.is_symlink(), "unsafe replacement directory")
    v5 = load_v5()
    targets = {source: output_dir / v5.OUTPUT_NAMES[source] for source in v5.SOURCE_ORDER}
    observed = {
        source: (target.stat().st_size, sha256(target.read_bytes()))
        for source, target in targets.items()
        if target.is_file() and not target.is_symlink()
    }
    new_pins = {source: (len(projected[source]), sha256(projected[source])) for source in v5.SOURCE_ORDER}
    if observed == new_pins:
        return [{"path": str(target), **describe(projected[source])} for source, target in targets.items()]
    expected_old = {source: V5_OUTPUT_PINS[target.name] for source, target in targets.items()}
    require(observed == expected_old, f"existing derived-output vector is neither v5 nor v6: {observed}")

    nonce = f"{os.getpid()}"
    stages: dict[str, Path] = {}
    rollbacks: dict[str, Path] = {}
    try:
        for ordinal, source in enumerate(v5.SOURCE_ORDER, 1):
            target = targets[source]
            stage = output_dir / f".{target.name}.v6-stage-{nonce}-{ordinal}"
            rollback = output_dir / f".{target.name}.v5-rollback-{nonce}-{ordinal}"
            require(not stage.exists() and not rollback.exists(), "transaction path collision")
            with stage.open("xb") as handle:
                handle.write(projected[source])
                handle.flush()
                os.fsync(handle.fileno())
            require(stage.read_bytes() == projected[source], f"stage mismatch: {stage}")
            shutil.copy2(target, rollback)
            require((rollback.stat().st_size, sha256(rollback.read_bytes())) == expected_old[source], f"rollback mismatch: {rollback}")
            stages[source] = stage
            rollbacks[source] = rollback
        for source in v5.SOURCE_ORDER:
            os.replace(stages[source], targets[source])
        for source in v5.SOURCE_ORDER:
            require(targets[source].read_bytes() == projected[source], f"installed output mismatch: {targets[source]}")
        for rollback in rollbacks.values():
            rollback.unlink()
    except Exception:
        for source in reversed(v5.SOURCE_ORDER):
            rollback = rollbacks.get(source)
            target = targets[source]
            if rollback and rollback.exists():
                current = target.read_bytes() if target.exists() else None
                if current is None or current == projected[source]:
                    os.replace(rollback, target)
        for stage in stages.values():
            if stage.exists():
                stage.unlink()
        raise
    return [{"path": str(target), **describe(projected[source])} for source, target in targets.items()]


def compact(report: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema",
        "status",
        "classification",
        "source_order",
        "dependencies",
        "selection",
        "structural_policy",
        "tex_dimension_policy",
        "output_manifest",
        "output_manifest_sha256",
        "conversion_classes",
        "projection_issues",
        "limitations",
        "report_sha256_excluding_this_field",
    )
    return {key: report[key] for key in keys}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--full-report", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--write-output", type=Path)
    parser.add_argument("--replace-v5-output", type=Path)
    args = parser.parse_args(argv)
    require(not (args.write_output and args.replace_v5_output), "select one output mode")
    try:
        report, projected = project_corpus(args.source_dir)
        payload = report if args.full_report else compact(report)
        if args.write_output:
            payload = copy.deepcopy(payload)
            payload["installed_outputs"] = write_new_outputs(args.write_output, projected)
        if args.replace_v5_output:
            payload = copy.deepcopy(payload)
            payload["installed_outputs"] = replace_v5_outputs(args.replace_v5_output, projected)
    except Exception as error:
        failure = {
            "schema": "noether-isv-cyrillic-projection-v6-failure-v1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json(failure))
        return 1
    sys.stdout.buffer.write(canonical_json(payload))
    if args.require_ready and report["status"] != "READY_DETERMINISTIC_DERIVATION_IN_MEMORY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
