# CNPS Oracle 19c Testing Guide

## Complete guide to setting up, connecting, and testing the CNPS demo on Oracle 19c

---

## 1. Prerequisites

- **Oracle 19c** (XEPDB1 or any PDB/Service)
- **SQL*Plus** or **Oracle SQL Developer** to run scripts
- **Backend running** (FastAPI on port 8000)
- **Frontend running** (Vite on port 5000)
- The `oracledb` Python package (already in `backend/requirements.txt`)

---

## 2. Create the CNPS Demo Schema & Data

### Option A: One-command SQL*Plus (recommended)

```bash
sqlplus system/your_password@XEPDB1 @scripts/oracle_cnps_demo.sql
```

This creates:
- User `cnps_demo` / password `cnps_demo_2026` (if not exists)
- 5 tables: `regional_offices`, `employers`, `contributions`, `pension_payments`, `workplace_accidents`
- ~10 regional offices, 500 employers, 15,000 contributions, 2,000 pensions, 800 workplace accidents
- Built-in data quality issues (overdue payments, biases, delays, missing data)

### Option B: SQL Developer

1. Open `scripts/oracle_cnps_demo.sql` in SQL Developer
2. Run as script (F5) while connected to your PDB
3. The script auto-creates the user and schema

### Option C: Run only the data population (if schema already exists)

If you want to point to an existing schema without re-creating user/tables, edit the script and:
- Remove the user creation block
- Remove the `DROP TABLE` block
- Keep only the INSERT statements for each table

---

## 3. Connect in SAAS Settings

### Step 1: Open Settings → Connection

Navigate to **Settings → Connection** in the app.

### Step 2: Fill in the connection form

| Field | Value |
|-------|-------|
| **DB Type** | `oracle` |
| **Credentials** | `oracle+oracledb://cnps_demo:cnps_demo_2026@YOUR_HOST:1521/XEPDB1` |
| **Host** | Your Oracle host (or `localhost` if running locally) |
| **Port** | `1521` |
| **DB Name** | `XEPDB1` (or your service name) |

**Example for local Oracle XE:**
```
oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/XEPDB1
```

**Example for remote Oracle:**
```
oracle+oracledb://cnps_demo:cnps_demo_2026@oracle-demo.example.com:1521/XEPDB1
```

### Step 3: Test Connection

Click **Test Connection** — you should see a green success message.

### Step 4: Save

Click **Save Connection**.

---

## 4. Verify Schema Discovery

1. Go to **Schema Explorer** (`/explorer`)
2. Click **Re-discover**
3. You should see:

| Stat | Expected |
|------|----------|
| **Tables** | 5 |
| **Dialect** | `oracle` |
| **Schemas** | 1 (`CNPS_DEMO` or uppercase schema) |
| **Analyses ready** | 5+ (contribution trends, payment anomalies, claim throughput, etc.) |

4. Tables should show **purple domain tags**:
   - `contributions` → **contribution**, **payment** tags
   - `pension_payments` → **payment**, **pension** tags
   - `workplace_accidents` → **claim** tag
   - `employers` → **employer** tag
   - `regional_offices` → (generic, no specific domain)

---

## 5. Testing the Key Demo Features

### 5.1 Run Suggested Analyses

In Schema Explorer, click **Run** on any analysis card:
- **Contribution trend over time** → line chart showing monthly sums
- **Late/missing contribution detection** → staleness report
- **Payment anomaly detection** → z-score outliers
- **Claim processing throughput** → weekly claim counts
- **Pension/benefit liability forecast** → projection chart

### 5.2 Sync to Dashboard

Click **Sync to Dashboard** — this runs all suggested analyses and writes results as KPI rows to your Supabase dashboard.

### 5.3 Dashboard

Check the **Dashboard** page — KPIs from Oracle data will appear in the tile grid with NORMAL / WARNING / CRITICAL statuses.

### 5.4 AI Analyst

Go to **Analysis** page and try these goals:
- *"Analyze contribution collection efficiency to improve cash flow"*
- *"Identify regional offices with performance issues that need management attention"*
- *"Evaluate pension processing bottlenecks to improve service delivery"*

### 5.5 Ask Your Data (NLQ)

Try these natural-language questions:
- *"How many overdue contributions are there?"*
- *"Which regional office has the worst accident claim rejection rate?"*
- *"Show total contributions by region for the last 6 months"*
- *"Which employers are delinquent?"*

### 5.6 Validation

Go to **Validation** page — you'll see CNPS data quality checks showing:
- Overdue payment counts
- Missing employee SSNs
- Regional performance disparities
- Suspicious contribution amounts

---

## 6. Data Quality Issues Built Into the Data

The Oracle demo data includes these real-world anomalies that SAAS will detect:

