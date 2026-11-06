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
    """Version in use of every prompt in the directory, as recorded in its front matter: the latest file, except the
    judge, whose version is the configured rubric (`judge.RUBRIC_VERSION`, spec v0.10.0 D1: judge.v4 exists, judge.v3
    stays the default until task 86)."""
    from merchant_assistant.evaluation.judge import RUBRIC_VERSION  # imported here: evaluation depends on this module

    pinned = {"judge": RUBRIC_VERSION}
    names = sorted({p.name.split(".v")[0] for p in prompts_dir.glob("*.v*.md")})
    return {
        name: load_prompt(prompts_dir, name, _pinned(prompts_dir, name, pinned.get(name))).version for name in names
    }


def _pinned(prompts_dir: Path, name: str, version: str | None) -> str | None:
    """The configured version when its file is in the directory, else `None` (the latest)."""
    return version if version is not None and (prompts_dir / f"{name}.v{version}.md").exists() else None


@lru_cache
def load_prompt(prompts_dir: Path, name: str, version: str | None = None) -> Prompt:
    """The latest version of a prompt, or exactly `version` (older campaigns and the on-demand evaluation pin one)."""
    if version is not None:
        pinned = prompts_dir / f"{name}.v{version}.md"
        if not pinned.exists():
            raise FileNotFoundError(f"prompt not found: {name} version {version}")
        candidates = [pinned]
    else:
        candidates = sorted(prompts_dir.glob(f"{name}.v*.md"), key=lambda p: int(p.stem.rsplit(".v", 1)[1]))
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
