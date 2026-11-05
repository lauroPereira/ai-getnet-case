r"""Refuses tracked files that mention a personal or machine-specific path (AGENTS.md, "Caminhos pessoais").

A personal path identifies the user or the machine: a home directory (`C:\Users\<name>`, `/home/<name>`,
`/Users/<name>`), `AppData`, a session scratchpad. The project path (`C:\workspace\...`) is not personal.
Placeholders such as `<scratchpad da sessão>`, `%LOCALAPPDATA%`, `$env:LOCALAPPDATA` and `Users\...` pass.

Usage:
  python tools/scripts/checar-caminhos-pessoais.py            # all tracked files
  python tools/scripts/checar-caminhos-pessoais.py a.md b.py  # only these files (e.g. a pre-commit hook)
Exit code 1 lists every occurrence as path:line: text.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
PATTERNS = (
    # Home directories on Windows and macOS (C:\Users\name, /c/Users/name, /Users/name); "Users\..." and
    # "Users\<nome>" are placeholders and pass.
    re.compile(r"[\\/]Users[\\/]{1,2}(?!\.\.\.|<)[A-Za-z0-9_.-]"),
    # Linux home; "/home/<nome>" passes.
    re.compile(r"(?<![\w/])/home/(?!\.\.\.)[A-Za-z0-9_.-]+/"),
    # AppData as part of a path (the bare word in prose and LOCALAPPDATA in upper case pass).
    re.compile(r"AppData[\\/]|[\\/]AppData(?![A-Za-z])"),
)
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".sqlite3", ".db", ".zip", ".gz", ".woff", ".woff2",
}


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [ROOT / name for name in out.decode("utf-8").split("\0") if name]


def occurrences(path: Path) -> list[tuple[int, str]]:
    if path.resolve() == SELF or path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if any(pattern.search(line) for pattern in PATTERNS):
            found.append((number, line.strip()[:160]))
    return found


def main(argv: list[str]) -> int:
    files = [Path(name).resolve() for name in argv] if argv else tracked_files()
    hits = [(path, number, line) for path in files for number, line in occurrences(path)]
    for path, number, line in hits:
        try:
            shown = path.relative_to(ROOT)
        except ValueError:
            shown = path
        print(f"{shown.as_posix()}:{number}: {line}")
    if hits:
        print(f"caminhos pessoais: {len(hits)} ocorrência(s) versionada(s); use caminho relativo ou marcador.")
        return 1
    print(f"caminhos pessoais: nenhuma ocorrência em {len(files)} arquivo(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
