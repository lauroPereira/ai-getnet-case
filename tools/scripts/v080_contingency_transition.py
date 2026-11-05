"""Task 77: raise the v080-qa fixed cap from USD 1.10 to 1.40 and the primary ceiling from USD 1.70 to 2.00.

The contingency approved on 2026-11-05 adds at most USD 0.30 to the campaign that is already mounted. Both ledgers
keep their history: only `fixed_budget_cap.limit_usd` (campaign) and the two `.limit` sidecars change. The logical
SHA-256 of the ledger entries must be the same before and after.

Dry run is the default: it opens both ledgers read-only, checks everything and prints the plan. `--apply` needs
explicit ledger paths and a new audit directory; it backs up each SQLite file and the sidecar bytes, writes
`prepared.json`, applies, verifies and writes `applied.json`. A rerun after a complete apply changes nothing; a rerun
after an interrupted apply finishes the remaining steps.

    python tools/scripts/v080_contingency_transition.py --primary P --campaign C            # dry run
    python tools/scripts/v080_contingency_transition.py --primary P --campaign C --apply --audit-dir D
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

CAP_ID = "v080-qa"
CAMPAIGN_BEFORE, CAMPAIGN_AFTER = 1.10, 1.40
PRIMARY_BEFORE, PRIMARY_AFTER = 1.70, 2.00
ABSOLUTE_LIMIT_USD = 5.0
PROCESS_MARKERS = ("merchant_assistant", "merchant-assistant", "uvicorn")
LEDGER_COLUMNS = "id,at,request_id,agent,model,reserved_usd,actual_usd,status"


class TransitionError(Exception):
    pass


def _same(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12)


def _sidecar(path: Path) -> Path:
    return Path(f"{path}.limit")


def _read_ceiling(path: Path) -> float:
    try:
        value = float(_sidecar(path).read_text(encoding="ascii").strip())
    except (OSError, ValueError) as exc:
        raise TransitionError(f"{_sidecar(path)}: missing or invalid ceiling sidecar") from exc
    if not math.isfinite(value) or not 0 <= value <= ABSOLUTE_LIMIT_USD:
        raise TransitionError(f"{_sidecar(path)}: ceiling {value!r} is outside USD 0 to 5")
    return value


@contextlib.contextmanager
def _connect(path: Path, *, write: bool):
    """An autocommit connection that is always closed (Windows keeps open SQLite files locked)."""
    if not path.is_file():
        raise TransitionError(f"{path}: ledger not found")
    if write:
        conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    else:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=10, isolation_level=None)
    try:
        conn.execute("PRAGMA busy_timeout = 10000")
        yield conn
    finally:
        conn.close()


def ledger_snapshot(conn: sqlite3.Connection) -> dict:
    """Entries in id order, serialized with exact float representations, plus the numbers the audit records."""
    rows = conn.execute(f"SELECT {LEDGER_COLUMNS} FROM ledger ORDER BY id").fetchall()
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps([repr(v) if isinstance(v, float) else v for v in row]).encode("utf-8") + b"\n")
    committed = sum((row[6] if row[7] == "settled" else row[5] if row[7] == "reserved" else 0.0) or 0.0 for row in rows)
    return {
        "entries": len(rows),
        "last_id": rows[-1][0] if rows else None,
        "open_reservations": sum(1 for row in rows if row[7] == "reserved"),
        "committed_usd": round(committed, 8),
        "logical_sha256": digest.hexdigest(),
    }


def _cap_rows(conn: sqlite3.Connection) -> list[tuple]:
    try:
        return conn.execute("SELECT cap_id,limit_usd FROM fixed_budget_cap").fetchall()
    except sqlite3.Error as exc:
        raise TransitionError("campaign ledger has no fixed_budget_cap table") from exc


def _stage(value: float, before: float, after: float, label: str) -> str:
    if _same(value, before):
        return "before"
    if _same(value, after):
        return "after"
    raise TransitionError(f"{label} is {value!r}; expected {before!r} (before) or {after!r} (after)")


def inspect(primary: Path, campaign: Path) -> dict:
    """Read-only state of both ledgers; raises when either is not in a state this transition knows."""
    if primary.resolve() == campaign.resolve():
        raise TransitionError("primary and campaign must be different ledgers")
    with _connect(primary, write=False) as p_conn, _connect(campaign, write=False) as c_conn:
        p_snap, c_snap = ledger_snapshot(p_conn), ledger_snapshot(c_conn)
        rows = _cap_rows(c_conn)
    if len(rows) != 1 or rows[0][0] != CAP_ID:
        raise TransitionError(f"campaign ledger must hold exactly one {CAP_ID!r} cap; found {rows!r}")
    p_ceiling, c_ceiling, c_cap = _read_ceiling(primary), _read_ceiling(campaign), float(rows[0][1])
    stages = {
        "primary_ceiling": _stage(p_ceiling, PRIMARY_BEFORE, PRIMARY_AFTER, "primary ceiling sidecar"),
        "campaign_ceiling": _stage(c_ceiling, CAMPAIGN_BEFORE, CAMPAIGN_AFTER, "campaign ceiling sidecar"),
        "campaign_cap": _stage(c_cap, CAMPAIGN_BEFORE, CAMPAIGN_AFTER, "fixed_budget_cap.limit_usd"),
    }
    if stages["campaign_ceiling"] == "after" and stages["campaign_cap"] == "before":
        raise TransitionError(
            "campaign sidecar is already 1.40 while the cap record is 1.10; not a state this procedure produces"
        )
    for name, snap in (("primary", p_snap), ("campaign", c_snap)):
        if snap["open_reservations"]:
            raise TransitionError(f"{name} ledger has {snap['open_reservations']} open reservation(s)")
    return {
        "primary": {"path": str(primary), "ceiling_usd": p_ceiling, **p_snap},
        "campaign": {"path": str(campaign), "ceiling_usd": c_ceiling, "cap_usd": c_cap, **c_snap},
        "stages": stages,
        "complete": all(stage == "after" for stage in stages.values()),
        "coverage_after_usd": {
            "primary_room": round(PRIMARY_AFTER - p_snap["committed_usd"], 8),
            "campaign_room": round(CAMPAIGN_AFTER - c_snap["committed_usd"], 8),
        },
    }


def project_processes() -> list[str]:
    """Command lines of running project processes (API, uvicorn, CLI), excluding this one."""
    if os.name == "nt":
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId)`t$($_.CommandLine)" }',
        ]
    else:
        command = ["ps", "-eo", "pid=,args="]
    try:
        output = subprocess.run(command, capture_output=True, text=True, timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise TransitionError(f"could not list processes to confirm none of the project is running: {exc}") from exc
    found = []
    for line in output.splitlines():
        pid, _, args = line.strip().partition("\t" if os.name == "nt" else " ")
        if pid.strip() == str(os.getpid()) or Path(__file__).name in args:
            continue
        if any(marker in args.lower() for marker in PROCESS_MARKERS):
            found.append(line.strip())
    return found


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha256(path: Path) -> str:
    """Hash of a text source with LF line endings, so it matches the versioned blob on any checkout."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _backup(source: Path, target: Path) -> dict:
    with _connect(source, write=False) as src, contextlib.closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    with _connect(target, write=False) as check:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise TransitionError(f"{target}: backup failed the integrity check")
        snapshot = ledger_snapshot(check)
    sidecar_copy = Path(f"{target}.limit.bytes")
    sidecar_copy.write_bytes(_sidecar(source).read_bytes())
    return {
        "sqlite": str(target),
        "sqlite_sha256": _file_sha256(target),
        "logical_sha256": snapshot["logical_sha256"],
        "sidecar_bytes": str(sidecar_copy),
        "sidecar_sha256": _file_sha256(sidecar_copy),
    }


