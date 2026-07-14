#!/usr/bin/env python3
"""
CNPS PostgreSQL Demo Database — comprehensive dataset for full app testing.

Generates a large, realistic CNPS (Caisse Nationale de Prévoyance Sociale)
dataset directly in a PostgreSQL database (Supabase).

Features:
  - 14 Senegal regions, 50 employers, 5000 insured workers
  - 24 months of contributions with seasonal patterns and anomalies
  - Delinquent employers, sparse regions, duplicate rows for validation
  - Pension payments, AT/MP claims, social benefits
  - Pre-aggregated monthly summaries for fast dashboard queries

Usage:
  pip install psycopg2-binary
  set SUPABASE_DB_URL=postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
  python scripts/seed_cnps_postgres.py

  Or pass the URL as an argument:
  python scripts/seed_cnps_postgres.py --db-url "postgresql://..."
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, timedelta
from collections import defaultdict

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


# ── Configuration ──────────────────────────────────────────────────────────

REGIONS = [
    ("DK", "Dakar", "M. Amadou Ba"),
    ("TH", "Thiès", "M. Ousmane Sarr"),
    ("ZI", "Ziguinchor", "M. Claude Bassène"),
    ("SL", "Saint-Louis", "M. Ibrahima Sow"),
    ("KA", "Kaolack", "M. Moussa Ndiaye"),
    ("TG", "Tambacounda", "M. Boubacar Diallo"),
    ("KO", "Kolda", "M. Abdoulaye Fofana"),
    ("FO", "Fatick", "M. Mamadou Sy"),
    ("MB", "Mbour", "M. Cheikh Mbaye"),
    ("DB", "Diourbel", "M. Aliou Sow"),
    ("LO", "Louga", "M. Oumar Sy"),
    ("RG", "Rufisque", "M. Amadou Diop"),
    ("KE", "Kédougou", "M. Moussa Fall"),
    ("SE", "Sédhiou", "M. Babacar Sow"),
]

SECTORS = [
    "energy", "health", "education", "telecom", "industry",
    "agriculture", "transport", "finance", "construction",
    "public", "mining", "services", "tourism", "retail",
]

FIRST_NAMES = [
    "Jean", "Marie", "Paul", "Aminata", "Samuel", "Grace", "Eric", "Fatou",
    "Patrick", "Claire", "Ibrahim", "Rose", "Michel", "Awa", "Joseph",
    "Khady", "Pierre", " Ndèye", "Antoine", "Mariama", "Carlos", "Fatima",
    "Daniel", "Aïssatou", "François", "Oumou", "Guillaume", "Sokhna",
    "Alain", "Rama", "Olivier", "Degou", "Bernard", "Adama", "Thierry",
    "Binta", "André", "Khadija", "Laurent", "Coumba", "Emmanuel", "Daba",
    "Georges", "Nafissatou", "Michel", "Mariama", "Henri", "Awa", "David",
    "Aminata", "Marc", "Fatima", "Luc", "Ouleymatou", "Christian", "Khady",
]

LAST_NAMES = [
    "Nkomo", "Fouda", "Mbarga", "Tchoumi", "Essomba", "Ngassa", "Abena",
    "Kamga", "Mballa", "Onana", "Diallo", "Sow", "Fall", "Sy", "Ndiaye",
    "Ba", "Diop", "Gueye", "Sarr", "Fofana", "Touré", "Kone", "Cissé",
    "Traoré", "Konaté", "Keïta", "Diarra", "Sissoko", "Sidibé", "Dembélé",
    "Camara", "Bah", "Sako", "Kourouma", "Sylla", "Fadiga", "Dieng",
    "Bathily", "Mendy", "Niasse", "Diong", "Faye", "Sagna", "Ndao",
    "Gomis", "Seck", "Thiam", "Diouf", "Mbaye", "Bamba", "Sané",
]

EMPLOYERS = [
    ("EMP-4001", "Sonatel (Télécoms)", "DK", "telecom", 850),
    ("EMP-4002", "Senelec (Énergie)", "DK", "energy", 1200),
    ("EMP-4003", "CHU de Dakar", "DK", "health", 600),
    ("EMP-4004", "Université Cheikh Anta Diop", "DK", "education", 450),
    ("EMP-4005", "Société Bolloré Transport", "DK", "transport", 320),
    ("EMP-4006", "BCEAO (Siège Dakar)", "DK", "finance", 180),
    ("EMP-4007", "Ciments du Sahel", "TH", "industry", 400),
    ("EMP-4008", "SOTRACO", "TH", "transport", 250),
    ("EMP-4009", "Hôpital de Thiès", "TH", "health", 280),
    ("EMP-4010", "Tigo (Telecel)", "TH", "telecom", 150),
    ("EMP-4011", "Sucaf Sénégal", "KA", "agriculture", 350),
    ("EMP-4012", "SOS Sahel", "KA", "agriculture", 120),
    ("EMP-4013", "PMT Sénégal", "TG", "mining", 500),
    ("EMP-4014", "Société des Potasses", "TG", "mining", 280),
    ("EMP-4015", "Groupe Teranga", "DK", "tourism", 200),
    ("EMP-4016", "Entreprises en Difficulté SA", "FO", "industry", 90),
    ("EMP-4017", "Retardataires Industriels", "DB", "industry", 110),
    ("EMP-4018", "Paiements En Retard Ltd", "LO", "retail", 75),
    ("EMP-4019", "Port Autonome de Dakar", "DK", "transport", 380),
    ("EMP-4020", "GIE Casamance Agricole", "ZI", "agriculture", 160),
    ("EMP-4021", "Hôpital Républicain", "SL", "health", 310),
    ("EMP-4022", "Université Gaston Berger", "SL", "education", 200),
    ("EMP-4023", "Sene-Gaz", "MB", "energy", 140),
    ("EMP-4024", "Mairie de Mbour", "MB", "public", 95),
    ("EMP-4025", "Saham Assurances", "DK", "finance", 160),
    ("EMP-4026", "ENEA Engineering", "DK", "energy", 120),
    ("EMP-4027", "SODEFITEX", "ZI", "agriculture", 450),
    ("EMP-4028", "BTP Sen", "TH", "construction", 200),
    ("EMP-4029", "Karaté SARL", "FO", "services", 60),
    ("EMP-4030", "Société Minière de Kédougou", "KE", "mining", 350),
    ("EMP-4031", "Ferme Avicole du Sine", "KA", "agriculture", 180),
    ("EMP-4032", "CFAO Motors Sénégal", "DK", "retail", 90),
    ("EMP-4033", "Société des Eaux du Sénégal", "DK", "services", 280),
    ("EMP-4034", "Agrico Pastoral du Ferlo", "LO", "agriculture", 130),
    ("EMP-4035", "Pêcheries de Saint-Louis", "SL", "agriculture", 210),
    ("EMP-4036", "TOTAL Energies Sénégal", "DK", "energy", 170),
    ("EMP-4037", "Orange Money Sénégal", "DK", "finance", 130),
    ("EMP-4038", "SMT (Sénéchal)", "TH", "construction", 160),
    ("EMP-4039", "Bouygues Bâtiment", "DK", "construction", 220),
    ("EMP-4040", "Radisson Blu Dakar", "DK", "tourism", 140),
    ("EMP-4041", "Lycée Ferrer Diourbel", "DB", "education", 80),
    ("EMP-4042", "Moulin de Diourbel", "DB", "industry", 110),
    ("EMP-4043", "Coopérative Ndogou", "TG", "agriculture", 200),
    ("EMP-4044", "Sénégalaise des Phosphates", "LO", "mining", 260),
    ("EMP-4045", "West Africa Logistics", "MB", "transport", 150),
    ("EMP-4046", "Dakar Technopole", "DK", "services", 90),
    ("EMP-4047", "Hôpital de Ziguinchor", "ZI", "health", 180),
    ("EMP-4048", "Société sénégalaise de banque", "DK", "finance", 200),
    ("EMP-4049", "Compagnie Sucrière du Sénégal", "KA", "industry", 320),
    ("EMP-4050", "GIE Pêche Kassoum", "SE", "agriculture", 85),
]

# Delinquent employers — high overdue rate
DELINQUENT_CODES = {"EMP-4016", "EMP-4017", "EMP-4018"}

# Months of data
MONTHS = 24

# ── Helpers ────────────────────────────────────────────────────────────────

def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def rand_date_in_month(year: int, month: int) -> date:
    first = date(year, month, 1)
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return rand_date(first, last)


def chunked_insert(cursor, table: str, columns: list[str], rows: list[tuple], batch_size: int = 2000):
    """Insert rows in batches for performance."""
    placeholders = ", ".join(["%s"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        cursor.executemany(sql, batch)


# ── Schema ─────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
DROP TABLE IF EXISTS monthly_summaries CASCADE;
DROP TABLE IF EXISTS employer_expected_contributions CASCADE;
DROP TABLE IF EXISTS social_benefit_payments CASCADE;
DROP TABLE IF EXISTS at_mp_claims CASCADE;
DROP TABLE IF EXISTS pension_payments CASCADE;
DROP TABLE IF EXISTS contributions CASCADE;
DROP TABLE IF EXISTS beneficiaries CASCADE;
DROP TABLE IF EXISTS insured_workers CASCADE;
DROP TABLE IF EXISTS employers CASCADE;
DROP TABLE IF EXISTS regional_offices CASCADE;

CREATE TABLE regional_offices (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    director_name VARCHAR(150)
);

CREATE TABLE employers (
    id SERIAL PRIMARY KEY,
    employer_code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    regional_code VARCHAR(10) NOT NULL REFERENCES regional_offices(code),
    sector VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    registered_at DATE DEFAULT CURRENT_DATE
);

CREATE TABLE insured_workers (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    employer_id INTEGER NOT NULL REFERENCES employers(id),
    hire_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    gender VARCHAR(10),
    birth_date DATE
);

CREATE TABLE beneficiaries (
    id SERIAL PRIMARY KEY,
    beneficiary_id VARCHAR(20) NOT NULL UNIQUE,
    insured_worker_id INTEGER NOT NULL REFERENCES insured_workers(id),
    relationship VARCHAR(50),
    pension_start_date DATE,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE contributions (
    id SERIAL PRIMARY KEY,
    contribution_date DATE NOT NULL,
    contribution_amount NUMERIC(15,2) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    employer_id INTEGER NOT NULL REFERENCES employers(id),
    regional_code VARCHAR(10) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'paid',
    period_month VARCHAR(7) NOT NULL
);

CREATE TABLE pension_payments (
    id SERIAL PRIMARY KEY,
    payment_date DATE NOT NULL,
    pension_amount NUMERIC(15,2) NOT NULL,
    beneficiary_id VARCHAR(20) NOT NULL,
    regional_code VARCHAR(10) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'paid'
);

CREATE TABLE at_mp_claims (
    id SERIAL PRIMARY KEY,
    claim_date DATE NOT NULL,
    claim_status VARCHAR(20) DEFAULT 'open',
    employer_id INTEGER NOT NULL REFERENCES employers(id),
    employee_id VARCHAR(20) NOT NULL,
    regional_code VARCHAR(10) NOT NULL,
    severity VARCHAR(20),
    days_lost INTEGER DEFAULT 0,
    claim_amount NUMERIC(15,2)
);

CREATE TABLE social_benefit_payments (
    id SERIAL PRIMARY KEY,
    payment_date DATE NOT NULL,
    benefit_amount NUMERIC(15,2) NOT NULL,
    benefit_type VARCHAR(50),
    beneficiary_id VARCHAR(20),
    regional_code VARCHAR(10) NOT NULL
);

CREATE TABLE employer_expected_contributions (
    id SERIAL PRIMARY KEY,
    employer_id INTEGER NOT NULL REFERENCES employers(id),
    period_month VARCHAR(7) NOT NULL,
    expected_amount NUMERIC(15,2) NOT NULL,
    regional_code VARCHAR(10) NOT NULL
);

CREATE TABLE monthly_summaries (
    id SERIAL PRIMARY KEY,
    period_month VARCHAR(7) NOT NULL,
    regional_code VARCHAR(10),
    total_contributions NUMERIC(18,2),
    total_pensions NUMERIC(18,2),
    total_claims INTEGER,
    total_claim_amount NUMERIC(18,2),
    active_employers INTEGER,
    active_workers INTEGER,
    paid_rate NUMERIC(5,2),
    UNIQUE(period_month, regional_code)
);

CREATE INDEX idx_contrib_date ON contributions(contribution_date);
CREATE INDEX idx_contrib_region ON contributions(regional_code);
CREATE INDEX idx_contrib_period ON contributions(period_month);
CREATE INDEX idx_contrib_emp ON contributions(employer_id);
CREATE INDEX idx_pension_date ON pension_payments(payment_date);
CREATE INDEX idx_pension_region ON pension_payments(regional_code);
CREATE INDEX idx_claim_date ON at_mp_claims(claim_date);
CREATE INDEX idx_claim_region ON at_mp_claims(regional_code);
CREATE INDEX idx_workers_emp ON insured_workers(employer_id);
CREATE INDEX idx_workers_status ON insured_workers(status);
CREATE INDEX idx_expected_period ON employer_expected_contributions(period_month);
"""


