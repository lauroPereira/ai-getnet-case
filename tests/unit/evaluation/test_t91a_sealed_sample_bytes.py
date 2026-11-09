"""Task 91a (spec v0.11.0 D5): the sealed calibration sample of v0.11.0 comes back with the sealed bytes from any
checkout. The two CSVs keep the bytes the seal records (CRLF between records, LF inside multi-line fields, as
written) and the seal file keeps its own (LF lines); under `* text=auto` Git could give other bytes back, so
`.gitattributes` marks the three `-text`."""

from __future__ import annotations

import hashlib
import shutil
import subprocess

import pytest

from merchant_assistant.config import PROJECT_ROOT

SEAL = PROJECT_ROOT / "tests" / "scenarios" / "calibration_v0110.sha256"
SEALED = (
    "docs/evidence/v0110-calibracao-amostra.csv",
    "docs/evidence/v0110-calibracao-amostra-claims.csv",
    "tests/scenarios/calibration_v0110.sha256",
)


def sealed_hashes() -> dict[str, str]:
    lines = SEAL.read_text(encoding="utf-8").splitlines()
    pairs = (line.split(maxsplit=1) for line in lines if line.strip() and not line.startswith("#"))
    return {name.lstrip("*"): digest for digest, name in pairs}


def test_gitattributes_keeps_the_sealed_files_out_of_line_ending_conversion():
    rules = {
        tuple(line.split())
        for line in (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert all((path, "-text") in rules for path in SEALED)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_git_reports_text_unset_for_the_sealed_files():
    done = subprocess.run(
        ["git", "check-attr", "text", "--", *SEALED], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        pytest.skip("not a Git working tree")
    assert done.stdout.splitlines() == [f"{path}: text: unset" for path in SEALED]


def test_the_versioned_csvs_have_the_bytes_the_seal_records():
    hashes = sealed_hashes()
    for path in SEALED[:2]:
        name = path.rsplit("/", 1)[1]
        data = (PROJECT_ROOT / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == hashes[name], path
        assert b"\r\n" in data  # the sealed bytes: CRLF between records, as written
    assert b"\r" not in SEAL.read_bytes()  # the seal itself is LF
