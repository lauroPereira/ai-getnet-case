r"""Refuses tracked Markdown files with a relative link whose target does not exist.

For every tracked `*.md` (except `docs/raw/`, kept as delivered), each inline link `[text](target)`, image
`![alt](target)` and reference definition `[label]: target` outside code is resolved against the file's directory
(or the repository root when it starts with `/`) and must exist inside the repository: a local absolute path
(`C:/...`) or a target outside the repository does not resolve on the hosting site. External schemes (`http:`,
`https:`, `mailto:` ...) are skipped. A `#fragment` pointing at a Markdown file, or at the file itself, must match one
of its headings, slugged as GitHub does.

Usage:
  python tools/scripts/checar-links.py            # all tracked Markdown files
  python tools/scripts/checar-links.py a.md b.md  # only these files
Exit code 1 lists every broken link as path:line: target.
"""

from __future__ import annotations

import re
import subprocess
import sys
from functools import cache
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_PREFIXES = (("docs", "raw"),)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
INLINE_LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*(<[^>]*>|[^\s()]*(?:\([^\s()]*\)[^\s()]*)*)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
HTML_ANCHOR = re.compile(r"<a\s+(?:name|id)=\"([^\"]+)\"", re.IGNORECASE)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+:")  # two letters or more: "C:" is a drive, not a scheme
DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def tracked_markdown() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, check=True, capture_output=True).stdout
    files = []
    for name in out.decode("utf-8").split("\0"):
        if not name:
            continue
        parts = Path(name).parts
        if any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIXES):
            continue
        files.append(ROOT / name)
    return files


def lines_outside_code(text: str, keep_inline: bool = False) -> list[tuple[int, str]]:
    """Lines outside fenced blocks, numbered from 1, with inline code removed unless `keep_inline`."""
    kept, fence = [], None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
            continue
        if match:
            fence = match.group(1)
            continue
        kept.append((number, line if keep_inline else INLINE_CODE.sub("", line)))
    return kept


def slug(heading: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links keep their text
    text = re.sub(r"<[^>]+>", "", text).replace("`", "")
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


@cache
def anchors(path: Path) -> frozenset[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return frozenset()
    seen: dict[str, int] = {}
    found = set()
    for _, line in lines_outside_code(text, keep_inline=True):
        found.update(HTML_ANCHOR.findall(line))
        match = HEADING.match(line)
        if not match:
            continue
        base = slug(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return frozenset(found)


def broken(path: Path, target: str) -> bool:
    target = target.strip("<>").strip()
    if not target or SCHEME.match(target):
        return False
    if DRIVE.match(target):
        return True
    target, _, fragment = target.partition("#")
    target = unquote(target.split("?", 1)[0])
    if target:
        base = ROOT if target.startswith("/") else path.parent
        resolved = (base / target.lstrip("/")).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            return True
    else:
        resolved = path
    if fragment and resolved.suffix.lower() == ".md" and resolved.is_file():
        return unquote(fragment).lower() not in anchors(resolved)
    return False


def problems(path: Path) -> list[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    found = []
    for number, line in lines_outside_code(text):
        targets = [match.group(1) for match in INLINE_LINK.finditer(line)]
        reference = REFERENCE.match(line)
        if reference:
            targets.append(reference.group(1))
        found.extend((number, target) for target in targets if broken(path, target))
    return found


def main(argv: list[str]) -> int:
    files = [Path(name).resolve() for name in argv] if argv else tracked_markdown()
    hits = [(path, number, target) for path in files for number, target in problems(path)]
    for path, number, target in hits:
        try:
            shown = path.relative_to(ROOT).as_posix()
        except ValueError:
            shown = path.as_posix()
        print(f"{shown}:{number}: {target}")
    if hits:
        print(f"Links quebrados: {len(hits)} em {len({path for path, _, _ in hits})} arquivo(s).")
        return 1
    print(f"Links relativos: nenhum alvo ausente em {len(files)} arquivo(s) Markdown.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
