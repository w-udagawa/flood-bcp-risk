"""Assessment のシリアライズ（JSON / CSV）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .scoring import Assessment

CSV_FIELDS = [
    "building_id",
    "tier",
    "score_version",
    "data_version",
    "computed_at",
    "status",
    "H",
    "V",
    "I",
    "P",
    "C",
    "priority",
    "priority_raised_by_low_confidence",
    "missing_info",
    "priority_checks",
    "measures",
    "evidence",
]


def write_json(assessments: Iterable[Assessment], path: Path | str) -> None:
    payload = [a.as_dict() for a in assessments]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _flatten_for_csv(a: Assessment) -> dict[str, object]:
    d = a.as_dict()
    row = {k: d[k] for k in CSV_FIELDS if k not in ("missing_info", "priority_checks", "measures", "evidence")}
    row["missing_info"] = json.dumps(d["missing_info"], ensure_ascii=False)
    row["priority_checks"] = json.dumps(d["priority_checks"], ensure_ascii=False)
    row["measures"] = ";".join(d["measures"])
    row["evidence"] = json.dumps(d["evidence"], ensure_ascii=False)
    return row


def write_csv(assessments: Iterable[Assessment], path: Path | str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for a in assessments:
            writer.writerow(_flatten_for_csv(a))
