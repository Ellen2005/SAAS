#!/usr/bin/env python3
"""
CNPS Large Oracle Demo Database — Production-scale testing dataset.

Generates: cnps_oracle_large.db (SQLite) or Oracle DDL/SQL scripts
- 8 years of historical data (2018-2026)
- 500+ employers across 10 regions
- 10,000+ insured workers
- 500,000+ contributions
- Realistic patterns: seasonal variations, economic trends, anomalies

Usage:
  python scripts/seed_oracle_cnps_large.py --output ./data/cnps_oracle_large.db
  python scripts/seed_oracle_cnps_large.py --oracle-script --output ./data/oracle_cnps_demo.sql
"""
from __future__ import annotations

import argparse
import os
import random
import sqlite3
from datetime import date, timedelta
from typing import List, Tuple

# Default output
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cnps_oracle_large.db",
)

# 10 Regions across Cameroon
REGIONS = [
    ("DOU", "Douala", "Littoral"),
    ("YAO", "Yaoundé", "Centre"),
    ("BUE", "Buéa", "Southwest"),
    ("GAR", "Garoua", "North"),
    ("BAF", "Bafoussam", "West"),
    ("NGA", "Ngaoundéré", "Adamawa"),
    ("MAR", "Maroua", "Far North"),
    ("BMD", "Bamenda", "Northwest"),
    ("EBL", "Ebolowa", "South"),
    ("BERT", "Bertoua", "East"),
]

# 500+ employers across sectors
EMPLOYER_SECTORS = [
    ("transport", 45),
    ("energy", 35),
    ("health", 40),
    ("education", 50),
    ("industry", 60),
    ("agriculture", 55),
    ("telecom", 20),
    ("finance", 30),
    ("construction", 40),
    ("public", 35),
    ("retail", 50),
    ("mining", 15),
    ("tourism", 25),
    ("manufacturing", 45),
    ("logistics", 30),
]

FIRST_NAMES = [
    "Jean", "Marie", "Paul", "Aminata", "Samuel", "Grace", "Eric", "Fatou", "Patrick", "Claire",
    "Ibrahim", "Rose", "Emmanuel", "Christine", "Joseph", "Marguerite", "André", "Jeanne", "Pierre", "Lucie",
    "François", "Catherine", "Michel", "Antoinette", "Bernard", "Thérèse", "Luc", "Monique", "Alain", "Suzanne",
    "Jean-Pierre", "Marie-Claire", "Paul-Emile", "Aminata", "Samuel", "Grace", "Eric", "Fatou", "Patrick", "Claire",
]

