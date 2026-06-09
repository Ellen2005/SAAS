#!/usr/bin/env python3
"""
CNPS Full Demo Database — end-to-end testing of every app feature.

Generates: cnps_full_demo.db (SQLite) at repo root by default.

Designed for:
  - Schema Explorer (domain purple tags, ready-to-run analyses)
  - ETL / KPI monitoring
  - Goal-driven Analysis presets
  - Semantic template field mapping
  - CNPS validation (staleness, duplicates, regional gaps)
  - Multi-region / employer compliance scenarios

Usage:
  python scripts/seed_cnps_full_demo.py
  python scripts/seed_cnps_full_demo.py --output ./data/cnps_full_demo.db
"""
from __future__ import annotations

import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

# Default output: project root (same level as scripts/ directory)
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cnps_full_demo.db",
)

REGIONS = [
    ("DOU", "Douala"),
    ("YAO", "Yaoundé"),
    ("BUE", "Buéa"),
    ("GAR", "Garoua"),
    ("BAF", "Bafoussam"),
    ("NGA", "Ngaoundéré"),
    ("MAR", "Maroua"),
    ("BMD", "Bamenda"),
]

EMPLOYERS = [
    ("EMP-1001", "Port Autonome de Douala", "DOU", "transport"),
    ("EMP-1002", "Eneo Cameroon", "DOU", "energy"),
    ("EMP-1003", "Hôpital Central de Yaoundé", "YAO", "health"),
    ("EMP-1004", "Université de Yaoundé I", "YAO", "education"),
    ("EMP-1005", "Brasseries du Cameroun", "DOU", "industry"),
    ("EMP-1006", "Société Nationale des Hydrocarbures", "YAO", "energy"),
    ("EMP-1007", "Camtel", "YAO", "telecom"),
    ("EMP-1008", "Plantations du Littoral", "BUE", "agriculture"),
    ("EMP-1009", "Cimencam", "BAF", "industry"),
    ("EMP-1010", "Mairie de Garoua", "GAR", "public"),
    ("EMP-1011", "Cotton Development Board", "MAR", "agriculture"),
    ("EMP-1012", "Bamenda General Hospital", "BMD", "health"),
    ("EMP-1013", "Agro-Industries du Centre", "NGA", "agriculture"),
    ("EMP-1014", "BTP Nord", "GAR", "construction"),
    ("EMP-1015", "Douala Stock Exchange Services", "DOU", "finance"),
    ("EMP-1016", "Late Payer Industries SA", "BAF", "industry"),  # mostly overdue
    ("EMP-1017", "Regional Test Employer", "BUE", "test"),
]