def _write_ceiling(path: Path, value: float) -> None:
    """Replace the sidecar atomically with the exact representation the budget guard publishes (`repr` and a line
    end), keeping the line terminator of the current file (the guard writes in text mode, CRLF on Windows)."""
    sidecar = _sidecar(path)
    terminator = b"\r\n" if sidecar.read_bytes().endswith(b"\r\n") else b"\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{sidecar.name}.", suffix=".tmp", dir=sidecar.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(repr(value).encode("ascii") + terminator)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, sidecar)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _raise_campaign_cap(campaign: Path) -> None:
    with _connect(campaign, write=True) as conn:
        conn.execute("BEGIN EXCLUSIVE")
        try:
            if conn.execute("SELECT COUNT(*) FROM ledger WHERE status='reserved'").fetchone()[0]:
                raise TransitionError("campaign ledger gained an open reservation")
            cur = conn.execute(
                "UPDATE fixed_budget_cap SET limit_usd=? WHERE cap_id=? AND abs(limit_usd - ?) <= 1e-12",
                (CAMPAIGN_AFTER, CAP_ID, CAMPAIGN_BEFORE),
            )
            if cur.rowcount != 1:
                raise TransitionError("campaign cap record changed while applying")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply(primary: Path, campaign: Path, audit_dir: Path, *, processes=project_processes) -> dict:
    before = inspect(primary, campaign)
    if before["complete"]:
        return {"result": "already_applied", "state": before}
    running = processes()
    if running:
        raise TransitionError(f"project processes are running: {running}")
    if audit_dir.exists() and any(audit_dir.iterdir()):
        raise TransitionError(f"{audit_dir}: audit directory must be new or empty")
    audit_dir.mkdir(parents=True, exist_ok=True)
    prepared = {
        "procedure": Path(__file__).name,
        "procedure_sha256": _source_sha256(Path(__file__)),
        "at": _now(),
        "targets": {
            "campaign_cap_usd": CAMPAIGN_AFTER,
            "campaign_ceiling_usd": CAMPAIGN_AFTER,
            "primary_ceiling_usd": PRIMARY_AFTER,
        },
        "before": before,
        "project_processes": running,
        "backups": {
            "primary": _backup(primary, audit_dir / "primary.backup.sqlite3"),
            "campaign": _backup(campaign, audit_dir / "campaign.backup.sqlite3"),
        },
    }
    for name in ("primary", "campaign"):
        if prepared["backups"][name]["logical_sha256"] != before[name]["logical_sha256"]:
            raise TransitionError(f"{name} backup does not hold the same entries")
    _write_json(audit_dir / "prepared.json", prepared)

    if before["stages"]["campaign_cap"] == "before":
        _raise_campaign_cap(campaign)
    if before["stages"]["campaign_ceiling"] == "before":
        _write_ceiling(campaign, CAMPAIGN_AFTER)
    if before["stages"]["primary_ceiling"] == "before":
        _write_ceiling(primary, PRIMARY_AFTER)

    after = inspect(primary, campaign)
    checks = {
        "complete": after["complete"],
        **{
            f"{name}_{key}_unchanged": after[name][key] == before[name][key]
            for name in ("primary", "campaign")
            for key in ("logical_sha256", "entries", "last_id", "committed_usd")
        },
        "primary_covers_campaign": after["coverage_after_usd"]["primary_room"]
        >= after["coverage_after_usd"]["campaign_room"],
    }
    applied = {
        "at": _now(),
        "after": after,
        "checks": checks,
        "result": "applied" if all(checks.values()) else "verification_failed",
    }
    _write_json(audit_dir / "applied.json", applied)
    if not all(checks.values()):
        raise TransitionError(f"post-apply verification failed: {checks}")
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--primary", required=True, type=Path, help="Primary ledger (budget.sqlite3).")
    parser.add_argument("--campaign", required=True, type=Path, help="Campaign ledger (budget-v080-qa.sqlite3).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="Check and print the plan (default).")
    mode.add_argument("--apply", action="store_true", help="Apply; needs --audit-dir.")
    parser.add_argument("--audit-dir", type=Path, help="New directory for backups, prepared.json and applied.json.")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            if args.audit_dir is None:
                parser.error("--apply needs --audit-dir")
            result = apply(args.primary, args.campaign, args.audit_dir)
        else:
            state = inspect(args.primary, args.campaign)
            result = {
                "result": "dry_run",
                "would_change": [name for name, stage in state["stages"].items() if stage == "before"],
                "project_processes": project_processes(),
                "state": state,
            }
    except TransitionError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