LAST_NAMES = [
    "Nkomo", "Fouda", "Mbarga", "Tchoumi", "Essomba", "Ngassa", "Abena", "Kamga", "Mballa", "Onana",
    "Ondoa", "Ewane", "Toko", "Mbia", "Nkoulou", "Atangana", "Mendomo", "Kouam", "Ngo", "Biya",
    "Fon", "Kechia", "Limbong", "Mukete", "Ndive", "Nembo", "Nkwi", "Sah", "Tanyi", "Wepngong",
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema with indexes for performance."""
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA cache_size = -64000;  -- 64MB cache

        -- Regional offices
        CREATE TABLE regional_offices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            province TEXT NOT NULL,
            director_name TEXT,
            established_date DATE
        );

        -- Employers (500+)
        CREATE TABLE employers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            sector TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            registered_at DATE,
            size_category TEXT,  -- SME, Medium, Large, Enterprise
            annual_revenue REAL,
            employee_count INTEGER
        );

        -- Insured workers (10,000+)
        CREATE TABLE insured_workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            hire_date DATE,
            status TEXT DEFAULT 'active',
            gender TEXT,
            birth_date DATE,
            position TEXT,
            salary REAL,
            contribution_class INTEGER
        );

        -- Beneficiaries (pensioners, spouses, survivors)
        CREATE TABLE beneficiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            beneficiary_id TEXT NOT NULL UNIQUE,
            insured_worker_id INTEGER NOT NULL REFERENCES insured_workers(id),
            relationship TEXT,
            pension_start_date DATE,
            status TEXT DEFAULT 'active',
            monthly_pension REAL
        );

        -- Contributions (500,000+ records)
        CREATE TABLE contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contribution_date DATE NOT NULL,
            contribution_amount REAL NOT NULL,
            employee_id TEXT NOT NULL,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            regional_code TEXT NOT NULL,
            payment_status TEXT DEFAULT 'paid',
            period_month TEXT NOT NULL,
            payment_method TEXT,
            reference_number TEXT
        );

        -- Pension payments
        CREATE TABLE pension_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date DATE NOT NULL,
            pension_amount REAL NOT NULL,
            beneficiary_id TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            payment_status TEXT DEFAULT 'paid',
            payment_method TEXT
        );

        -- AT/MP claims (workplace accidents)
        CREATE TABLE at_mp_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_date DATE NOT NULL,
            claim_status TEXT DEFAULT 'open',
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            employee_id TEXT NOT NULL,
            regional_code TEXT NOT NULL,
            severity TEXT,
            days_lost INTEGER DEFAULT 0,
            claim_amount REAL,
            medical_costs REAL,
            compensation_paid REAL
        );

        -- Social benefit payments
        CREATE TABLE social_benefit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date DATE NOT NULL,
            benefit_amount REAL NOT NULL,
            benefit_type TEXT,
            beneficiary_id TEXT,
            regional_code TEXT NOT NULL,
            approval_status TEXT DEFAULT 'approved'
        );

        -- Expected contributions for compliance tracking
        CREATE TABLE employer_expected_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_id INTEGER NOT NULL REFERENCES employers(id),
            period_month TEXT NOT NULL,
            expected_amount REAL NOT NULL,
            regional_code TEXT NOT NULL,
            calculated_at DATE
        );

        -- Indexes for performance
        CREATE INDEX idx_contrib_date ON contributions(contribution_date);
        CREATE INDEX idx_contrib_region ON contributions(regional_code);
        CREATE INDEX idx_contrib_employer ON contributions(employer_id);
        CREATE INDEX idx_contrib_period ON contributions(period_month);
        CREATE INDEX idx_pension_date ON pension_payments(payment_date);
        CREATE INDEX idx_claim_date ON at_mp_claims(claim_date);
        CREATE INDEX idx_claim_employer ON at_mp_claims(employer_id);
        CREATE INDEX idx_worker_employer ON insured_workers(employer_id);
        CREATE INDEX idx_worker_status ON insured_workers(status);
        CREATE INDEX idx_employer_region ON employers(regional_code);
        CREATE INDEX idx_employer_sector ON employers(sector);
    """)
    print("✓ Schema created with performance indexes")


