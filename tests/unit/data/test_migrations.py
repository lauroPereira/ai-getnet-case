import json
import sqlite3
from types import SimpleNamespace

import pytest

from merchant_assistant import cli
from merchant_assistant.config import Settings
from merchant_assistant.data.clock import FixedClock
from merchant_assistant.data.db import connect
from merchant_assistant.data.migrations import LATEST, RollbackRefused, current_version, migrate
from merchant_assistant.data.seed import seed
from merchant_assistant.data.webhook_outbox import enqueue

DOWN_TO_9 = ["down 0011_evaluation_rubric", "down 0010_webhook_outbox"]
DOWN_TO_8 = [*DOWN_TO_9, "down 0009_identity_hitl"]
UP_FROM_9 = ["up 0010_webhook_outbox", "up 0011_evaluation_rubric"]
UP_FROM_8 = ["up 0009_identity_hitl", *UP_FROM_9]


def tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_new_database_reaches_latest(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    assert current_version(conn) == LATEST
    assert {
        "conversations",
        "messages",
        "case_attempts",
        "customers",
        "enablement_requests",
        "sale_cancellations",
        "profiles",
        "profile_versions",
        "api_principals",
        "api_sessions",
        "router_comparisons",
        "run_snapshots",
        "kb_documents",
        "kb_drafts",
        "kb_versions",
        "kb_state",
        "kb_events",
        "webhook_outbox",
    } <= tables(conn)


def test_outbox_0010_upgrades_v9_without_losing_existing_rows(tmp_path):
    conn = connect(tmp_path / "v9.sqlite3")
    assert migrate(conn, 9) == DOWN_TO_9
    conn.execute(
        "INSERT INTO webhook_inbox VALUES ('evt_old','ticketing','ticket.assigned','hc_old',200,'{}','2026-01-01')"
    )
    assert migrate(conn) == UP_FROM_9
    assert conn.execute("SELECT event_id FROM webhook_inbox").fetchone()[0] == "evt_old"
    assert conn.execute("SELECT COUNT(*) FROM webhook_outbox").fetchone()[0] == 0
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_outbox_is_part_of_the_callers_transaction_and_masks_each_destination(tmp_path):
    conn = connect(tmp_path / "outbox.sqlite3")
    data = {"case_id": "hc_1", "operator_id": "op_ana", "reply_text": "Cartão 4111111111111111"}
    conn.execute("BEGIN IMMEDIATE")
    enqueue(conn, "conversation.replied", data, "action-1")
    conn.execute("ROLLBACK")
    assert conn.execute("SELECT COUNT(*) FROM webhook_outbox").fetchone()[0] == 0
    conn.execute("BEGIN IMMEDIATE")
    event_id = enqueue(conn, "conversation.replied", data, "action-1")
    conn.execute("COMMIT")
    assert enqueue(conn, "conversation.replied", data | {"reply_text": "different"}, "action-1") == event_id
    rows = conn.execute("SELECT target,body FROM webhook_outbox ORDER BY target").fetchall()
    assert len(rows) == 2 and all("4111111111111111" not in row["body"] for row in rows)
    assert "op_ana" not in rows[0]["body"] and "op_ana" in rows[1]["body"]


def test_down_and_up_keep_core_data(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    assert migrate(conn, 1) == [
        "down 0011_evaluation_rubric",
        "down 0010_webhook_outbox",
        "down 0009_identity_hitl",
        "down 0008_demo_results",
        "down 0007_kb_versions",
        "down 0006_profiles_api",
        "down 0005_business_journeys",
        "down 0004_handoff_conversation",
        "down 0003_case_attempts",
        "down 0002_conversations",
    ]
    assert "conversations" not in tables(conn) and current_version(conn) == 1
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 2
    assert migrate(conn) == [
        "up 0002_conversations",
        "up 0003_case_attempts",
        "up 0004_handoff_conversation",
        "up 0005_business_journeys",
        "up 0006_profiles_api",
        "up 0007_kb_versions",
        "up 0008_demo_results",
        "up 0009_identity_hitl",
        "up 0010_webhook_outbox",
        "up 0011_evaluation_rubric",
    ]
    assert current_version(conn) == LATEST


def test_database_from_010_is_upgraded_in_place(tmp_path):
    path = tmp_path / "old.sqlite3"
    raw = sqlite3.connect(path, isolation_level=None)
    raw.executescript(
        "CREATE TABLE customers (customer_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, "
        "segment TEXT NOT NULL); INSERT INTO customers VALUES ('c1','Old','x');"
    )
    raw.close()
    conn = connect(path)
    assert current_version(conn) == LATEST
    assert conn.execute("SELECT display_name FROM customers").fetchone()[0] == "Old"


def test_full_rollback_and_invalid_target(tmp_path):
    conn = connect(tmp_path / "db.sqlite3")
    migrate(conn, 0)
    assert tables(conn) <= {"schema_version", "sqlite_sequence"}
    try:
        migrate(conn, LATEST + 1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_journeys_migration_round_trip_preserves_core_data(tmp_path):
    conn = connect(tmp_path / "journeys.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    before = conn.execute("SELECT sale_id, gross_minor FROM sales ORDER BY sale_id").fetchall()
    assert migrate(conn, 4) == [
        "down 0011_evaluation_rubric",
        "down 0010_webhook_outbox",
        "down 0009_identity_hitl",
        "down 0008_demo_results",
        "down 0007_kb_versions",
        "down 0006_profiles_api",
        "down 0005_business_journeys",
    ]
    assert "enablement_requests" not in tables(conn)
    assert [tuple(row) for row in conn.execute("SELECT sale_id, gross_minor FROM sales ORDER BY sale_id")] == [
        tuple(row) for row in before
    ]
    assert migrate(conn, 5) == ["up 0005_business_journeys"]
    assert current_version(conn) == 5


def test_identity_migration_0009_round_trip(tmp_path):
    conn = connect(tmp_path / "identity.sqlite3")
    assert migrate(conn, 8) == DOWN_TO_8
    conn.execute("INSERT INTO api_principals VALUES ('demo:default','demo','cliente1988','d1',1)")
    conn.execute(
        "INSERT INTO api_sessions(session_id,token_digest,principal_id,created_at,expires_at) "
        "VALUES ('s1','t1','demo:default','a','b')"
    )
    assert migrate(conn) == UP_FROM_8
    # Existing principals keep their sessions and receive the scopes of their role.
    assert conn.execute("SELECT scopes FROM api_principals").fetchone()[0] == (
        '["support:read","handoff:create","conversation:read"]'
    )
    assert {"principal_id", "scope"} <= {r[1] for r in conn.execute("PRAGMA table_info(audit_events)")}
    assert {"rate_limit_hits", "auth_accounts", "revoked_tokens"} <= tables(conn)
    assert "on_behalf_of" in {r[1] for r in conn.execute("PRAGMA table_info(audit_events)")}
    conn.execute("INSERT INTO api_principals(principal_id,role,scopes) VALUES ('service:t','service','[]')")
    conn.execute("INSERT INTO api_principals VALUES ('merchant:c1','merchant','c1','d2',1,'[]')")
    conn.execute("INSERT INTO api_principals VALUES ('operator:op','operator',NULL,'d3',1,'[]')")
    conn.execute(
        "INSERT INTO api_sessions(session_id,token_digest,principal_id,created_at,expires_at) "
        "VALUES ('s2','t2','merchant:c1','a','b')"
    )
    assert migrate(conn, 8) == DOWN_TO_8
    # Rolling back drops what the 0008 schema cannot hold: merchant/operator principals and their sessions.
    assert [tuple(r) for r in conn.execute("SELECT principal_id FROM api_principals")] == [("demo:default",)]
    assert [tuple(r) for r in conn.execute("SELECT session_id FROM api_sessions")] == [("s1",)]
    assert not {"rate_limit_hits", "auth_accounts", "revoked_tokens"} & tables(conn)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    try:
        conn.execute("INSERT INTO api_principals VALUES ('merchant:c2','merchant','c2','d4',1)")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("0008 schema must refuse the merchant role")
    assert migrate(conn) == UP_FROM_8 and current_version(conn) == LATEST


def test_queue_part_of_0009_keeps_cases_and_messages(tmp_path):
    conn = connect(tmp_path / "queue.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    assert migrate(conn, 8) == DOWN_TO_8
    conn.execute(
        "INSERT INTO conversations (conversation_id, customer_id, state, created_at, updated_at) "
        "VALUES ('conv_legacy0001','cliente1988','handoff','t','t')"
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, request_id, role, text, tokens, created_at) "
        "VALUES ('conv_legacy0001','req_1','merchant','Quero um atendente',4,'t')"
    )
    conn.execute(
        "INSERT INTO handoff_cases (case_id, protocol, customer_id, idempotency_key, reason, payload, created_at, "
        "conversation_id) VALUES ('hc_legacy','SIM-20261026-ABCDEF','cliente1988','k1','customer_request','{}','t',"
        "'conv_legacy0001')"
    )
    assert migrate(conn) == UP_FROM_8
    row = conn.execute("SELECT * FROM handoff_cases WHERE case_id='hc_legacy'").fetchone()
    assert (row["protocol"], row["queue_state"], row["resume_count"], row["thread_id"]) == (
        "SIM-20261026-ABCDEF",
        "open",
        0,
        None,
    )
    assert {"handoff_events", "webhook_deliveries", "webhook_inbox"} <= tables(conn)
    assert {"event_id", "error"} <= {r[1] for r in conn.execute("PRAGMA table_info(webhook_deliveries)")}
    assert conn.execute("SELECT via FROM messages").fetchone()[0] is None
    conn.execute("INSERT INTO handoff_events VALUES ('hev_1','hc_legacy','approve','op_ana','key-00000001','{}','t')")
    try:
        conn.execute("INSERT INTO handoff_events VALUES ('hev_2','hc_legacy','reply','op_ana','key-00000001','{}','t')")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("the idempotency key must be unique")
    try:
        conn.execute("UPDATE handoff_cases SET queue_state='lost' WHERE case_id='hc_legacy'")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("queue_state must be checked")
    assert migrate(conn, 8) == DOWN_TO_8
    assert not {"handoff_events", "webhook_deliveries", "webhook_inbox"} & tables(conn)
    assert "queue_state" not in {r[1] for r in conn.execute("PRAGMA table_info(handoff_cases)")}
    assert conn.execute("SELECT protocol FROM handoff_cases").fetchone()[0] == "SIM-20261026-ABCDEF"
    assert conn.execute("SELECT text FROM messages").fetchone()[0] == "Quero um atendente"


# --- 0010 rollback: the outbox is the only copy of events not delivered yet ---------------------------------------


def add_outbox_row(conn, event_id, status, attempts=0, target="ticketing"):
    conn.execute(
        "INSERT INTO webhook_outbox (event_id,target,event,case_id,body,attempts,status) "
        "VALUES (?,?,'handoff.created','hc_1',?,?,?)",
        (event_id, target, f'{{"id":"{event_id}"}}', attempts, status),
    )


def outbox_rows(conn):
    return [tuple(row) for row in conn.execute("SELECT * FROM webhook_outbox ORDER BY event_id, target")]


def test_rollback_of_0010_is_refused_while_an_event_is_pending(tmp_path):
    conn = connect(tmp_path / "pending.sqlite3")
    add_outbox_row(conn, "evt_new", "pending")
    add_outbox_row(conn, "evt_retrying", "pending", attempts=2)
    add_outbox_row(conn, "evt_done", "delivered", attempts=1)
    with pytest.raises(RollbackRefused) as refused:
        migrate(conn, 9)
    message = str(refused.value)
    assert "2 event(s) not delivered (pending: 2)" in message and "Deliver them or resolve them" in message
    assert "delivered:" not in message


def test_rollback_of_0010_is_refused_while_an_event_has_failed(tmp_path):
    conn = connect(tmp_path / "failed.sqlite3")
    add_outbox_row(conn, "evt_exhausted", "failed", attempts=3)
    with pytest.raises(RollbackRefused) as refused:
        migrate(conn, 9)
    assert "1 event(s) not delivered (failed: 1)" in str(refused.value)


def test_refused_rollback_reports_each_state_and_leaves_the_database_as_it_was(tmp_path):
    conn = connect(tmp_path / "intact.sqlite3")
    seed(conn, FixedClock("2026-10-26T10:00:00"))
    add_outbox_row(conn, "evt_a", "pending", attempts=1)
    add_outbox_row(conn, "evt_b", "failed", attempts=3, target="merchant")
    add_outbox_row(conn, "evt_c", "rejected", attempts=1)
    add_outbox_row(conn, "evt_d", "delivered", attempts=1)
    before = outbox_rows(conn)
    for target in (9, 8, 0):  # a deeper rollback is refused at the same point, before any step is applied
        with pytest.raises(RollbackRefused) as refused:
            migrate(conn, target)
        assert "3 event(s) not delivered (failed: 1, pending: 1, rejected: 1)" in str(refused.value)
        assert current_version(conn) == LATEST
        assert outbox_rows(conn) == before
    assert {"webhook_outbox", "webhook_inbox", "conversations", "customers"} <= tables(conn)
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 2
    assert [row[0] for row in conn.execute("SELECT version FROM schema_version ORDER BY version")] == list(
        range(1, LATEST + 1)
    )
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_rollback_of_0010_with_an_empty_outbox_drops_the_table(tmp_path):
    conn = connect(tmp_path / "empty.sqlite3")
    assert migrate(conn, 9) == DOWN_TO_9
    assert "webhook_outbox" not in tables(conn) and current_version(conn) == 9


def test_rollback_of_0010_with_only_delivered_events_drops_the_table(tmp_path):
    conn = connect(tmp_path / "delivered.sqlite3")
    add_outbox_row(conn, "evt_a", "delivered", attempts=1)
    add_outbox_row(conn, "evt_a", "delivered", attempts=1, target="merchant")
    assert migrate(conn, 9) == DOWN_TO_9
    assert "webhook_outbox" not in tables(conn) and current_version(conn) == 9


def test_0010_comes_up_again_after_a_rollback(tmp_path):
    conn = connect(tmp_path / "again.sqlite3")
    add_outbox_row(conn, "evt_a", "delivered", attempts=1)
    assert migrate(conn, 9) == DOWN_TO_9
    assert migrate(conn) == UP_FROM_9
    assert current_version(conn) == LATEST and outbox_rows(conn) == []
    add_outbox_row(conn, "evt_b", "pending")
    assert [row[0] for row in conn.execute("SELECT event_id FROM webhook_outbox")] == ["evt_b"]


def test_rollback_goes_through_once_the_blocking_events_are_resolved(tmp_path):
    conn = connect(tmp_path / "resolved.sqlite3")
    add_outbox_row(conn, "evt_a", "pending")
    with pytest.raises(RollbackRefused):
        migrate(conn, 9)
    conn.execute("UPDATE webhook_outbox SET status='delivered', attempts=1")
    assert migrate(conn, 9) == DOWN_TO_9
    assert current_version(conn) == 9


def test_cli_migrate_refuses_the_rollback_with_a_clear_message(tmp_path, capsys):
    settings = Settings(_env_file=None, runtime_dir=tmp_path)
    conn = connect(settings.db_path)
    add_outbox_row(conn, "evt_a", "failed", attempts=3)
    conn.close()
    with pytest.raises(SystemExit) as refused:
        cli.cmd_migrate(settings, SimpleNamespace(to=9))
    assert "cannot roll back 0010_webhook_outbox" in str(refused.value) and "failed: 1" in str(refused.value)
    assert capsys.readouterr().out == ""
    conn = connect(settings.db_path)
    assert current_version(conn) == LATEST and len(outbox_rows(conn)) == 1
    conn.close()


# --- 0011: rubric columns of run_evaluations and the human calibrations ------------------------------------------


def columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def add_evaluation(conn, evaluation_id, *, rubric_version="2", result="{}", extra=""):
    conn.execute(
        "INSERT INTO run_evaluations (evaluation_id,request_id,principal_id,method,rubric,rubric_version,evaluator,"
        "config_digest,result,evidence,critical_failures,cost_usd,state,error,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            evaluation_id,
            "req_synthetic01",
            "cli:eval",
            "model",
            "judge",
            rubric_version,
            '{"model":"deepseek-flash","provider":"deepseek"}',
            f"digest-{evaluation_id}",
            result,
            "{}",
            "[]",
            0.001,
            "completed",
            None,
            "2026-11-04T10:00:00+00:00",
        ),
    )
    if extra:
        conn.execute(f"UPDATE run_evaluations SET {extra} WHERE evaluation_id=?", (evaluation_id,))


def add_calibration(conn, sample_id="S01", rater="owner", calibration_id=None):
    scores = '{"groundedness":4,"factual_correctness":5,"relevance":5,"usefulness":4}'
    conn.execute(
        "INSERT INTO calibrations (calibration_id,campaign,sample_id,case_id,request_id,evaluation_id,route,split,"
        "rater,rubric_version,scores,unsupported_claim,note,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            calibration_id or f"cal_{sample_id}_{rater}",
            "v080-qa",
            sample_id,
            "UC01",
            "req_synthetic01",
            "eval_v3",
            "knowledge",
            "dev",
            rater,
            "3",
            scores,
            0,
            None,
            "2026-11-04T12:00:00+00:00",
        ),
    )


def test_0011_adds_the_rubric_columns_and_the_calibrations_table(tmp_path):
    conn = connect(tmp_path / "rubric.sqlite3")
    assert {"rubric_version", "evaluator", "scores", "repetition", "unsupported_claim"} <= set(
        columns(conn, "run_evaluations")
    )
    assert "calibrations" in tables(conn)
    assert {"campaign", "sample_id", "rater", "scores", "unsupported_claim", "evaluation_id"} <= set(
        columns(conn, "calibrations")
    )


def v3_result(repetition, claim):
    return json.dumps(
        {
            "repetition": repetition,
            "groundedness": 5,
            "factual_correctness": 4,
            "relevance": 5,
            "usefulness": 3,
            "unsupported_claim": claim,
            "groundedness_reason": "Supported.",
        }
    )


def test_0011_round_trip_keeps_every_evaluation_and_rebuilds_the_columns_from_result(tmp_path):
    conn = connect(tmp_path / "evaluations.sqlite3")
    assert migrate(conn, 10) == ["down 0011_evaluation_rubric"]
    assert not {"scores", "repetition", "unsupported_claim"} & set(columns(conn, "run_evaluations"))
    add_evaluation(conn, "eval_v2", result='{"answers_question":4,"clarity_and_tone":4,"honesty":5,"comment":"ok"}')
    add_evaluation(conn, "eval_v3_a", rubric_version="3", result=v3_result(2, False))
    add_evaluation(conn, "eval_v3_b", rubric_version="3", result=v3_result(3, True))
    add_evaluation(conn, "eval_v3_failed", rubric_version="3", result='{"repetition": 4}')

    def state():
        return {
            r["evaluation_id"]: (r["repetition"], r["unsupported_claim"], r["scores"] and json.loads(r["scores"]))
            for r in conn.execute("SELECT * FROM run_evaluations")
        }

    scores = {"groundedness": 5, "factual_correctness": 4, "relevance": 5, "usefulness": 3}
    expected = {
        "eval_v2": (1, None, None),  # a judge.v2 row keeps the defaults
        "eval_v3_a": (2, 0, scores),
        "eval_v3_b": (3, 1, scores),
        "eval_v3_failed": (4, None, None),  # a failed judgement has no scores or verdict, only its repetition
    }
    assert migrate(conn) == ["up 0011_evaluation_rubric"]  # the upgrade rebuilds the columns from `result`
    assert state() == expected

    before = {r["evaluation_id"]: dict(r) for r in conn.execute("SELECT * FROM run_evaluations")}
    assert migrate(conn, 10) == ["down 0011_evaluation_rubric"]  # nothing is lost: result keeps the whole judgement
    assert not {"scores", "repetition", "unsupported_claim"} & set(columns(conn, "run_evaluations"))
    rows = {r["evaluation_id"]: r for r in conn.execute("SELECT * FROM run_evaluations")}
    assert set(rows) == set(expected) and rows["eval_v3_b"]["result"] == v3_result(3, True)
    assert rows["eval_v3_b"]["rubric_version"] == "3" and rows["eval_v3_b"]["evaluator"].count("deepseek") == 2
    assert "calibrations" not in tables(conn)

    assert migrate(conn) == ["up 0011_evaluation_rubric"] and current_version(conn) == LATEST
    assert state() == expected  # the repetition and the verdict came back with the second upgrade
    after = {r["evaluation_id"]: dict(r) for r in conn.execute("SELECT * FROM run_evaluations")}
    assert {k: v | {"scores": None} for k, v in after.items()} == {k: v | {"scores": None} for k, v in before.items()}
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_0011_checks_the_verdict_and_keeps_one_score_sheet_per_rater_and_sample(tmp_path):
    conn = connect(tmp_path / "checks.sqlite3")
    add_evaluation(conn, "eval_v3", rubric_version="3")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE run_evaluations SET unsupported_claim=2 WHERE evaluation_id='eval_v3'")
    add_calibration(conn)
    add_calibration(conn, rater="second")  # another rater of the same sample is allowed
    with pytest.raises(sqlite3.IntegrityError):  # the same rater cannot score a sample twice in one campaign
        add_calibration(conn, "S01", "owner", calibration_id="cal_duplicate")


def test_rollback_of_0011_is_refused_while_human_scores_exist_and_changes_nothing(tmp_path):
    conn = connect(tmp_path / "calibrated.sqlite3")
    add_evaluation(conn, "eval_v3", rubric_version="3", extra="repetition=3, unsupported_claim=1")
    add_calibration(conn, "S01")
    add_calibration(conn, "S02")
    for target in (10, 9, 0):  # a deeper rollback stops at the same point, before any step runs
        with pytest.raises(RollbackRefused) as refused:
            migrate(conn, target)
        assert "cannot roll back 0011_evaluation_rubric" in str(refused.value)
        assert "2 human score(s)" in str(refused.value)
        assert current_version(conn) == LATEST
    assert conn.execute("SELECT COUNT(*) FROM calibrations").fetchone()[0] == 2
    assert conn.execute("SELECT repetition, unsupported_claim FROM run_evaluations").fetchone()[:] == (3, 1)

    conn.execute("DELETE FROM calibrations")
    assert migrate(conn, 10) == ["down 0011_evaluation_rubric"]
    assert current_version(conn) == 10


def test_cli_migrate_refuses_the_0011_rollback_with_a_clear_message(tmp_path, capsys):
    settings = Settings(_env_file=None, runtime_dir=tmp_path)
    conn = connect(settings.db_path)
    add_calibration(conn)
    conn.close()
    with pytest.raises(SystemExit) as refused:
        cli.cmd_migrate(settings, SimpleNamespace(to=10))
    assert "cannot roll back 0011_evaluation_rubric" in str(refused.value) and "1 human score(s)" in str(refused.value)
    assert capsys.readouterr().out == ""