# ── Data Generation ────────────────────────────────────────────────────────

def generate_data(conn, months=MONTHS):
    cur = conn.cursor()
    today = date.today()
    start = today - timedelta(days=30 * months)
    random.seed(42)

    print("Inserting regional offices...")
    for code, name, director in REGIONS:
        cur.execute(
            "INSERT INTO regional_offices (code, name, director_name) VALUES (%s, %s, %s)",
            (code, name, director),
        )

    print("Inserting employers...")
    employer_ids = {}
    employer_regions = {}
    employer_sector = {}
    for code, name, region, sector, headcount in EMPLOYERS:
        cur.execute(
            """INSERT INTO employers (employer_code, name, regional_code, sector, active, registered_at)
               VALUES (%s, %s, %s, %s, TRUE, %s) RETURNING id""",
            (code, name, region, sector, rand_date(start, today - timedelta(days=365))),
        )
        eid = cur.fetchone()[0]
        employer_ids[code] = eid
        employer_regions[code] = region
        employer_sector[code] = sector

    print("Generating 5000 insured workers...")
    workers = []
    for i in range(5000):
        emp_code = EMPLOYERS[i % len(EMPLOYERS)][0]
        eid = employer_ids[emp_code]
        worker_id = f"INS-{30000 + i}"
        hire = rand_date(start, today - timedelta(days=30))
        status = random.choices(["active", "terminated"], weights=[92, 8])[0]
        gender = random.choice(["M", "F"])
        bday = rand_date(date(1960, 1, 1), date(2002, 12, 31))
        workers.append((worker_id, random.choice(FIRST_NAMES).strip(), random.choice(LAST_NAMES).strip(),
                        eid, hire, status, gender, bday))

    chunked_insert(cur, "insured_workers",
                   ["employee_id", "first_name", "last_name", "employer_id", "hire_date", "status", "gender", "birth_date"],
                   workers)

    # Fetch back the integer PKs assigned to each worker
    cur.execute("SELECT id, employee_id FROM insured_workers")
    worker_pk_map = {row[1]: row[0] for row in cur.fetchall()}

    print("Generating 1200 beneficiaries...")
    active_workers = [w for w in workers if w[5] == "active"]
    beneficiaries = []
    for i in range(1200):
        w = random.choice(active_workers)
        ben_id = f"BEN-{5000 + i}"
        relationship = random.choice(["spouse", "survivor", "retiree", "child", "disabled"])
        pstart = rand_date(start, today)
        worker_pk = worker_pk_map.get(w[0])
        if worker_pk:
            beneficiaries.append((ben_id, worker_pk, relationship, pstart, "active"))

    chunked_insert(cur, "beneficiaries",
                   ["beneficiary_id", "insured_worker_id", "relationship", "pension_start_date", "status"],
                   beneficiaries)

    # ── Contributions ──────────────────────────────────────────────────────
    print("Generating 120,000+ contributions (this takes a minute)...")
    contrib_rows = []
    dup_worker = workers[0][0]
    dup_emp_id = workers[0][2]
    dup_period = today.strftime("%Y-%m")

    for m in range(months):
        month_date = start + timedelta(days=28 * m)
        year = month_date.year
        month = month_date.month
        period = f"{year}-{month:02d}"

        # Seasonal multiplier: lower in Jul-Aug, higher in Nov-Dec
        seasonal = 1.0
        if month in (7, 8):
            seasonal = 0.75
        elif month in (11, 12):
            seasonal = 1.3
        elif month in (1, 2):
            seasonal = 0.9

        for w in workers:
            emp_code = next(c for c, eid in employer_ids.items() if eid == w[2])
            region = employer_regions[emp_code]
            is_delinquent = emp_code in DELINQUENT_CODES

            # Skip some Tambacounda data in recent months (sparse anomaly)
            if region == "TG" and m >= months - 3:
                if random.random() < 0.7:
                    continue

            contrib_date = rand_date_in_month(year, month)
            if contrib_date > today:
                continue

            base_amount = random.uniform(35_000, 420_000) * seasonal
            amount = round(base_amount, 2)

            if is_delinquent:
                status = random.choices(["overdue", "pending", "paid"], weights=[55, 20, 25])[0]
            else:
                status = random.choices(["paid", "paid", "paid", "pending", "overdue"], weights=[70, 15, 5, 5, 5])[0]

            contrib_rows.append((contrib_date, amount, w[0], w[2], region, status, period))

    # Intentional duplicates for validation testing
    for _ in range(3):
        dup_date = today - timedelta(days=random.randint(1, 15))
        contrib_rows.append((dup_date, 99999.99, dup_worker, dup_emp_id, "DK", "paid", dup_period))

    chunked_insert(cur, "contributions",
                   ["contribution_date", "contribution_amount", "employee_id", "employer_id",
                    "regional_code", "payment_status", "period_month"],
                   contrib_rows)
    print(f"  -> Inserted {len(contrib_rows):,} contribution rows")

    # ── Pension Payments ───────────────────────────────────────────────────
    print("Generating 3000 pension payments...")
    pension_rows = []
    ben_ids = [b[0] for b in beneficiaries]
    for _ in range(3000):
        ben_id = random.choice(ben_ids)
        pay_date = rand_date(start, today)
        region = random.choice(REGIONS)[0]
        amount = round(random.uniform(55_000, 280_000), 2)
        pension_rows.append((pay_date, amount, ben_id, region, "paid"))

    chunked_insert(cur, "pension_payments",
                   ["payment_date", "pension_amount", "beneficiary_id", "regional_code", "payment_status"],
                   pension_rows)

    # ── AT/MP Claims ───────────────────────────────────────────────────────
    print("Generating 500 AT/MP claims...")
    claim_rows = []
    for _ in range(500):
        w = random.choice(workers)
        claim_date = rand_date(start, today)
        region = employer_regions.get(
            next((c for c, eid in employer_ids.items() if eid == w[2]), None), "DK"
        )
        status = random.choice(["open", "closed", "under_review", "settled"])
        severity = random.choices(["minor", "moderate", "severe"], weights=[50, 35, 15])[0]
        days_lost = random.randint(0, 180) if severity != "minor" else random.randint(0, 15)
        amount = round(random.uniform(75_000, 3_500_000), 2)
        claim_rows.append((claim_date, status, w[2], w[0], region, severity, days_lost, amount))

    chunked_insert(cur, "at_mp_claims",
                   ["claim_date", "claim_status", "employer_id", "employee_id",
                    "regional_code", "severity", "days_lost", "claim_amount"],
                   claim_rows)

    # ── Social Benefit Payments ────────────────────────────────────────────
    print("Generating 800 social benefit payments...")
    benefit_rows = []
    benefit_types = ["maternity", "family", "disability", "survivor", "orphan", "old_age"]
    for _ in range(800):
        pay_date = rand_date(start, today)
        amount = round(random.uniform(20_000, 150_000), 2)
        btype = random.choice(benefit_types)
        ben = random.choice(ben_ids) if ben_ids else None
        region = random.choice(REGIONS)[0]
        benefit_rows.append((pay_date, amount, btype, ben, region))

    chunked_insert(cur, "social_benefit_payments",
                   ["payment_date", "benefit_amount", "benefit_type", "beneficiary_id", "regional_code"],
                   benefit_rows)

    # ── Employer Expected Contributions ────────────────────────────────────
    print("Generating employer expected contributions...")
    expected_rows = []
    for emp_code, eid in employer_ids.items():
        region = employer_regions[emp_code]
        base = random.uniform(1_200_000, 8_000_000)
        for m in range(months):
            month_date = start + timedelta(days=28 * m)
            period = f"{month_date.year}-{month_date.month:02d}"
            expected_rows.append((eid, period, round(base, 2), region))

    chunked_insert(cur, "employer_expected_contributions",
                   ["employer_id", "period_month", "expected_amount", "regional_code"],
                   expected_rows)

    # ── Monthly Summaries ──────────────────────────────────────────────────
    print("Computing monthly summaries...")
    cur.execute("""
        INSERT INTO monthly_summaries (period_month, regional_code, total_contributions, total_pensions,
                                       total_claims, total_claim_amount, active_employers, active_workers, paid_rate)
        SELECT
            c.period_month,
            c.regional_code,
            SUM(c.contribution_amount),
            COALESCE(p.pension_total, 0),
            COALESCE(cl.claim_count, 0),
            COALESCE(cl.claim_total, 0),
            COUNT(DISTINCT c.employer_id),
            COUNT(DISTINCT c.employee_id),
            ROUND(100.0 * SUM(CASE WHEN c.payment_status = 'paid' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2)
        FROM contributions c
        LEFT JOIN (
            SELECT regional_code, DATE_TRUNC('month', payment_date)::date AS month_start,
                   SUM(pension_amount) AS pension_total
            FROM pension_payments
            GROUP BY 1, 2
        ) p ON p.regional_code = c.regional_code
            AND p.month_start = (TO_DATE(c.period_month || '-01', 'YYYY-MM-DD'))
        LEFT JOIN (
            SELECT regional_code, DATE_TRUNC('month', claim_date)::date AS month_start,
                   COUNT(*) AS claim_count, SUM(claim_amount) AS claim_total
            FROM at_mp_claims
            GROUP BY 1, 2
        ) cl ON cl.regional_code = c.regional_code
            AND cl.month_start = (TO_DATE(c.period_month || '-01', 'YYYY-MM-DD'))
        GROUP BY c.period_month, c.regional_code, p.pension_total, cl.claim_count, cl.claim_total
        ON CONFLICT (period_month, regional_code) DO NOTHING
    """)

    conn.commit()
    print("\nDone! All data inserted.")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed CNPS PostgreSQL demo database")
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL"),
                        help="PostgreSQL connection URL (or set SUPABASE_DB_URL env var)")
    parser.add_argument("--months", type=int, default=MONTHS, help="Months of data (default: 24)")
    args = parser.parse_args()

    if not args.db_url:
        print("ERROR: No database URL provided.")
        print("Set SUPABASE_DB_URL env var or pass --db-url argument.")
        print("\nExample:")
        print('  set SUPABASE_DB_URL=postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres')
        print("  python scripts/seed_cnps_postgres.py")
        sys.exit(1)

    months = args.months

    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(args.db_url)
        conn.autocommit = False
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        sys.exit(1)

    try:
        print("Creating schema...")
        cur = conn.cursor()
        cur.execute(SCHEMA_SQL)
        conn.commit()

        generate_data(conn, months=months)

        # Print summary
        cur = conn.cursor()
        tables = [
            "regional_offices", "employers", "insured_workers", "beneficiaries",
            "contributions", "pension_payments", "at_mp_claims",
            "social_benefit_payments", "employer_expected_contributions", "monthly_summaries",
        ]
        print("\n=== Dataset Summary ===")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            n = cur.fetchone()[0]
            print(f"  {t}: {n:,} rows")

        # Verify anomalies exist
        cur.execute("SELECT COUNT(*) FROM contributions WHERE payment_status = 'overdue'")
        overdue = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM contributions WHERE contribution_amount = 99999.99")
        dupes = cur.fetchone()[0]
        cur.execute("SELECT regional_code, COUNT(*) FROM contributions GROUP BY regional_code ORDER BY COUNT(*)")
        region_counts = cur.fetchall()

        print(f"\n=== Anomaly Verification ===")
        print(f"  Overdue contributions: {overdue:,}")
        print(f"  Duplicate test rows: {dupes}")
        print(f"  Regional distribution:")
        for rc, cnt in region_counts:
            print(f"    {rc}: {cnt:,}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