| Issue | How to see it |
|-------|---------------|
| **7,008 overdue contributions** | Validation page or NLQ: "How many overdue contributions?" |
| **5,341 invalid amounts** (negative/zero/null) | Schema Explorer analysis or validation |
| **2,715 missing employee SSNs** | Validation page shows data quality issues |
| **BER office: 52.4% claim rejection rate** | NLQ: "Which region has the highest claim rejection rate?" |
| **KRI office: 50.6% claim rejection rate** | NLQ: "Show rejection rates by region" |
| **404 pension claims taking >30 days** | Analysis: "Evaluate pension processing bottlenecks" |
| **157 delinquent employers** | NLQ: "List delinquent employers" |
| **23 employers with missing names** | Validation: data quality report |

---

## 7. Semantic Mapping (Admin)

For the Admin user, you can map CNPS fields to the Oracle columns:

| Global Field | Oracle Column | Table |
|--------------|---------------|-------|
| contribution_amount | CONTRIBUTION_AMOUNT | CONTRIBUTIONS |
| contribution_date | CONTRIBUTION_DATE | CONTRIBUTIONS |
| employee_id | EMPLOYEE_SSN | CONTRIBUTIONS |
| employer_id | EMPLOYER_ID | CONTRIBUTIONS |
| payment_status | PAYMENT_STATUS | CONTRIBUTIONS |
| pension_amount | PENSION_AMOUNT | PENSION_PAYMENTS |
| regional_code | REGIONAL_CODE | CONTRIBUTIONS |
| accident_date | ACCIDENT_DATE | WORKPLACE_ACCIDENTS |
| claim_status | CLAIM_STATUS | WORKPLACE_ACCIDENTS |

Go to **Governance → Semantic layer → CNPS Core Schema** and map these fields. Then refresh data to enable configured ETL mode.

---

## 8. Troubleshooting

### Connection fails with "ORA-...: TNS:listener does not currently know of service requested"

**Fix:** Your service name is wrong. Common Oracle 19c XE service names:
- `XEPDB1` (Pluggable Database)
- `XE` (Root container)
- `ORCL` (Custom install)
- `ORCLPDB` (Some 19c installations)

Query your service name:
```sql
SELECT name, pdb FROM v$services ORDER BY name;
```

### Connection fails with "ORA-12514: TNS:listener does not know of service"

**Fix:** The listener might not be configured for your PDB. Register the PDB:
```sql
ALTER SYSTEM SET LOCAL_LISTENER = '(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))';
ALTER SYSTEM REGISTER;
```

### "oracledb" not installed

**Fix:** 
```bash
pip install oracledb
```

### Tables appear in uppercase but schema shows 0 tables

Oracle stores object names in UPPERCASE by default. The introspection code handles this — just click **Re-discover** after first connection.

### NLQ returns "Could not find tables" with Oracle

**Fix:** The database_connections table may not have `db_type` set to `oracle`. Re-save the connection and ensure the DB type dropdown says **Oracle**.

---

## 9. Comparison: SQLite Demo vs Oracle Demo

| Feature | SQLite (`cnps_full_demo.db`) | SQLite Realistic (`cnps_realistic_demo.db`) | Oracle 19c (`oracle_cnps_demo.sql`) |
|---------|------|------|--------|
| **Tables** | 8 | 5 | 5 |
| **Total rows** | ~6,500 | ~144,000 | ~144,000 |
| **Data quality issues** | Basic (overdue, duplicates) | Advanced (bias, missing data, anomalies) | Same as realistic |
| **Connection string** | `sqlite:///C:/path/cnps_full_demo.db` | `sqlite:///C:/path/cnps_realistic_demo.db` | `oracle+oracledb://cnps_demo:pass@host:1521/XEPDB1` |
| **Best for** | Quick feature test | Sales demo with real-world problems | Production-like Oracle environment test |
| **Setup time** | 10 seconds | 30 seconds | 5-10 minutes |

---

## 10. Quick Start (if you've lost track)

```bash
# Step 1: Run the Oracle SQL script
sqlplus system/your_password@XEPDB1 @scripts/oracle_cnps_demo.sql

# Step 2: Verify the data
sqlplus cnps_demo/cnps_demo_2026@XEPDB1
SELECT COUNT(*) FROM contributions;
SELECT COUNT(*) FROM employers;
SELECT COUNT(*) FROM workplace_accidents;

# Step 3: In the SAAS app, go to Settings → Connection
#    DB Type: oracle
#    Credentials: oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/XEPDB1
#    Test Connection → Save

# Step 4: Schema Explorer → Re-discover → see 5 tables with purple tags
# Step 5: Run suggested analyses, Sync to dashboard
# Step 6: Explore Dashboard, Analysis, NLQ, Validation
```

---

**Oracle 19c is now fully supported and tested. All features work identically to SQLite/PostgreSQL — just with Oracle's native SQL dialect under the hood.**