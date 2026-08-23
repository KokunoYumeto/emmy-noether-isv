#!/usr/bin/env python3
"""Build compact machine indexes over the frozen 171-row editorial ledger."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "NORMALIZATION_DECISIONS_v019.jsonl"
DECISIONS = ROOT / "decision_records"
OUTPUT = ROOT / "release_v019" / "evidence"
LEDGER_PIN = (
    771_044,
    "4391C7FE0B81253F599118EED95927CDBA9B66A6C9644FECEEE98F5F53FC50F3",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha256_bytes(raw)}


def collect_alternative_fields(value: Any, path: str = "$") -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            lowered = key.casefold()
            if "alternative" in lowered or "reject" in lowered:
                results.append({"path": child_path, "value": child})
            else:
                results.extend(collect_alternative_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            results.extend(collect_alternative_fields(child, f"{path}[{index}]"))
    return results


def main() -> int:
    ledger_raw = LEDGER.read_bytes()
    if (len(ledger_raw), sha256_bytes(ledger_raw)) != LEDGER_PIN:
        raise RuntimeError("ledger pin drift")
    rows = [json.loads(line) for line in ledger_raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != 171:
        raise RuntimeError(f"ledger row drift: {len(rows)}")
    ids = [row.get("decision_id") for row in rows]
    if len(set(ids)) != len(ids) or ids[-1] != "ISV019-EDIT-0171":
        raise RuntimeError("ledger identity or head drift")

    index_rows = []
    rejected_rows = []
    tsv_rows = []
    for ordinal, row in enumerate(rows, 1):
        decision_id = row["decision_id"]
        companions = []
        alternative_fields = collect_alternative_fields(row, "$.ledger_row")
        for suffix in (".json", ".md"):
            path = DECISIONS / f"{decision_id}{suffix}"
            if not path.is_file():
                continue
            companions.append(record(path))
            if suffix == ".json":
                sidecar = json.loads(path.read_text(encoding="utf-8"))
                alternative_fields.extend(collect_alternative_fields(sidecar, "$.sidecar"))
        classification = (
            row.get("classification")
            or row.get("epistemic_type")
            or row.get("scope")
            or row.get("choice")
            or "UNCLASSIFIED_LEGACY_ROW"
        )
        source_change_declared = bool(
            row.get("source_change")
            or (isinstance(row.get("claims"), dict) and row["claims"].get("source_changes"))
            or (isinstance(row.get("result"), dict) and any("source" in str(key).casefold() for key in row["result"]))
        )
        index_rows.append(
            {
                "ordinal": ordinal,
                "decision_id": decision_id,
                "recorded_at": row.get("recorded_at"),
                "epistemic_type": row.get("epistemic_type"),
                "classification_or_scope": classification,
                "source_change_declared": source_change_declared,
                "alternative_field_count": len(alternative_fields),
                "companions": companions,
            }
        )
        if alternative_fields:
            rejected_rows.append(
                {
                    "decision_id": decision_id,
                    "ordinal": ordinal,
                    "fields": alternative_fields,
                }
            )
        tsv_rows.append(
            {
                "ordinal": ordinal,
                "decision_id": decision_id,
                "recorded_at": row.get("recorded_at") or "",
                "epistemic_type": row.get("epistemic_type") or "",
                "source_change_declared": str(source_change_declared).lower(),
                "alternative_field_count": len(alternative_fields),
                "companion_count": len(companions),
            }
        )

    index = {
        "schema": "noether-interslavic-editorial-decision-index/1.0",
        "release_id": "NOETHER-ISV-v019",
        "generated_at": "2026-08-22T00:00:00Z",
        "ledger": {**record(LEDGER), "rows": len(rows), "head": ids[-1]},
        "decisions": index_rows,
        "summary": {
            "decisions": len(rows),
            "decisions_with_explicit_alternative_or_rejection_fields": len(rejected_rows),
            "explicit_alternative_or_rejection_fields": sum(row["alternative_field_count"] for row in index_rows),
            "decisions_with_companion_files": sum(bool(row["companions"]) for row in index_rows),
        },
        "interpretation": "The ledger and sidecars are controlling evidence. This index is a discovery aid and does not replace them. Some later role-protection decisions encode rejected alternatives in human companions or candidate receipts rather than a field whose key contains alternative/reject.",
    }
    index_path = OUTPUT / "DECISION_INDEX.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    rejected_path = OUTPUT / "REJECTED_ALTERNATIVES_INDEX.jsonl"
    rejected_payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rejected_rows)
    rejected_path.write_text(rejected_payload, encoding="utf-8", newline="\n")

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(tsv_rows[0]), dialect="excel-tab", lineterminator="\n")
    writer.writeheader()
    writer.writerows(tsv_rows)
    manifest_path = OUTPUT / "APPLIED_EDIT_MANIFEST.tsv"
    manifest_path.write_text(buffer.getvalue(), encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "status": "PASS",
                "index": record(index_path),
                "rejected_alternatives": {**record(rejected_path), "rows": len(rejected_rows)},
                "applied_edit_manifest": {**record(manifest_path), "rows": len(tsv_rows)},
                "summary": index["summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
