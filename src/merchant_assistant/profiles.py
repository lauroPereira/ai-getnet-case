"""Immutable, versioned model profiles and their execution snapshots."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

AGENTS = ("router", "knowledge", "support", "escalation", "personality", "evaluation")
MAX_OUTPUT_TOKENS_BY_AGENT = {
    "router": 300,
    "knowledge": 500,
    "support": 1200,
    "escalation": 400,
    "personality": 600,
}
OUTPUT_TOKEN_PARAMETER = {
    "type": "integer",
    "minimum": 16,
    "maximum_by_agent": MAX_OUTPUT_TOKENS_BY_AGENT,
    "description": "Upper bound for generated and reasoning tokens; application values only lower existing agent caps.",
}
CATALOG = {
    "openai:gpt-6-luna": {
        "provider": "openai",
        "model": "gpt-6-luna",
        "agents": AGENTS,
        "capabilities": ["structured_output", "tools", "web_search"],
        "parameters": {
            "max_output_tokens": {
                **OUTPUT_TOKEN_PARAMETER,
                "documentation_url": "https://developers.openai.com/api/reference/resources/responses/methods/create",
            }
        },
    },
    "deepseek:deepseek-flash": {
        "provider": "deepseek",
        "model": "deepseek-flash",
        "agents": ("router", "support", "escalation", "personality", "evaluation"),
        "capabilities": ["structured_output", "tools"],
        "parameters": {
            "max_output_tokens": {
                **OUTPUT_TOKEN_PARAMETER,
                "documentation_url": "https://api-docs.deepseek.com/api/create-response/",
            }
        },
    },
    "typesafe:jev-1.14.0": {
        "provider": "typesafe",
        "model": "jev-1.14.0",
        "agents": ("router",),
        "capabilities": ["typed_decisions"],
        "parameters": {},
    },
}


class ProfileAgent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    model: str
    parameters: dict = Field(default_factory=dict)


class ProfileAgents(BaseModel):
    model_config = ConfigDict(extra="forbid")
    router: ProfileAgent
    knowledge: ProfileAgent
    support: ProfileAgent
    escalation: ProfileAgent
    personality: ProfileAgent
    evaluation: ProfileAgent


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def digest(value: str | dict) -> str:
    data = value if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _entry(provider: str, model: str = "gpt-6-luna") -> dict:
    return {"provider": provider, "model": model, "parameters": {}}


def _defaults() -> dict[str, dict]:
    reference = {key: _entry("openai") for key in AGENTS}
    hybrid = dict(reference)
    hybrid["router"] = _entry("deepseek", "deepseek-flash")
    adjusted = dict(reference)
    adjusted["router"] = _entry("deepseek", "deepseek-flash")
    adjusted["support"] = _entry("deepseek", "deepseek-flash")
    return {"reference": reference, "hybrid": hybrid, "adjusted": adjusted}


def bootstrap_profiles(conn: sqlite3.Connection) -> None:
    """Install immutable Reference/Hybrid versions and an editable Adjusted draft."""
    stamp = now()
    for profile_id, agents in _defaults().items():
        published = 0 if profile_id == "adjusted" else 1
        exists = conn.execute("SELECT 1 FROM profiles WHERE profile_id=?", (profile_id,)).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO profiles VALUES (?,?,?,?,?,?,?)",
            (profile_id, profile_id.title(), 1, 1, 1 if published else None, stamp, stamp),
        )
        payload = json.dumps(agents, sort_keys=True)
        conn.execute(
            "INSERT INTO profile_versions VALUES (?,?,?,?,?,?)",
            (profile_id, 1, "published" if published else "draft", payload, digest(agents), stamp),
        )


def validate_agents(value: dict) -> dict:
    agents = ProfileAgents.model_validate(value).model_dump()
    for name, config in agents.items():
        entry = CATALOG.get(f"{config['provider']}:{config['model']}")
        if entry is None or name not in entry["agents"]:
            raise ValueError(f"model is unavailable for agent {name}")
        if name == "router" and config["provider"] == "typesafe":
            raise ValueError("select JEV with router_mechanism='jev'; profile router models must be an LLM")
        parameters = config["parameters"]
        supported = entry.get("parameters", {})
        unknown = set(parameters) - set(supported)
        if unknown:
            unsupported = ", ".join(sorted(unknown))
            raise ValueError(f"unsupported parameter(s) for {config['provider']}:{config['model']}: {unsupported}")
        for parameter, raw_value in parameters.items():
            spec = supported[parameter]
            maximum = spec["maximum_by_agent"].get(name)
            if maximum is None:
                raise ValueError(f"{parameter} is unavailable for agent {name}; Evaluation is reserved for v0.6.0")
            if type(raw_value) is not int:
                raise ValueError(f"{parameter} for agent {name} must be an integer")
            if not spec["minimum"] <= raw_value <= maximum:
                raise ValueError(f"{parameter} for agent {name} must be between {spec['minimum']} and {maximum}")
    return agents


def list_profiles(conn: sqlite3.Connection, *, role: str) -> list[dict]:
    bootstrap_profiles(conn)
    rows = conn.execute("SELECT * FROM profiles ORDER BY profile_id").fetchall()
    result = []
    for row in rows:
        if row["published_version"] is None and role != "admin":
            continue
        if role == "demo" and not row["demo_allowed"]:
            continue
        version = row["published_version"] or row["draft_version"]
        item = conn.execute(
            "SELECT * FROM profile_versions WHERE profile_id=? AND version=?", (row["profile_id"], version)
        ).fetchone()
        result.append(
            {
                "profile_id": row["profile_id"],
                "name": row["name"],
                "version": version,
                "state": item["state"],
                "agents": json.loads(item["agents"]),
                "digest": item["digest"],
                "demo_allowed": bool(row["demo_allowed"]),
            }
        )
    return result


def get_profile(conn: sqlite3.Connection, profile_id: str, version: int | None, *, role: str) -> dict | None:
    bootstrap_profiles(conn)
    row = conn.execute("SELECT * FROM profiles WHERE profile_id=?", (profile_id,)).fetchone()
    if row is None or (role == "demo" and not row["demo_allowed"]):
        return None
    selected = version if version is not None else row["published_version"]
    if selected is None or (role != "admin" and selected != row["published_version"]):
        return None
    item = conn.execute(
        "SELECT * FROM profile_versions WHERE profile_id=? AND version=?", (profile_id, selected)
    ).fetchone()
    if item is None or item["state"] != "published":
        return None
    return {
        "profile_id": profile_id,
        "version": selected,
        "agents": json.loads(item["agents"]),
        "digest": item["digest"],
        "published_at": item["created_at"],
    }


def create_draft(conn: sqlite3.Connection, name: str, agents: dict, *, demo_allowed: bool) -> dict:
    normalized = validate_agents(agents)
    profile_id = f"profile_{uuid.uuid4().hex[:16]}"
    stamp, payload = now(), json.dumps(normalized, sort_keys=True)
    conn.execute(
        "INSERT INTO profiles VALUES (?,?,?,?,?,?,?)", (profile_id, name, int(demo_allowed), 1, None, stamp, stamp)
    )
    conn.execute(
        "INSERT INTO profile_versions VALUES (?,?,?,?,?,?)",
        (profile_id, 1, "draft", payload, digest(normalized), stamp),
    )
    return {
        "profile_id": profile_id,
        "version": 1,
        "state": "draft",
        "agents": normalized,
        "demo_allowed": demo_allowed,
    }


def update_draft(conn: sqlite3.Connection, profile_id: str, expected_version: int, agents: dict) -> dict:
    row = conn.execute("SELECT * FROM profiles WHERE profile_id=?", (profile_id,)).fetchone()
    if row is None:
        raise LookupError("profile not found")
    if row["published_version"] == expected_version:
        raise PermissionError("published profile versions are immutable")
    if row["draft_version"] != expected_version:
        raise RuntimeError("profile version conflict")
    normalized = validate_agents(agents)
    version = expected_version + 1
    stamp, payload = now(), json.dumps(normalized, sort_keys=True)
    conn.execute(
        "INSERT INTO profile_versions VALUES (?,?,?,?,?,?)",
        (profile_id, version, "draft", payload, digest(normalized), stamp),
    )
    conn.execute("UPDATE profiles SET draft_version=?, updated_at=? WHERE profile_id=?", (version, stamp, profile_id))
    return {"profile_id": profile_id, "version": version, "state": "draft", "agents": normalized}


def publish(conn: sqlite3.Connection, profile_id: str, expected_version: int) -> dict:
    row = conn.execute("SELECT * FROM profiles WHERE profile_id=?", (profile_id,)).fetchone()
    if row is None:
        raise LookupError("profile not found")
    if row["draft_version"] != expected_version:
        raise RuntimeError("profile version conflict")
    item = conn.execute(
        "SELECT * FROM profile_versions WHERE profile_id=? AND version=?", (profile_id, expected_version)
    ).fetchone()
    if item is None or item["state"] != "draft":
        raise PermissionError("only a draft can be published")
    agents = validate_agents(json.loads(item["agents"]))
    stamp = now()
    conn.execute(
        "UPDATE profile_versions SET state='published' WHERE profile_id=? AND version=?", (profile_id, expected_version)
    )
    conn.execute(
        "UPDATE profiles SET published_version=?, updated_at=? WHERE profile_id=?",
        (expected_version, stamp, profile_id),
    )
    return {
        "profile_id": profile_id,
        "version": expected_version,
        "state": "published",
        "agents": agents,
        "digest": item["digest"],
        "published_at": stamp,
    }