FIRST = ["Jean", "Marie", "Paul", "Aminata", "Samuel", "Grace", "Eric", "Fatou", "Patrick", "Claire", "Ibrahim", "Rose"]
LAST = ["Nkomo", "Fouda", "Mbarga", "Tchoumi", "Essomba", "Ngassa", "Abena", "Kamga", "Mballa", "Onana"]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE regional_offices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            director_name TEXT
        );

        CREATE TABLE employers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            sector TEXT,
            active INTEGER DEFAULT 1,
            registered_at DATE
        );

        CREATE TABLE insured_workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            hire_date DATE,
            status TEXT DEFAULT 'active',
            gender TEXT,
            birth_date DATE
        );

        CREATE TABLE beneficiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id TEXT NOT NULL UNIQUE,
            insured_worker_id INTEGER NOT NULL REFERENCES insured_workers(id),
            relationship TEXT,
            pension_start_date DATE,
            status TEXT DEFAULT 'active'
        );

        /* Domain tag: contribution */
        CREATE TABLE contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contribution_date DATE NOT NULL,
            contribution_amount REAL NOT NULL,
            employee_id TEXT NOT NULL,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            regional_code TEXT NOT NULL,
            payment_status TEXT DEFAULT 'paid',
            period_month TEXT NOT NULL
        );

        /* Domain tags: payment, pension */
        CREATE TABLE pension_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date DATE NOT NULL,
            pension_amount REAL NOT NULL,
            beneficiary_id TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            payment_status TEXT DEFAULT 'paid'
        );

        /* Domain tag: claim (AT/MP) */
        CREATE TABLE at_mp_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_date DATE NOT NULL,
            claim_status TEXT DEFAULT 'open',
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            employee_id TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            severity TEXT,
            days_lost INTEGER DEFAULT 0,
            claim_amount REAL
        );

        /* Domain tag: benefit, payment */
        CREATE TABLE social_benefit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date DATE NOT NULL,
            benefit_amount REAL NOT NULL,
            benefit_type TEXT,
            beneficiary_id TEXT,
            regional_code TEXT NOT NULL
        );

        /* For compliance / delinquent employer tests */
        CREATE TABLE employer_expected_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            period_month TEXT NOT NULL,
            expected_amount REAL NOT NULL,
            regional_code TEXT NOT NULL
        );

        CREATE INDEX idx_contrib_date ON contributions(contribution_date);
        CREATE INDEX idx_contrib_region ON contributions(regional_code);
        CREATE INDEX idx_pension_date ON pension_payments(payment_date);
        CREATE INDEX idx_claim_date ON at_mp_claims(claim_date);
        """
    )


def seed(conn: sqlite3.Connection, months: int = 18) -> None:
    today = date.today()
    start = today - timedelta(days=30 * months)
    cur = conn.cursor()
    random.seed(42)

    for code, name in REGIONS:
        cur.execute(
            "INSERT INTO regional_offices (code, name, director_name) VALUES (?, ?, ?)",
            (code, name, f"Director {name}"),
        )

    employer_ids = {}
    for code, name, region, sector in EMPLOYERS:
        cur.execute(
            """INSERT INTO employers (employer_code, name, regional_code, sector, active, registered_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (code, name, region, sector, _d(start, today)),
        )
        employer_ids[code] = cur.lastrowid

    workers: list[tuple[str, int, str]] = []
    for i in range(280):
        emp_key = EMPLOYERS[i % len(EMPLOYERS)][0]
        eid = employer_ids[emp_key]
        emp_id = f"INS-{30000 + i}"
        cur.execute(
            """INSERT INTO insured_workers
               (employee_id, first_name, last_name, employer_id, hire_date, status, gender, birth_date)
               VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
            (
                emp_id,
                random.choice(FIRST),
                random.choice(LAST),
                eid,
                _d(start, today - timedelta(days=60)),
                random.choice(["M", "F"]),
                _d(date(1965, 1, 1), date(2000, 12, 31)),
            ),
        )
        workers.append((emp_id, eid, EMPLOYERS[i % len(EMPLOYERS)][2]))

    for i, (emp_id, _, _) in enumerate(workers[:65]):
        cur.execute(
            """INSERT INTO beneficiaries (beneficiary_id, insured_worker_id, relationship, pension_start_date, status)
               VALUES (?, (SELECT id FROM insured_workers WHERE employee_id = ?), ?, ?, 'active')""",
            (f"BEN-{5000 + i}", emp_id, random.choice(["spouse", "survivor", "retiree"]), _d(start, today)),
        )

    # Expected contributions per employer per month
    for emp_key, eid in employer_ids.items():
        region = next(r for c, _, r, _ in EMPLOYERS if c == emp_key)
        for m in range(months):
            period = (start + timedelta(days=28 * m)).strftime("%Y-%m")
            cur.execute(
                """INSERT INTO employer_expected_contributions
                   (employer_id, period_month, expected_amount, regional_code)
                   VALUES (?, ?, ?, ?)""",
                (eid, period, round(random.uniform(800_000, 4_500_000), 2), region),
            )

    # Contributions — include overdue cluster for EMP-1016, one stale region (MAR sparse), one duplicate pair
    dup_emp = workers[0][0]
    dup_period = today.strftime("%Y-%m")
    for emp_id, eid, region in workers:
        emp_code = next(c for c, i in employer_ids.items() if i == eid)
        is_late_employer = emp_code == "EMP-1016"
        for m in range(months):
            contrib_date = start + timedelta(days=28 * m + random.randint(0, 12))
            if contrib_date > today:
                continue
            if region == "MAR" and m > months - 4:
                continue  # sparse recent data in Maroua
            amount = round(random.uniform(25_000, 380_000), 2)
            if is_late_employer:
                status = random.choices(["overdue", "pending", "paid"], weights=[5, 2, 1])[0]
            else:
                status = random.choices(["paid", "paid", "paid", "pending", "overdue"], weights=[6, 2, 1, 1, 1])[0]
            period = contrib_date.strftime("%Y-%m")
            cur.execute(
                """INSERT INTO contributions
                   (contribution_date, contribution_amount, employee_id, employer_id, regional_code, payment_status, period_month)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (contrib_date.isoformat(), amount, emp_id, eid, region, status, period),
            )

    # Intentional duplicate for validation test
    cur.execute(
        """INSERT INTO contributions
           (contribution_date, contribution_amount, employee_id, employer_id, regional_code, payment_status, period_month)
           VALUES (?, 99999, ?, ?, 'DOU', 'paid', ?)""",
        (today.isoformat(), dup_emp, employer_ids["EMP-1001"], dup_period),
    )
    cur.execute(
        """INSERT INTO contributions
           (contribution_date, contribution_amount, employee_id, employer_id, regional_code, payment_status, period_month)
           VALUES (?, 99999, ?, ?, 'DOU', 'paid', ?)""",
        (today.isoformat(), dup_emp, employer_ids["EMP-1001"], dup_period),
    )

    ben_ids = [r[0] for r in cur.execute("SELECT beneficiary_id FROM beneficiaries").fetchall()]
    for ben_id in ben_ids:
        region = random.choice(REGIONS)[0]
        for m in range(min(months, 10)):
            pay_date = today - timedelta(days=30 * m + random.randint(1, 20))
            cur.execute(
                """INSERT INTO pension_payments (payment_date, pension_amount, beneficiary_id, regional_code, payment_status)
                   VALUES (?, ?, ?, ?, 'paid')""",
                (pay_date.isoformat(), round(random.uniform(45_000, 220_000), 2), ben_id, region),
            )

    for _ in range(72):
        emp_id, eid, region = random.choice(workers)
        acc_date = _d(start, today)
        cur.execute(
            """INSERT INTO at_mp_claims
               (claim_date, claim_status, employer_id, employee_id, regional_code, severity, days_lost, claim_amount)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                acc_date,
                random.choice(["open", "closed", "under_review"]),
                eid,
                emp_id,
                region,
                random.choice(["minor", "moderate", "severe"]),
                random.randint(0, 120),
                round(random.uniform(50_000, 2_000_000), 2),
            ),
        )

    for _ in range(90):
        pay_date = _d(start, today)
        cur.execute(
            """INSERT INTO social_benefit_payments
               (payment_date, benefit_amount, benefit_type, beneficiary_id, regional_code)
               VALUES (?, ?, ?, ?, ?)""",
            (
                pay_date,
                round(random.uniform(15_000, 95_000), 2),
                random.choice(["maternity", "family", "disability", "survivor"]),
                random.choice(ben_ids) if ben_ids else None,
                random.choice(REGIONS)[0],
            ),
        )

    conn.commit()


def _d(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, max(delta, 1)))).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed CNPS full demo SQLite database")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--months", type=int, default=18)
    args = parser.parse_args()

    if os.path.exists(args.output):
        os.remove(args.output)

    conn = sqlite3.connect(args.output)
    try:
        create_schema(conn)
        seed(conn, months=args.months)
        tables = [
            "regional_offices", "employers", "insured_workers", "beneficiaries",
            "contributions", "pension_payments", "at_mp_claims",
            "social_benefit_payments", "employer_expected_contributions",
        ]
        print(f"Created {os.path.abspath(args.output)}\n")
        for t in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n:,} rows")
        print("\nSQLite connection string:")
        print(f"  sqlite:///{os.path.abspath(args.output).replace(chr(92), '/')}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
