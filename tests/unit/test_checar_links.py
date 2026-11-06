"""tools/scripts/checar-links.py: relative Markdown links must resolve inside the repository."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "scripts" / "checar-links.py"


@pytest.fixture()
def checker(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("checar_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path.resolve())
    module.anchors.cache_clear()
    return module


def write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_existing_targets_external_links_and_code_pass(checker, tmp_path):
    write(tmp_path, "docs/b.md", "# Título com `código`\n\n## Seção (RF-1)\n")
    page = write(
        tmp_path,
        "docs/a.md",
        "[b](b.md) [seção](b.md#seção-rf-1) [título](b.md#título-com-código) [web](https://example.com)\n"
        "[raiz](/docs/b.md) [aqui](#local) ![img](b.md)\n\n## Local\n\n"
        "```text\n[cerca](nao-existe.md)\n```\n`[inline](nao-existe.md)`\n[ref]: b.md\n",
    )
    assert checker.problems(page) == []


def test_missing_targets_anchors_drive_paths_and_outside_root_fail(checker, tmp_path):
    write(tmp_path, "docs/b.md", "# B\n")
    page = write(
        tmp_path,
        "docs/a.md",
        "[x](falta.md)\n[y](b.md#nao-ha)\n[z](C:/workspace/outro/arquivo.md)\n[w](../../fora.md)\n[r]: falta2.md\n",
    )
    assert [number for number, _ in checker.problems(page)] == [1, 2, 3, 4, 5]


def test_main_reports_and_returns_one(checker, tmp_path, capsys):
    page = write(tmp_path, "a.md", "[x](falta.md)\n")
    assert checker.main([str(page)]) == 1
    assert "a.md:1: falta.md" in capsys.readouterr().out
