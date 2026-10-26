"""Deterministic synthetic data, with every date relative to the injected clock.

`cliente1988` is the merchant used by the challenge examples. `cliente_demo_002` exists to test isolation.
All names, identifiers, amounts and codes are fictional.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, time, timedelta

from merchant_assistant.data.clock import Clock, add_business_days, today
from merchant_assistant.data.db import SYNTHETIC_TABLES

MAIN_CUSTOMER = "cliente1988"
OTHER_CUSTOMER = "cliente_demo_002"

RESPONSE_CODES = [
    ("05", "issuer_declined", "Transação não autorizada pelo banco emissor do cartão.",
     "Peça ao comprador para falar com o banco emissor ou usar outro meio de pagamento.", 0),
    ("51", "insufficient_funds", "Saldo ou limite insuficiente no cartão do comprador.",
     "Ofereça outro meio de pagamento, como outro cartão ou Pix.", 0),
    ("57", "not_permitted", "Transação não permitida para este cartão.",
     "Confirme se a bandeira e a modalidade estão habilitadas; se estiverem, peça outro meio de pagamento.", 0),
    ("91", "issuer_unavailable", "Emissor do cartão temporariamente indisponível.",
     "Aguarde alguns minutos e tente novamente.", 1),
]


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def seed(conn: sqlite3.Connection, clock: Clock) -> dict[str, int]:
    """Recreates all synthetic rows. Local handoff records are preserved."""
    now = clock.now()
    d0 = today(clock)
    tz = clock.tz

    def at(day_offset: int, hh: int, mm: int) -> datetime:
        return datetime.combine(d0 + timedelta(days=day_offset), time(hh, mm), tzinfo=tz)

    conn.execute("BEGIN")
    try:
        for table in SYNTHETIC_TABLES:
            conn.execute(f"DELETE FROM {table}")  # noqa: S608 - fixed table names

        conn.executemany("INSERT INTO response_codes VALUES (?,?,?,?,?)", RESPONSE_CODES)
        conn.executemany(
            "INSERT INTO customers VALUES (?,?,?)",
            [(MAIN_CUSTOMER, "Empório Exemplo 1988", "varejo"), (OTHER_CUSTOMER, "Loja Demo 002", "servicos")],
        )
        conn.executemany(
            "INSERT INTO contracts VALUES (?,?,?,?,?)",
            [
                (MAIN_CUSTOMER, json.dumps(["get_smart", "pix", "link_de_pagamento", "get_conta"]), "get_conta",
                 "debit_d1_credit_d2", (d0 - timedelta(days=400)).isoformat()),
                (OTHER_CUSTOMER, json.dumps(["get_classica", "get_tap", "pix"]), "bank_account",
                 "debit_d1_credit_d30", (d0 - timedelta(days=90)).isoformat()),
            ],
        )

        sales = [
            # sale_id, customer, captured_at, gross, payment_type, installments, channel, device
            ("sale_1988_0001", MAIN_CUSTOMER, at(-1, 9, 42), 15000, "debit", 1, "pos", "dev_1988_gs01"),
            ("sale_1988_0002", MAIN_CUSTOMER, at(-1, 13, 5), 120000, "credit", 1, "pos", "dev_1988_gs01"),
            ("sale_1988_0003", MAIN_CUSTOMER, at(-1, 17, 30), 8000, "pix", 1, "pos", "dev_1988_gs01"),
            ("sale_1988_0004", MAIN_CUSTOMER, at(-6, 11, 15), 50000, "credit", 1, "payment_link", None),
            ("sale_002_0001", OTHER_CUSTOMER, at(-1, 10, 0), 99000, "credit", 3, "pos", "dev_002_gc01"),
            ("sale_002_0002", OTHER_CUSTOMER, at(-1, 15, 20), 4500, "debit", 1, "get_tap", "dev_002_tap01"),
        ]
        conn.executemany(
            "INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?)",
            [(s[0], s[1], _iso(s[2]), s[3], "BRL", s[4], s[5], s[6], s[7]) for s in sales],
        )

        def receivable(rid, sale_id, customer, net, fee, expected, status):
            return (rid, sale_id, customer, net, fee, "BRL", expected.isoformat(), status)

        y = d0 - timedelta(days=1)
        receivables = [
            receivable("rcv_1988_0001", "sale_1988_0001", MAIN_CUSTOMER, 14806, 194, add_business_days(y, 1), "LOT_DONE"),
            receivable("rcv_1988_0002", "sale_1988_0002", MAIN_CUSTOMER, 116220, 3780, add_business_days(y, 2),
                       "LOT_DONE"),
            receivable("rcv_1988_0003", "sale_1988_0003", MAIN_CUSTOMER, 8000, 0, y, "SETTLED"),
            receivable("rcv_1988_0004", "sale_1988_0004", MAIN_CUSTOMER, 48425, 1575,
                       add_business_days(d0 - timedelta(days=6), 2), "SETTLED"),
            receivable("rcv_002_0001", "sale_002_0001", OTHER_CUSTOMER, 95436, 3564, y + timedelta(days=30), "LOT_DONE"),
            receivable("rcv_002_0002", "sale_002_0002", OTHER_CUSTOMER, 4441, 59, add_business_days(y, 1), "LOT_DONE"),
        ]
        conn.executemany("INSERT INTO receivables VALUES (?,?,?,?,?,?,?,?)", receivables)
        payouts = [
            ("rcv_1988_0001", "SCHEDULED", 0, None),
            ("rcv_1988_0002", "SCHEDULED", 0, None),
            ("rcv_1988_0003", "PAID", 1, _iso(at(-1, 17, 31))),
            ("rcv_1988_0004", "PAID", 1, _iso(at(-4, 8, 10))),
            ("rcv_002_0001", "SCHEDULED", 0, None),
            ("rcv_002_0002", "SCHEDULED", 0, None),
        ]
        conn.executemany("INSERT INTO payouts VALUES (?,?,?,?)", payouts)

        conn.executemany(
            "INSERT INTO devices VALUES (?,?,?,?,?,?,?)",
            [
                ("dev_1988_gs01", MAIN_CUSTOMER, "Get Smart", "wifi", "offline", _iso(now - timedelta(hours=3)),
                 json.dumps({"wifi_configured": True, "mobile_data": "available", "firmware": "demo-4.2"})),
                ("dev_002_gc01", OTHER_CUSTOMER, "Get Clássica", "chip_3g", "online",
                 _iso(now - timedelta(minutes=4)), json.dumps({"wifi_configured": False, "firmware": "demo-3.9"})),
                ("dev_002_tap01", OTHER_CUSTOMER, "Get Tap", "mobile", "online", _iso(now - timedelta(minutes=9)),
                 json.dumps({"android": "14"})),
            ],
        )

        events = [
            ("txn_1988_0101", MAIN_CUSTOMER, "dev_1988_gs01", now - timedelta(hours=3, minutes=10), 23000, "credit",
             "declined", "51"),
            ("txn_1988_0100", MAIN_CUSTOMER, "dev_1988_gs01", at(-3, 16, 2), 4590, "debit", "declined", "05"),
            ("txn_1988_0099", MAIN_CUSTOMER, "dev_1988_gs01", at(-1, 13, 5), 120000, "credit", "approved", "00"),
            ("txn_002_0201", OTHER_CUSTOMER, "dev_002_gc01", at(-1, 10, 0), 99000, "credit", "approved", "00"),
        ]
        conn.executemany(
            "INSERT INTO authorization_events VALUES (?,?,?,?,?,?,?,?,?)",
            [(e[0], e[1], e[2], _iso(e[3]), e[4], "BRL", e[5], e[6], e[7]) for e in events],
        )

        conn.executemany(
            "INSERT INTO support_cases VALUES (?,?,?,?,?,?,?,?)",
            [
                ("case_1988_001", MAIN_CUSTOMER, "device", "closed",
                 "Maquininha sem conexão Wi-Fi; reconfigurar a rede resolveu.",
                 json.dumps([{"step": "Reconfigurar o Wi-Fi da maquininha", "result": "resolveu"}]),
                 _iso(at(-60, 10, 0)), _iso(at(-60, 10, 25))),
                ("case_002_001", OTHER_CUSTOMER, "receivables", "open", "Dúvida sobre prazo de recebimento em 30 dias.",
                 json.dumps([]), _iso(at(-2, 9, 0)), None),
            ],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in SYNTHETIC_TABLES}  # noqa: S608