def seed_large_dataset(conn: sqlite3.Connection, years: int = 8) -> None:
    """Generate large realistic dataset spanning multiple years."""
    today = date.today()
    start = date(2018, 1, 1)  # 8 years of data
    months = years * 12
    cur = conn.cursor()
    random.seed(42)  # Reproducible data

    print(f"\nGenerating {years} years of data ({start} to {today})...")

    # 1. Regional offices
    print("  → Seeding regional offices...")
    for code, name, province in REGIONS:
        cur.execute(
            "INSERT INTO regional_offices (code, name, province, director_name, established_date) VALUES (?, ?, ?, ?, ?)",
            (code, name, province, f"Dr. {random.choice(LAST_NAMES)}", "2010-01-01"),
        )

    # 2. Employers (500+)
    print("  → Seeding employers...")
    employer_ids = {}
    employer_codes = []
    emp_counter = 1000
    
    for sector, count in EMPLOYER_SECTORS:
        for i in range(count):
            emp_counter += 1
            code = f"EMP-{emp_counter}"
            region = random.choice(REGIONS)[0]
            name = generate_company_name(sector, i)
            
            # Size categories
            size_weights = [0.4, 0.35, 0.2, 0.05]  # SME, Medium, Large, Enterprise
            size = random.choices(["SME", "Medium", "Large", "Enterprise"], weights=size_weights)[0]
            
            # Revenue and employee count based on size
            if size == "SME":
                revenue = random.uniform(10_000_000, 100_000_000)
                emp_count = random.randint(10, 50)
            elif size == "Medium":
                revenue = random.uniform(100_000_000, 500_000_000)
                emp_count = random.randint(50, 200)
            elif size == "Large":
                revenue = random.uniform(500_000_000, 2_000_000_000)
                emp_count = random.randint(200, 1000)
            else:  # Enterprise
                revenue = random.uniform(2_000_000_000, 10_000_000_000)
                emp_count = random.randint(1000, 5000)

            cur.execute(
                """INSERT INTO employers 
                   (employer_code, name, regional_code, sector, active, registered_at, size_category, annual_revenue, employee_count)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                (code, name, region, sector, random_date(start, today), size, revenue, emp_count),
            )
            employer_ids[code] = cur.lastrowid
            employer_codes.append((code, employer_ids[code], region, sector))

    print(f"    ✓ Created {len(employer_ids)} employers")

    # 3. Insured workers (10,000+)
    print("  → Seeding insured workers...")
    workers = []
    worker_counter = 0
    
    for emp_code, eid, region, sector in employer_codes:
        # Get employer's employee count
        cur.execute("SELECT employee_count FROM employers WHERE id = ?", (eid,))
        emp_count = cur.fetchone()[0]
        
        # Create workers (80% of declared count for realism)
        num_workers = int(emp_count * random.uniform(0.7, 0.9))
        
        for _ in range(num_workers):
            worker_counter += 1
            emp_id = f"INS-{worker_counter:06d}"
            gender = random.choice(["M", "F"])
            birth_year = random.randint(1960, 2000)
            birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
            hire_year = random.randint(2018, 2024)
            hire_date = date(hire_year, random.randint(1, 12), random.randint(1, 28))
            
            # Position and salary based on sector
            if sector in ["finance", "telecom", "energy"]:
                position = random.choice(["Manager", "Senior", "Mid-level", "Junior"])
                salary = random.uniform(150_000, 800_000)
            elif sector in ["health", "education"]:
                position = random.choice(["Doctor", "Nurse", "Teacher", "Admin"])
                salary = random.uniform(80_000, 400_000)
            else:
                position = random.choice(["Worker", "Supervisor", "Technician", "Clerk"])
                salary = random.uniform(50_000, 250_000)
            
            contribution_class = random.randint(1, 6)
            
            cur.execute(
                """INSERT INTO insured_workers
                   (employee_id, first_name, last_name, employer_id, hire_date, status, gender, birth_date, position, salary, contribution_class)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (emp_id, random.choice(FIRST_NAMES), random.choice(LAST_NAMES), eid, hire_date.isoformat(),
                 gender, birth_date.isoformat(), position, salary, contribution_class),
            )
            workers.append((emp_id, eid, region, emp_code))

    print(f"    ✓ Created {len(workers):,} insured workers")

    # 4. Beneficiaries (pensioners)
    print("  → Seeding beneficiaries...")
    ben_ids = []
    for i, (emp_id, _, _) in enumerate(workers[:5000]):  # 50% of workers have beneficiaries
        ben_id = f"BEN-{i:06d}"
        relationship = random.choice(["spouse", "survivor", "retiree", "orphan"])
        pension_start = random_date(start, today - timedelta(days=365))
        monthly_pension = random.uniform(25_000, 150_000)
        
        cur.execute(
            """INSERT INTO beneficiaries
               (beneficiary_id, insured_worker_id, relationship, pension_start_date, status, monthly_pension)
               VALUES (?, (SELECT id FROM insured_workers WHERE employee_id = ?), ?, ?, 'active', ?)""",
            (ben_id, emp_id, relationship, pension_start.isoformat(), monthly_pension),
        )
        ben_ids.append(ben_id)

    print(f"    ✓ Created {len(ben_ids):,} beneficiaries")

    # 5. Expected contributions per employer per month
    print("  → Generating expected contributions...")
    for emp_code, eid, region, sector in employer_codes:
        for m in range(months):
            period = (start + timedelta(days=30 * m)).strftime("%Y-%m")
            
            # Base expected amount varies by sector and size
            cur.execute("SELECT size_category, employee_count FROM employers WHERE id = ?", (eid,))
            size, emp_count = cur.fetchone()
            
            base_per_worker = random.uniform(15_000, 45_000)
            expected = base_per_worker * emp_count * random.uniform(0.85, 1.15)
            
            cur.execute(
                """INSERT INTO employer_expected_contributions
                   (employer_id, period_month, expected_amount, regional_code, calculated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (eid, period, round(expected, 2), region, today.isoformat()),
            )

    print(f"    ✓ Created {len(employer_codes) * months:,} expected contributions")

    # 6. Contributions (500,000+ records with realistic patterns)
    print("  → Generating contributions (this may take a moment)...")
    contrib_count = 0
    
    for emp_id, eid, region, emp_code in workers:
        # Get employer sector for realistic contribution patterns
        cur.execute("SELECT sector FROM employers WHERE id = ?", (eid,))
        sector = cur.fetchone()[0]
        
        for m in range(months):
            contrib_date = start + timedelta(days=30 * m + random.randint(0, 15))
            if contrib_date > today:
                continue
            
            # Seasonal patterns
            month = contrib_date.month
            seasonal_factor = 1.0
            if month in [1, 2]:  # Low season (holidays)
                seasonal_factor = 0.7
            elif month in [6, 7, 8]:  # High season
                seasonal_factor = 1.3
            
            # Economic trend (growth over years)
            year_factor = 1.0 + (contrib_date.year - 2018) * 0.05
            
            # Base amount from worker's salary
            cur.execute("SELECT salary, contribution_class FROM insured_workers WHERE employee_id = ?", (emp_id,))
            salary, contrib_class = cur.fetchone()
            base_amount = (salary * 0.08) * contrib_class / 6  # ~8% contribution
            
            amount = base_amount * seasonal_factor * year_factor * random.uniform(0.9, 1.1)
            amount = round(amount, 2)
            
            # Payment status with realistic distribution
            if random.random() < 0.05:  # 5% overdue
                status = "overdue"
            elif random.random() < 0.10:  # 10% pending
                status = "pending"
            else:  # 85% paid
                status = "paid"
            
            period = contrib_date.strftime("%Y-%m")
            payment_method = random.choice(["bank_transfer", "mobile_money", "cash", "check"])
            ref_num = f"REF-{contrib_date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            cur.execute(
                """INSERT INTO contributions
                   (contribution_date, contribution_amount, employee_id, employer_id, regional_code, 
                    payment_status, period_month, payment_method, reference_number)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (contrib_date.isoformat(), amount, emp_id, eid, region, status, period, payment_method, ref_num),
            )
            contrib_count += 1

    print(f"    ✓ Created {contrib_count:,} contributions")

    # 7. Pension payments
    print("  → Generating pension payments...")
    pension_count = 0
    for ben_id in ben_ids:
        region = random.choice(REGIONS)[0]
        # Monthly pension for up to 5 years back
        for m in range(min(60, months)):
            pay_date = today - timedelta(days=30 * m + random.randint(1, 20))
            if pay_date < start:
                break
            
            # Get base pension amount
            cur.execute("SELECT monthly_pension FROM beneficiaries WHERE beneficiary_id = ?", (ben_id,))
            base_pension = cur.fetchone()[0]
            
            # Annual increase (3% per year)
            years_elapsed = (today - pay_date).days / 365
            pension_amount = base_pension * (1.03 ** years_elapsed)
            
            cur.execute(
                """INSERT INTO pension_payments
                   (payment_date, pension_amount, beneficiary_id, regional_code, payment_status, payment_method)
                   VALUES (?, ?, ?, ?, 'paid', ?)""",
                (pay_date.isoformat(), round(pension_amount, 2), ben_id, region, random.choice(["bank_transfer", "mobile_money"])),
            )
            pension_count += 1

    print(f"    ✓ Created {pension_count:,} pension payments")

    # 8. AT/MP claims (workplace accidents)
    print("  → Generating AT/MP claims...")
    claim_count = 0
    for _ in range(5000):
        emp_id, eid, region, emp_code = random.choice(workers)
        acc_date = random_date(start, today)
        severity = random.choices(["minor", "moderate", "severe"], weights=[0.6, 0.3, 0.1])[0]
        days_lost = random.randint(0, 120) if severity != "minor" else random.randint(0, 10)
        claim_amount = random.uniform(50_000, 2_000_000)
        medical_costs = claim_amount * random.uniform(0.3, 0.6)
        compensation = claim_amount * random.uniform(0.5, 0.8) if severity == "severe" else 0
        
        cur.execute(
            """INSERT INTO at_mp_claims
               (claim_date, claim_status, employer_id, employee_id, regional_code, severity, 
                days_lost, claim_amount, medical_costs, compensation_paid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (acc_date.isoformat(), random.choice(["closed", "closed", "closed", "under_review"]),
             eid, emp_id, region, severity, days_lost, claim_amount, medical_costs, compensation),
        )
        claim_count += 1

    print(f"    ✓ Created {claim_count:,} AT/MP claims")

    # 9. Social benefit payments
    print("  → Generating social benefits...")
    benefit_count = 0
    for _ in range(10000):
        pay_date = random_date(start, today)
        benefit_type = random.choice(["maternity", "family", "disability", "survivor", "old_age"])
        benefit_amount = random.uniform(15_000, 95_000)
        region = random.choice(REGIONS)[0]
        
        cur.execute(
            """INSERT INTO social_benefit_payments
               (payment_date, benefit_amount, benefit_type, beneficiary_id, regional_code, approval_status)
               VALUES (?, ?, ?, ?, ?, 'approved')""",
            (pay_date.isoformat(), benefit_amount, benefit_type, random.choice(ben_ids) if ben_ids and random.random() < 0.7 else None, region),
        )
        benefit_count += 1

    print(f"    ✓ Created {benefit_count:,} social benefit payments")

    conn.commit()
    print("\n✓ Large dataset generation complete!")


def generate_company_name(sector: str, index: int) -> str:
    """Generate realistic company names."""
    prefixes = {
        "transport": ["Trans", "Logi", "Transports", "Voyage"],
        "energy": ["Eneo", "Energie", "Power", "Electric"],
        "health": ["Hôpital", "Clinique", "Medical", "Santé"],
        "education": ["Université", "Collège", "Ecole", "Education"],
        "industry": ["Industrie", "Manufacturing", "Production", "Usine"],
        "agriculture": ["Agro", "Plantation", "Farming", "Agriculture"],
        "telecom": ["Telecom", "Mobile", "Communication", "Network"],
        "finance": ["Bank", "Finance", "Invest", "Capital"],
        "construction": ["Construction", "BTP", "Build", "Batiment"],
        "public": ["Mairie", "Gouvernement", "Public", "Municipal"],
        "retail": ["Supermarket", "Market", "Shop", "Retail"],
        "mining": ["Mining", "Extraction", "Mineral", "Resources"],
        "tourism": ["Hotel", "Tourism", "Resort", "Travel"],
        "manufacturing": ["Manufacturing", "Factory", "Production", "Industrie"],
        "logistics": ["Logistics", "Shipping", "Freight", "Transport"],
    }
    
    suffixes = ["Cameroon", "Cam", "SA", "Ltd", "Group", "Corp", "International", "Africa"]
    
    prefix = random.choice(prefixes.get(sector, ["Company"]))
    suffix = random.choice(suffixes)
    
    return f"{prefix} {suffix} {index}"


def random_date(start: date, end: date) -> str:
    """Generate random date between start and end."""
    delta = (end - start).days
    random_days = random.randint(0, max(delta, 1))
    return (start + timedelta(days=random_days)).isoformat()


def generate_oracle_sql(output_file: str, years: int = 8) -> None:
    """Generate Oracle SQL script for database creation and data insertion."""
    today = date.today()
    start = date(2018, 1, 1)
    months = years * 12
    
    with open(output_file, 'w') as f:
        f.write("""-- CNPS Large Oracle Demo Database
-- Generated for production-scale testing
-- 8 years of historical data (2018-2026)
-- 500+ employers, 10,000+ workers, 500,000+ contributions

-- Drop existing tables
BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE contributions CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE pension_payments CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE at_mp_claims CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE social_benefit_payments CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE beneficiaries CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE insured_workers CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE employer_expected_contributions CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE employers CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
   EXECUTE IMMEDIATE 'DROP TABLE regional_offices CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- Create tables
CREATE TABLE regional_offices (
    id NUMBER PRIMARY KEY,
    code VARCHAR2(10) NOT NULL UNIQUE,
    name VARCHAR2(100) NOT NULL,
    province VARCHAR2(50) NOT NULL,
    director_name VARCHAR2(100),
    established_date DATE
);

CREATE TABLE employers (
    id NUMBER PRIMARY KEY,
    employer_code VARCHAR2(20) NOT NULL UNIQUE,
    name VARCHAR2(200) NOT NULL,
    regional_code VARCHAR2(10) NOT NULL,
    sector VARCHAR2(50) NOT NULL,
    active NUMBER DEFAULT 1,
    registered_at DATE,
    size_category VARCHAR2(20),
    annual_revenue NUMBER(15,2),
    employee_count NUMBER
);

CREATE TABLE insured_workers (
    id NUMBER PRIMARY KEY,
    employee_id VARCHAR2(20) NOT NULL UNIQUE,
    first_name VARCHAR2(50) NOT NULL,
    last_name VARCHAR2(50) NOT NULL,
    employer_id NUMBER NOT NULL,
    hire_date DATE,
    status VARCHAR2(20) DEFAULT 'active',
    gender VARCHAR2(1),
    birth_date DATE,
    position VARCHAR2(50),
    salary NUMBER(10,2),
    contribution_class NUMBER
);

CREATE TABLE beneficiaries (
    id NUMBER PRIMARY KEY,
    beneficiary_id VARCHAR2(20) NOT NULL UNIQUE,
    insured_worker_id NUMBER NOT NULL,
    relationship VARCHAR2(20),
    pension_start_date DATE,
    status VARCHAR2(20) DEFAULT 'active',
    monthly_pension NUMBER(10,2)
);

CREATE TABLE contributions (
    id NUMBER PRIMARY KEY,
    contribution_date DATE NOT NULL,
    contribution_amount NUMBER(12,2) NOT NULL,
    employee_id VARCHAR2(20) NOT NULL,
    employer_id NUMBER NOT NULL,
    regional_code VARCHAR2(10) NOT NULL,
    payment_status VARCHAR2(20) DEFAULT 'paid',
    period_month VARCHAR2(7) NOT NULL,
    payment_method VARCHAR2(20),
    reference_number VARCHAR2(50)
);

CREATE TABLE pension_payments (
    id NUMBER PRIMARY KEY,
    payment_date DATE NOT NULL,
    pension_amount NUMBER(10,2) NOT NULL,
    beneficiary_id VARCHAR2(20) NOT NULL,
    regional_code VARCHAR2(10) NOT NULL,
    payment_status VARCHAR2(20) DEFAULT 'paid',
    payment_method VARCHAR2(20)
);

CREATE TABLE at_mp_claims (
    id NUMBER PRIMARY KEY,
    claim_date DATE NOT NULL,
    claim_status VARCHAR2(20) DEFAULT 'open',
    employer_id NUMBER NOT NULL,
    employee_id VARCHAR2(20) NOT NULL,
    regional_code VARCHAR2(10) NOT NULL,
    severity VARCHAR2(20),
    days_lost NUMBER DEFAULT 0,
    claim_amount NUMBER(12,2),
    medical_costs NUMBER(12,2),
    compensation_paid NUMBER(12,2)
);

CREATE TABLE social_benefit_payments (
    id NUMBER PRIMARY KEY,
    payment_date DATE NOT NULL,
    benefit_amount NUMBER(10,2) NOT NULL,
    benefit_type VARCHAR2(30),
    beneficiary_id VARCHAR2(20),
    regional_code VARCHAR2(10) NOT NULL,
    approval_status VARCHAR2(20) DEFAULT 'approved'
);

CREATE TABLE employer_expected_contributions (
    id NUMBER PRIMARY KEY,
    employer_id NUMBER NOT NULL,
    period_month VARCHAR2(7) NOT NULL,
    expected_amount NUMBER(12,2) NOT NULL,
    regional_code VARCHAR2(10) NOT NULL,
    calculated_at DATE
);

-- Indexes
CREATE INDEX idx_contrib_date ON contributions(contribution_date);
CREATE INDEX idx_contrib_region ON contributions(regional_code);
CREATE INDEX idx_contrib_employer ON contributions(employer_id);
CREATE INDEX idx_pension_date ON pension_payments(payment_date);
CREATE INDEX idx_claim_date ON at_mp_claims(claim_date);

-- Sequences
CREATE SEQUENCE seq_regional_offices START WITH 1;
CREATE SEQUENCE seq_employers START WITH 1;
CREATE SEQUENCE seq_insured_workers START WITH 1;
CREATE SEQUENCE seq_beneficiaries START WITH 1;
CREATE SEQUENCE seq_contributions START WITH 1;
CREATE SEQUENCE seq_pension_payments START WITH 1;
CREATE SEQUENCE seq_at_mp_claims START WITH 1;
CREATE SEQUENCE seq_social_benefits START WITH 1;
CREATE SEQUENCE seq_expected_contrib START WITH 1;

-- Note: Data insertion scripts would be generated here
-- Due to size, use the Python script to generate INSERT statements

COMMIT;
""")
    
    print(f"✓ Oracle SQL schema created: {output_file}")
    print(f"  → Use Python script to generate data: python scripts/seed_oracle_cnps_large.py --oracle-data")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate large CNPS demo dataset for Oracle")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output SQLite database path")
    parser.add_argument("--years", type=int, default=8, help="Number of years of data (default: 8)")
    parser.add_argument("--oracle-script", action="store_true", help="Generate Oracle SQL schema script")
    parser.add_argument("--oracle-data", action="store_true", help="Generate Oracle data insertion script")
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)

    if args.oracle_script:
        oracle_output = args.output.replace('.db', '_oracle_schema.sql')
        generate_oracle_sql(oracle_output, args.years)
        return

    # Generate SQLite database
    if os.path.exists(args.output):
        os.remove(args.output)
        print(f"Removed existing database: {args.output}")

    conn = sqlite3.connect(args.output)
    try:
        create_schema(conn)
        seed_large_dataset(conn, years=args.years)
        
        # Print summary
        tables = [
            "regional_offices", "employers", "insured_workers", "beneficiaries",
            "contributions", "pension_payments", "at_mp_claims",
            "social_benefit_payments", "employer_expected_contributions",
        ]
        print(f"\n{'='*60}")
        print(f"Database created: {os.path.abspath(args.output)}")
        print(f"{'='*60}")
        total_rows = 0
        for t in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            total_rows += n
            print(f"  {t:35s}: {n:>10,} rows")
        print(f"{'='*60}")
        print(f"  {'TOTAL':35s}: {total_rows:>10,} rows")
        print(f"{'='*60}\n")
        print(f"SQLite connection string:")
        print(f"  sqlite:///{os.path.abspath(args.output).replace(chr(92), '/')}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()