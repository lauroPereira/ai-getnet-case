"""Short catalog of labeled synthetic scenarios used by the demonstration (v0.6.0).

The labels feed the existing deterministic checks of `evaluation.runner`; a run only receives label-dependent
checks when it was started from a catalog scenario with exactly the catalog message."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from merchant_assistant.evaluation.runner import CHECK_KEYS, Case

CATALOG_FILE = Path("scenarios") / "catalog.json"
LABEL_FIELDS = (
    "accepted_routes",
    "expected_status",
    "expected_tools",
    "must_include_amounts",
    "must_include_any",
    "expect_sources",
    "must_not_include",
    "must_not_assert",
)


@lru_cache(maxsize=8)
def _load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    scenarios = {}
    for item in data["scenarios"]:
        if item["id"] in scenarios:
            raise ValueError(f"duplicate scenario {item['id']}")
        scenarios[item["id"]] = item
    return {"version": str(data["version"]), "scenarios": scenarios}


def catalog(data_dir: Path) -> dict:
    return _load(str(Path(data_dir) / CATALOG_FILE))


def get(data_dir: Path, scenario_id: str) -> dict | None:
    return catalog(data_dir)["scenarios"].get(scenario_id)


def as_case(scenario: dict, user_id: str) -> Case:
    return Case(
        id=scenario["id"],
        split="demo",
        message=scenario["message"],
        language=scenario["language"],
        accepted_routes=list(scenario["accepted_routes"]),
        expected_status=scenario["expected_status"],
        expected_tools=list(scenario.get("expected_tools", [])),
        must_include_amounts=list(scenario.get("must_include_amounts", [])),
        must_include_any=[list(group) for group in scenario.get("must_include_any", [])],
        expect_sources=bool(scenario.get("expect_sources", False)),
        must_not_include=list(scenario.get("must_not_include", [])),
        user_id=user_id,
        must_not_assert=list(scenario.get("must_not_assert", [])),
    )


def public_view(scenario: dict) -> dict:
    """What the interface may show: identification, message and which checks the labels enable."""
    return {
        "scenario_id": scenario["id"],
        "title": scenario["title"],
        "journey": scenario["journey"],
        "language": scenario["language"],
        "message": scenario["message"],
        "checks": [*CHECK_KEYS, "errors_ok", "isolation_ok"],
        "labels": {key: scenario[key] for key in LABEL_FIELDS if key in scenario},
    }
