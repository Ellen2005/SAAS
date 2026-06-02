#!/usr/bin/env python3
"""
CNPS Realistic Test Dataset Generator
Creates a dataset with real-world anomalies, errors, and data quality issues
to demonstrate how SAAS handles imperfect data and negative results
"""

import sqlite3
import random
import datetime
import os
from datetime import timedelta
import json

def create_realistic_cnps_database():
    """Create a realistic CNPS database with data quality issues and anomalies"""
    
    # Connect to database in scripts folder
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cnps_realistic_demo.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing tables
    tables = ['contributions', 'pension_payments', 'workplace_accidents', 'regional_offices', 'employers']
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    # Create tables
    cursor.execute('''
    CREATE TABLE regional_offices (
        id INTEGER PRIMARY KEY,
        code TEXT UNIQUE,
        name TEXT,
        region TEXT,
        manager_name TEXT,
        staff_count INTEGER,
        budget_allocated REAL,
        created_at TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE employers (
        id INTEGER PRIMARY KEY,
        employer_code TEXT,
        company_name TEXT,
        sector TEXT,
        employee_count INTEGER,
        regional_code TEXT,
        registration_date TEXT,
        status TEXT,
        last_payment_date TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE contributions (
        id INTEGER PRIMARY KEY,
        employer_id INTEGER,
        employee_ssn TEXT,
        employee_name TEXT,
        contribution_amount REAL,
        contribution_date TEXT,
        due_date TEXT,
        payment_status TEXT,
        regional_code TEXT,
        payment_method TEXT,
        late_fee REAL,
        created_at TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE pension_payments (
        id INTEGER PRIMARY KEY,
        beneficiary_ssn TEXT,
        beneficiary_name TEXT,
        pension_amount REAL,
        payment_date TEXT,
        payment_status TEXT,
        regional_code TEXT,
        processing_days INTEGER,
        rejection_reason TEXT,
        created_at TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE workplace_accidents (
        id INTEGER PRIMARY KEY,
        employee_ssn TEXT,
        employee_name TEXT,
        employer_id INTEGER,
        accident_date TEXT,
        accident_type TEXT,
        severity TEXT,
        claim_amount REAL,
        claim_status TEXT,
        regional_code TEXT,
        processing_days INTEGER,
        rejection_reason TEXT,
        created_at TEXT
    )
    ''')
    
    # Insert regional offices
    regional_offices = [
        ('YAO', 'Yaoundé', 'Centre', 'Marie Nguema', 25, 150000, '2020-01-01'),
        ('DLA', 'Douala', 'Littoral', 'Paul Mbarga', 30, 200000, '2020-01-01'),
        ('BAF', 'Bafoussam', 'Ouest', 'Jean Kamga', 18, 120000, '2020-01-01'),
        ('GAR', 'Garoua', 'Nord', 'Ahmadou Bello', 15, 100000, '2020-01-01'),
        ('BMD', 'Bamenda', 'Nord-Ouest', 'Grace Fon', 12, 80000, '2020-01-01'),
        ('BUE', 'Buea', 'Sud-Ouest', 'John Epie', 14, 90000, '2020-01-01'),
        ('BER', 'Bertoua', 'Est', 'Claude Atangana', 10, 70000, '2020-01-01'),
        ('MAR', 'Maroua', 'Extrême-Nord', 'Fatima Moussa', 16, 85000, '2020-01-01'),
        ('EVD', 'Ebolowa', 'Sud', 'Pierre Mvondo', 8, 60000, '2020-01-01'),
        ('KRI', 'Kribi', 'Sud', 'Anne Biyaga', 6, 50000, '2020-01-01')
    ]
    
    for i, (code, name, region, manager, staff, budget, created) in enumerate(regional_offices):
        cursor.execute('''
        INSERT INTO regional_offices (code, name, region, manager_name, staff_count, budget_allocated, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, region, manager, staff, budget, created))
    
    # Insert employers with realistic issues
    employers_data = []
    sectors = ['Manufacturing', 'Services', 'Agriculture', 'Mining', 'Construction', 'Education', 'Healthcare', 'Banking']
    statuses = ['active', 'suspended', 'inactive', 'delinquent']
    
    for i in range(500):
        regional_code = random.choice([r[0] for r in regional_offices])
        sector = random.choice(sectors)
        
        # Introduce data quality issues
        if random.random() < 0.05:  # 5% missing company names
            company_name = None
        else:
            company_name = f"{sector} Company {i+1}"
        
        if random.random() < 0.03:  # 3% invalid employee counts
            employee_count = random.choice([-1, 0, None, 99999])
        else:
            employee_count = random.randint(5, 500)
        
        # Some employers have suspicious patterns
        if random.random() < 0.1:  # 10% problematic employers
            status = 'delinquent'
            last_payment = (datetime.datetime.now() - timedelta(days=random.randint(90, 365))).strftime('%Y-%m-%d')
        else:
            status = random.choice(statuses)
            last_payment = (datetime.datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        
        employers_data.append((
            f"EMP{i+1:04d}",
            company_name,
            sector,
            employee_count,
            regional_code,
            (datetime.datetime.now() - timedelta(days=random.randint(30, 1095))).strftime('%Y-%m-%d'),
            status,
            last_payment
        ))
    
    cursor.executemany('''
    INSERT INTO employers (employer_code, company_name, sector, employee_count, regional_code, registration_date, status, last_payment_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', employers_data)
    
    # Insert contributions with realistic anomalies
    contributions_data = []
    payment_statuses = ['paid', 'overdue', 'pending', 'rejected', 'partial']
    payment_methods = ['bank_transfer', 'cash', 'check', 'mobile_money']
    
    # Get employer IDs
    cursor.execute('SELECT id, regional_code, employee_count FROM employers')
    employers = cursor.fetchall()
    
    for month_offset in range(12):  # Last 12 months
        base_date = datetime.datetime.now() - timedelta(days=30 * month_offset)
        
        for employer_id, regional_code, emp_count in employers:
            if emp_count is None or emp_count <= 0:
                continue
                
            # Generate contributions for this employer this month
            num_contributions = random.randint(1, min(emp_count or 10, 50))
            
            for contrib in range(num_contributions):
                contrib_date = base_date - timedelta(days=random.randint(0, 28))
                due_date = contrib_date + timedelta(days=30)
                
                # Introduce realistic anomalies
                if random.random() < 0.15:  # 15% payment issues
                    payment_status = random.choice(['overdue', 'rejected', 'partial'])
                    
                    # Overdue payments have escalating late fees
                    if payment_status == 'overdue':
                        days_overdue = (datetime.datetime.now() - due_date).days
                        late_fee = max(0, days_overdue * 500)  # 500 FCFA per day
                    else:
                        late_fee = 0
                else:
                    payment_status = 'paid'
                    late_fee = 0
                
                # Contribution amount anomalies
                if random.random() < 0.05:  # 5% suspicious amounts
                    contribution_amount = random.choice([0, -1000, 999999, None])
                elif regional_code == 'YAO' and random.random() < 0.3:  # Yaoundé has inflation issues
                    contribution_amount = random.uniform(25000, 45000)  # Higher than normal
                elif regional_code in ['KRI', 'EVD'] and random.random() < 0.4:  # Smaller offices struggle
                    contribution_amount = random.uniform(5000, 15000)  # Lower than normal
                else:
                    contribution_amount = random.uniform(15000, 25000)  # Normal range
                
                # Employee data quality issues
                if random.random() < 0.02:  # 2% missing SSN
                    employee_ssn = None
                    employee_name = f"Unknown Employee {contrib}"
                else:
                    employee_ssn = f"SSN{employer_id}{contrib:03d}"
                    employee_name = f"Employee {contrib} - Employer {employer_id}"
                
                contributions_data.append((
                    employer_id,
                    employee_ssn,
                    employee_name,
                    contribution_amount,
                    contrib_date.strftime('%Y-%m-%d'),
                    due_date.strftime('%Y-%m-%d'),
                    payment_status,
                    regional_code,
                    random.choice(payment_methods),
                    late_fee,
                    contrib_date.strftime('%Y-%m-%d %H:%M:%S')
                ))
    
    cursor.executemany('''
    INSERT INTO contributions (employer_id, employee_ssn, employee_name, contribution_amount, 
                             contribution_date, due_date, payment_status, regional_code, 
                             payment_method, late_fee, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', contributions_data)
    
    # Insert pension payments with processing issues
    pension_data = []
    pension_statuses = ['paid', 'pending', 'rejected', 'under_review']
    rejection_reasons = [
        'Incomplete documentation',
        'Age verification failed',
        'Contribution period insufficient',
        'Duplicate claim',
        'System error',
        None
    ]
    
    for i in range(2000):
        payment_date = datetime.datetime.now() - timedelta(days=random.randint(0, 365))
        
        # Processing time anomalies
        if random.random() < 0.2:  # 20% have processing delays
            processing_days = random.randint(45, 120)  # Excessive delays
            status = random.choice(['pending', 'under_review'])
        elif random.random() < 0.15:  # 15% rejected
            processing_days = random.randint(5, 30)
            status = 'rejected'
        else:
            processing_days = random.randint(1, 21)  # Normal processing
            status = 'paid'
        
        # Pension amount anomalies
        regional_code = random.choice([r[0] for r in regional_offices])
        if status == 'rejected':
            pension_amount = 0
        elif random.random() < 0.05:  # 5% suspicious amounts
            pension_amount = random.choice([999999, -5000, None])
        elif regional_code in ['YAO', 'DLA']:  # Urban areas have higher pensions
            pension_amount = random.uniform(80000, 150000)
        else:
            pension_amount = random.uniform(45000, 85000)
        
        rejection_reason = None
        if status == 'rejected':
            rejection_reason = random.choice([r for r in rejection_reasons if r is not None])
        
        pension_data.append((
            f"SSN{i+10000}",
            f"Pensioner {i+1}",
            pension_amount,
            payment_date.strftime('%Y-%m-%d'),
            status,
            regional_code,
            processing_days,
            rejection_reason,
            payment_date.strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    cursor.executemany('''
    INSERT INTO pension_payments (beneficiary_ssn, beneficiary_name, pension_amount, payment_date,
                                payment_status, regional_code, processing_days, rejection_reason, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', pension_data)
    
    # Insert workplace accidents with claim issues
    accident_data = []
    accident_types = ['Fall', 'Cut', 'Burn', 'Machinery', 'Chemical', 'Vehicle', 'Lifting', 'Other']
    severities = ['Minor', 'Moderate', 'Severe', 'Fatal']
    claim_statuses = ['approved', 'rejected', 'pending', 'under_investigation']
    
    for i in range(800):
        accident_date = datetime.datetime.now() - timedelta(days=random.randint(0, 730))
        
        # Claim processing anomalies
        severity = random.choice(severities)
        if severity == 'Fatal':
            claim_amount = random.uniform(2000000, 5000000)  # High claims
            processing_days = random.randint(60, 180)  # Long processing
            status = random.choice(['approved', 'under_investigation'])
        elif severity == 'Severe':
            claim_amount = random.uniform(500000, 2000000)
            processing_days = random.randint(30, 90)
            status = random.choice(claim_statuses)
        else:
            claim_amount = random.uniform(50000, 500000)
            processing_days = random.randint(5, 45)
            status = random.choice(claim_statuses)
        
        # Regional bias in claim approvals (realistic issue)
        regional_code = random.choice([r[0] for r in regional_offices])
        if regional_code in ['KRI', 'EVD', 'BER'] and random.random() < 0.4:  # Smaller offices have higher rejection rates
            status = 'rejected'
            claim_amount = 0
        
        # Data quality issues
        if random.random() < 0.03:  # 3% missing employee data
            employee_ssn = None
            employee_name = "Unknown Employee"
        else:
            employee_ssn = f"SSN{i+20000}"
            employee_name = f"Accident Victim {i+1}"
        
        rejection_reason = None
        if status == 'rejected':
            rejection_reason = random.choice([
                'Insufficient evidence',
                'Not work-related',
                'Late reporting',
                'Pre-existing condition',
                'Fraudulent claim'
            ])
        
        accident_data.append((
            employee_ssn,
            employee_name,
            random.randint(1, 500),  # employer_id
            accident_date.strftime('%Y-%m-%d'),
            random.choice(accident_types),
            severity,
            claim_amount,
            status,
            regional_code,
            processing_days,
            rejection_reason,
            accident_date.strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    cursor.executemany('''
    INSERT INTO workplace_accidents (employee_ssn, employee_name, employer_id, accident_date,
                                   accident_type, severity, claim_amount, claim_status,
                                   regional_code, processing_days, rejection_reason, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', accident_data)
    
    conn.commit()
    conn.close()
    
    print("[OK] Realistic CNPS database created: cnps_realistic_demo.db")
    print("\nDataset includes:")
    print("- 10 Regional offices with varying performance")
    print("- 500 Employers (some delinquent, some with data issues)")
    print("- ~15,000 Contributions (15% payment issues, amount anomalies)")
    print("- 2,000 Pension payments (20% delays, 15% rejections)")
    print("- 800 Workplace accidents (regional bias, processing issues)")
    print("\nData Quality Issues Included:")
    print("- Missing/null values in critical fields")
    print("- Negative and suspicious amounts")
    print("- Processing delays and bottlenecks")
    print("- Regional performance disparities")
    print("- High rejection rates in certain areas")
    print("- Late payments and escalating fees")
    print("- System errors and data inconsistencies")

def generate_data_quality_report():
    """Generate a report showing the data quality issues in the dataset"""
    
    conn = sqlite3.connect('cnps_realistic_demo.db')
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("DATA QUALITY ISSUES REPORT")
    print("="*60)
    
    # Contribution issues
    print("\nCONTRIBUTION ANOMALIES:")
    
    cursor.execute("SELECT COUNT(*) FROM contributions WHERE contribution_amount <= 0 OR contribution_amount IS NULL")
    invalid_amounts = cursor.fetchone()[0]
    print(f"- Invalid contribution amounts: {invalid_amounts}")
    
    cursor.execute("SELECT COUNT(*) FROM contributions WHERE payment_status = 'overdue'")
    overdue = cursor.fetchone()[0]
    print(f"- Overdue payments: {overdue}")
    
    cursor.execute("SELECT COUNT(*) FROM contributions WHERE employee_ssn IS NULL")
    missing_ssn = cursor.fetchone()[0]
    print(f"- Missing employee SSNs: {missing_ssn}")
    
    cursor.execute("SELECT SUM(late_fee) FROM contributions WHERE late_fee > 0")
    total_late_fees = cursor.fetchone()[0] or 0
    print(f"- Total late fees accumulated: {total_late_fees:,.0f} FCFA")
    
    # Regional performance disparities
    print("\nREGIONAL PERFORMANCE ISSUES:")
    
    cursor.execute('''
    SELECT regional_code, 
           COUNT(*) as total_contributions,
           SUM(CASE WHEN payment_status = 'overdue' THEN 1 ELSE 0 END) as overdue_count,
           ROUND(SUM(CASE WHEN payment_status = 'overdue' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as overdue_rate
    FROM contributions 
    GROUP BY regional_code 
    ORDER BY overdue_rate DESC
    ''')
    
    regional_performance = cursor.fetchall()
    print("Regional Overdue Rates:")
    for region, total, overdue, rate in regional_performance:
        print(f"  {region}: {rate}% overdue ({overdue}/{total})")
    
    # Pension processing issues
    print("\nPENSION PROCESSING PROBLEMS:")
    
    cursor.execute("SELECT COUNT(*) FROM pension_payments WHERE payment_status = 'rejected'")
    rejected_pensions = cursor.fetchone()[0]
    print(f"- Rejected pension claims: {rejected_pensions}")
    
    cursor.execute("SELECT AVG(processing_days) FROM pension_payments WHERE payment_status = 'paid'")
    avg_processing = cursor.fetchone()[0] or 0
    print(f"- Average processing time: {avg_processing:.1f} days")
    
    cursor.execute("SELECT COUNT(*) FROM pension_payments WHERE processing_days > 30")
    delayed_pensions = cursor.fetchone()[0]
    print(f"- Claims taking >30 days: {delayed_pensions}")
    
    # Workplace accident claim issues
    print("\nWORKPLACE ACCIDENT CLAIM ISSUES:")
    
    cursor.execute("SELECT COUNT(*) FROM workplace_accidents WHERE claim_status = 'rejected'")
    rejected_claims = cursor.fetchone()[0]
    print(f"- Rejected accident claims: {rejected_claims}")
    
    cursor.execute('''
    SELECT regional_code, 
           COUNT(*) as total_claims,
           SUM(CASE WHEN claim_status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
           ROUND(SUM(CASE WHEN claim_status = 'rejected' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as rejection_rate
    FROM workplace_accidents 
    GROUP BY regional_code 
    ORDER BY rejection_rate DESC
    ''')
    
    accident_performance = cursor.fetchall()
    print("Regional Claim Rejection Rates:")
    for region, total, rejected, rate in accident_performance:
        print(f"  {region}: {rate}% rejected ({rejected}/{total})")
    
    # Employer compliance issues
    print("\nEMPLOYER COMPLIANCE PROBLEMS:")
    
    cursor.execute("SELECT COUNT(*) FROM employers WHERE status = 'delinquent'")
    delinquent_employers = cursor.fetchone()[0]
    print(f"- Delinquent employers: {delinquent_employers}")
    
    cursor.execute("SELECT COUNT(*) FROM employers WHERE company_name IS NULL")
    missing_names = cursor.fetchone()[0]
    print(f"- Employers with missing names: {missing_names}")
    
    cursor.execute("SELECT COUNT(*) FROM employers WHERE employee_count <= 0 OR employee_count IS NULL")
    invalid_employee_counts = cursor.fetchone()[0]
    print(f"- Employers with invalid employee counts: {invalid_employee_counts}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("This dataset will demonstrate how SAAS:")
    print("- Detects and alerts on data quality issues")
    print("- Identifies performance disparities across regions")
    print("- Highlights processing bottlenecks and delays")
    print("- Provides actionable insights for operational improvements")
    print("- Handles missing, invalid, and suspicious data gracefully")
    print("="*60)

if __name__ == "__main__":
    print("Creating realistic CNPS test database with anomalies...")
    create_realistic_cnps_database()
    generate_data_quality_report()
    print("\nDatabase ready for SAAS demo!")
    print("File: cnps_realistic_demo.db")