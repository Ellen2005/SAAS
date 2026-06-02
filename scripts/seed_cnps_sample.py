#!/usr/bin/env python3
"""
Seed a CNPS (Cameroon social security) sample SQLite database for demos and testing.

NOT the same as generate_cnps_db.py at repo root (Customer Net Promoter Score).

Usage:
  python scripts/seed_cnps_sample.py
  python scripts/seed_cnps_sample.py --output path/to/cnps_institutional_sample.db
"""
from __future__ import annotations

import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cnps_institutional_sample.db",
)

REGIONS = [
    ("DOU", "Douala"),
    ("YAO", "Yaoundé"),
    ("BUE", "Buéa"),
    ("GAR", "Garoua"),
    ("BAF", "Bafoussam"),
]

EMPLOYER_NAMES = [
    "Société Camerounaise de Transport",
    "Agro-Industries du Littoral",
    "Bâtiments et Travaux Publics CM",
    "Hôpital Central de Yaoundé",
    "Université de Douala",
    "Brasseries du Cameroun",
    "Société Nationale des Hydrocarbures",
    "Port Autonome de Douala",
    "Camtel",
    "Eneo Cameroon",
]

FIRST_NAMES = ["Jean", "Marie", "Paul", "Aminata", "Samuel", "Grace", "Eric", "Fatou", "Patrick", "Claire"]
LAST_NAMES = ["Nkomo", "Fouda", "Mbarga", "Tchoumi", "Essomba", "Biya", "Ngassa", "Abena", "Kamga", "Mballa"]


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS regional_offices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS employers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            sector TEXT,
            active INTEGER DEFAULT 1,
            registered_at DATE
        );

        CREATE TABLE IF NOT EXISTS insured_workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            hire_date DATE,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS beneficiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id TEXT NOT NULL UNIQUE,
            insured_worker_id INTEGER NOT NULL REFERENCES insured_workers(id),
            relationship TEXT,
            pension_start_date DATE,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contribution_date DATE NOT NULL,
            contribution_amount REAL NOT NULL,
            employee_id TEXT NOT NULL,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            regional_code TEXT NOT NULL,
            payment_status TEXT DEFAULT 'paid',
            period_month TEXT
        );

        CREATE TABLE IF NOT EXISTS pension_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date DATE NOT NULL,
            pension_amount REAL NOT NULL,
            beneficiary_id TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            payment_status TEXT DEFAULT 'paid'
        );

        CREATE TABLE IF NOT EXISTS workplace_accidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accident_date DATE NOT NULL,
            claim_status TEXT DEFAULT 'open',
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            employee_id TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            severity TEXT,
            days_lost INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_contributions_date ON contributions(contribution_date);
        CREATE INDEX IF NOT EXISTS idx_contributions_regional ON contributions(regional_code);
        CREATE INDEX IF NOT EXISTS idx_pension_date ON pension_payments(payment_date);
        CREATE INDEX IF NOT EXISTS idx_accidents_date ON workplace_accidents(accident_date);
        """
    )


def seed_data(conn: sqlite3.Connection, months: int = 12) -> None:
    today = date.today()
    start = today - timedelta(days=30 * months)
    cur = conn.cursor()

    for code, name in REGIONS:
        cur.execute(
            "INSERT OR IGNORE INTO regional_offices (code, name) VALUES (?, ?)",
            (code, name),
        )

    employer_ids: list[int] = []
    for i, ename in enumerate(EMPLOYER_NAMES):
        region = REGIONS[i % len(REGIONS)][0]
        cur.execute(
            """
            INSERT INTO employers (employer_code, name, regional_code, sector, active, registered_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (f"EMP-{1000 + i}", ename, region, random.choice(["public", "private", "para-public"]), _random_date(start, today)),
        )
        employer_ids.append(cur.lastrowid)

    worker_rows: list[tuple[str, int]] = []
    for i in range(120):
        eid = employer_ids[i % len(employer_ids)]
        emp_id = f"INS-{20000 + i}"
        cur.execute(
            """
            INSERT INTO insured_workers (employee_id, first_name, last_name, employer_id, hire_date, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            """,
            (
                emp_id,
                random.choice(FIRST_NAMES),
                random.choice(LAST_NAMES),
                eid,
                _random_date(start, today - timedelta(days=30)),
            ),
        )
        worker_rows.append((emp_id, eid))

    for i, (emp_id, _) in enumerate(worker_rows[:40]):
        cur.execute(
            """
            INSERT INTO beneficiaries (beneficiary_id, insured_worker_id, relationship, pension_start_date, status)
            VALUES (?, (SELECT id FROM insured_workers WHERE employee_id = ?), ?, ?, 'active')
            """,
            (f"BEN-{3000 + i}", emp_id, random.choice(["spouse", "survivor"]), _random_date(start, today)),
        )

    # Contributions — monthly per worker with some overdue
    for emp_id, eid in worker_rows:
        region = cur.execute(
            "SELECT regional_code FROM employers WHERE id = ?", (eid,)
        ).fetchone()[0]
        for m in range(months):
            contrib_date = start + timedelta(days=28 * m + random.randint(0, 10))
            if contrib_date > today:
                continue
            amount = round(random.uniform(15000, 450000), 2)
            status = random.choices(["paid", "paid", "paid", "overdue", "pending"], k=1)[0]
            cur.execute(
                """
                INSERT INTO contributions
                (contribution_date, contribution_amount, employee_id, employer_id, regional_code, payment_status, period_month)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contrib_date.isoformat(),
                    amount,
                    emp_id,
                    eid,
                    region,
                    status,
                    contrib_date.strftime("%Y-%m"),
                ),
            )

    # Pension payments
    ben_rows = cur.execute("SELECT beneficiary_id FROM beneficiaries").fetchall()
    for ben_id, in ben_rows:
        region = random.choice(REGIONS)[0]
        for m in range(min(months, 6)):
            pay_date = today - timedelta(days=30 * m + random.randint(1, 20))
            cur.execute(
                """
                INSERT INTO pension_payments (payment_date, pension_amount, beneficiary_id, regional_code, payment_status)
                VALUES (?, ?, ?, ?, 'paid')
                """,
                (pay_date.isoformat(), round(random.uniform(35000, 180000), 2), ben_id, region),
            )

    # Workplace accidents
    for _ in range(45):
        emp_id, eid = random.choice(worker_rows)
        region = cur.execute(
            "SELECT regional_code FROM employers WHERE id = ?", (eid,)
        ).fetchone()[0]
        acc_date = _random_date(start, today)
        cur.execute(
            """
            INSERT INTO workplace_accidents
            (accident_date, claim_status, employer_id, employee_id, regional_code, severity, days_lost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                acc_date.isoformat(),
                random.choice(["open", "closed", "under_review"]),
                eid,
                emp_id,
                region,
                random.choice(["minor", "moderate", "severe"]),
                random.randint(0, 90),
            ),
        )

    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed CNPS institutional sample SQLite database")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output .db path")
    parser.add_argument("--months", type=int, default=12, help="Months of contribution history")
    args = parser.parse_args()

    if os.path.exists(args.output):
        os.remove(args.output)

    conn = sqlite3.connect(args.output)
    try:
        create_schema(conn)
        seed_data(conn, months=args.months)
        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in (
                "regional_offices",
                "employers",
                "insured_workers",
                "beneficiaries",
                "contributions",
                "pension_payments",
                "workplace_accidents",
            )
        }
        print(f"Created {args.output}")
        for table, n in counts.items():
            print(f"  {table}: {n} rows")
        print("\nConnect in Settings using SQLite file path:")
        print(f"  sqlite:///{os.path.abspath(args.output)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
