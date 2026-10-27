"""Versioned prompt files (`prompts/<name>.v<N>.md`) with `id` and `version` front matter."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    template: str

    def render(self, **values: object) -> str:
        return Template(self.template).safe_substitute({k: str(v) for k, v in values.items()})

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def prompt_versions(prompts_dir: Path) -> dict[str, str]:
    """Latest version of every prompt in the directory, as recorded in its front matter."""
    names = sorted({p.name.split(".v")[0] for p in prompts_dir.glob("*.v*.md")})
    return {name: load_prompt(prompts_dir, name).version for name in names}


@lru_cache
def load_prompt(prompts_dir: Path, name: str) -> Prompt:
    candidates = sorted(prompts_dir.glob(f"{name}.v*.md"))
    if not candidates:
        raise FileNotFoundError(f"prompt not found: {name}")
    raw = candidates[-1].read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        _, block, body = raw.split("---", 2)
        for line in block.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return Prompt(meta.get("id", name), meta.get("version", "0"), body.strip())
