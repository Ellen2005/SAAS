# Oracle 19c Connection Guide for SAAS

## Step-by-Step: Set Up Oracle 19c and Connect to SAAS

---

## Prerequisites

1. **Oracle 19c** installed on your machine (Oracle Database 19c XE is free)
2. **Python** installed (the backend runs in a virtual environment)
3. **SAAS** backend code cloned and running

---

## Step 1: Install Python Oracle Driver

Open a terminal in the `backend` directory with the virtual environment activated:

```bash
cd C:\Users\nguki\OneDrive\Desktop\SAAS\backend
.\venv\Scripts\activate
pip install oracledb
```

This installs `python-oracledb` — Oracle's official Python driver. It works in **thin mode** by default (no Oracle client needed).

---

## Step 2: Create the CNPS Demo Database in Oracle 19c

### Method A: Using SQL*Plus (Command Line)

1. Open **SQL*Plus** as administrator:
   ```bash
   sqlplus / as sysdba
   ```

2. Create the demo user and tablespace:
   ```sql
   ALTER SESSION SET CONTAINER = XEPDB1;
   CREATE USER cnps_demo IDENTIFIED BY cnps_demo_2026;
   GRANT CONNECT, RESOURCE, DBA TO cnps_demo;
   ALTER USER cnps_demo QUOTA UNLIMITED ON USERS;
   EXIT;
   ```

3. Connect as the demo user and run the schema script:
   ```bash
   sqlplus cnps_demo/cnps_demo_2026@//localhost:1521/XEPDB1
   ```

4. Copy and paste the contents of `scripts/oracle_cnps_demo.sql` into SQL*Plus.

5. Verify the tables were created:
   ```sql
   SELECT table_name FROM user_tables;
   ```
   You should see: `CONTRIBUTIONS`, `PENSIONS`, `EMPLOYERS`, `AT_MP_CLAIMS`

### Method B: Using Oracle SQL Developer (GUI)

1. Open **Oracle SQL Developer**
2. Create a new connection:
   - **Name**: CNPS_Demo
   - **Username**: cnps_demo
   - **Password**: cnps_demo_2026
   - **Hostname**: localhost
   - **Port**: 1521
   - **Service name**: XEPDB1
3. Click **Test** — if successful, click **Connect**
4. Open the file `scripts/oracle_cnps_demo.sql`
5. Click the **Run Script** button (F5)
6. Refresh the Connections panel — you should see the tables

---

## Step 3: Verify Connection String Format

Your connection string for Oracle 19c should be:

```
oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/XEPDB1
```

**Important**: 
- `oracle+oracledb://` — this tells the app to use the Oracle driver
- `cnps_demo` — username
- `cnps_demo_2026` — password
- `localhost:1521` — host and port
- `XEPDB1` — Oracle's pluggable database (PDB) name
- If using a different PDB, replace `XEPDB1` with yours

---

## Step 4: Connect SAAS to Oracle 19c

1. **Restart the backend** if it's running:
   ```bash
   # In backend directory with venv active
   uvicorn api.main:app --reload
   ```

2. **Login to SAAS** at http://localhost:5173

3. Go to **Settings** (gear icon) → **Database Connection**

4. Fill in the form:
   | Field | Value |
   |-------|-------|
   | Database Type | `Oracle` |
   | Connection String | `oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/XEPDB1` |
   | Host | `localhost` |
   | Port | `1521` |
   | Database Name | `XEPDB1` |

5. Click **Test Connection** — you should see "Connection verified!"

6. Click **Save Connection**

---

## Step 5: Sync and Analyze

1. Go to the **Dashboard**
2. Click **Sync Schema** — this discovers tables and columns in Oracle
3. Click **Generate Report** — runs ETL and creates KPIs
4. Go to **Query** (Ask Your Data) — type:
   ```
   Show total contributions by region
   ```

---

## Troubleshooting

### "ORA-12514: TNS listener does not know service"
- Your service name is wrong. Find the correct one:
  ```sql
  SELECT name, pdb FROM v$services;
  ```
- Common ones: `XEPDB1`, `ORCLPDB1`, `XE`, `ORCL`

### "DPY-3010: python-oracledb thin mode cannot connect"
- Oracle 19c XE may need thick mode. Install Oracle Instant Client:
  1. Download from: https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
  2. Extract to `C:\oracle\instantclient_19_25`
  3. Add to PATH: `set PATH=C:\oracle\instantclient_19_25;%PATH%`
  4. In Python:
     ```python
     import oracledb
     oracledb.init_oracle_client()
     ```

### "Connection refused"
- Ensure Oracle 19c is running:
  ```bash
  # Check if Oracle service is running
  sc query OracleServiceXE
  # Or for XE:
  sc query OracleServiceXEPDB1
  ```

### Table names are case-sensitive
- Oracle stores table names in UPPERCASE by default
- The SAAS schema introspector handles this automatically
- If you created tables with quoted lowercase names, use: `"contributions"`

---

## Connection String Reference

| Environment | Connection String |
|---|---|
| Local Oracle XE | `oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/XEPDB1` |
| CNPS Production | `oracle+oracledb://USER:PASS@cnps-oracle.intra.cm:1521/CNPSPDB` |
| Via SSH Tunnel | Use SAAS SSH tunnel feature in Settings → Connection |
| Windows Oracle | `oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/XE` |