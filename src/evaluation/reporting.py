from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.core.metrics import success_rate


@dataclass(frozen=True)
class PromptRunRecord:
    variant: str
    prompt_id: str
    category: str
    success: bool
    first_render_success: bool
    repair_rounds: int
    elapsed_seconds: float
    estimated_api_cost_usd: float
    provider_sequence: list[str]
    error: str


def aggregate_records(records: list[PromptRunRecord]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[PromptRunRecord]] = {}
    for record in records:
        grouped.setdefault(record.variant, []).append(record)

    aggregates: dict[str, dict[str, float]] = {}
    for variant, items in grouped.items():
        count = len(items)
        aggregates[variant] = {
            "count": float(count),
            "first_render_success_rate": success_rate([item.first_render_success for item in items]),
            "final_success_rate": success_rate([item.success for item in items]),
            "average_repair_rounds": _average([float(item.repair_rounds) for item in items]),
            "average_elapsed_seconds": _average([item.elapsed_seconds for item in items]),
            "average_api_cost_usd": _average([item.estimated_api_cost_usd for item in items]),
        }
    return aggregates


def write_reports(records: list[PromptRunRecord], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "results.json"
    csv_path = output_dir / "results.csv"
    payload = {
        "records": [asdict(record) for record in records],
        "aggregates": aggregate_records(records),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "variant",
                "prompt_id",
                "category",
                "success",
                "first_render_success",
                "repair_rounds",
                "elapsed_seconds",
                "estimated_api_cost_usd",
                "provider_sequence",
                "error",
            ],
        )
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row["provider_sequence"] = " > ".join(record.provider_sequence)
            writer.writerow(row)

    return json_path, csv_path


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
