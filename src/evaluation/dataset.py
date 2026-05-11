from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATASET = Path("data/evaluation/math_animation_prompts.json")


@dataclass(frozen=True)
class PromptCase:
    id: str
    category: str
    prompt: str


def load_prompt_cases(path: Path = DEFAULT_DATASET, limit: int | None = None) -> list[PromptCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        PromptCase(
            id=str(item["id"]),
            category=str(item["category"]),
            prompt=str(item["prompt"]),
        )
        for item in data
    ]
    return cases[:limit] if limit is not None else cases
