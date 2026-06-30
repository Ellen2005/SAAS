# Enterprise Analytics Platform — Complete System Flow

## End-to-End Data Flow for Every Feature

---

# 1. AUTHENTICATION FLOW

```
┌──────────┐     ┌──────────┐     ┌───────────┐     ┌────────────┐
│  Browser │────▶│  Vite    │────▶│  FastAPI   │────▶│  Supabase  │
│ (React)  │◀────│(Frontend)│◀────│ (Backend)  │◀────│ (Auth)     │
└──────────┘     └──────────┘     └───────────┘     └────────────┘
```

### Step-by-Step:

**1. User navigates to app**
```
Browser → GET / → Vite dev server serves index.html
         → React mounts App.jsx
         → AuthProvider checks localStorage for cached session
```

**2. User clicks "Login"**
```
Browser → POST /auth/v1/token?grant_type=password (to Supabase directly)
         → Supabase validates credentials
         → Returns JWT access_token + refresh_token
```

**3. React stores tokens**
```
React → localStorage.setItem('supabase.auth.token', ...)
      → AuthContext.setUser(response.user)
      → AuthContext calls GET /api/users/me (with Bearer token)
```

**4. Backend resolves user role**
```
FastAPI receives: GET /api/users/me
  Headers: { Authorization: "Bearer <jwt>" }

Flow:
  1. require_role middleware decodes JWT
  2. Queries Supabase: SELECT role, department_id FROM user_roles WHERE user_id = ?
  3. Queries Supabase: SELECT name FROM departments WHERE id = ?
  4. Returns: { role: "manager", department_id: "uuid", department_name: "Douala" }

React receives role → sets isManager=true → renders Manager UI
```

**5. Role-Based Navigation**
```
React:
  if isAdmin  → show: Dashboard, Reports, Admin, Analyst, Schema, Query, Validation, Settings
  if isManager→ show: Dashboard, Reports, Analyst, Schema, Query, Validation, Settings
  if isViewer → show: Dashboard, Reports only
```

---

# 2. DATABASE CONNECTION FLOW

```
┌──────────┐     ┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐
│  Settings│────▶│  React   │────▶│  FastAPI   │────▶│  Supabase   │     │  Target  │
│   Page   │     │  Form    │     │ /api/test- │     │ (encrypted) │────▶│ Database │
│          │     │          │     │ connection │     │  storage    │     │ (Oracle) │
└──────────┘     └──────────┘     └───────────┘     └────────────┘     └──────────┘
```

### Step-by-Step:

**1. User fills connection form in Settings page**
```
Fields:
  - Database Type: Oracle
  - Host: localhost
  - Port: 1521
  - Database Name: ORCLPDB
  - User: cnps_demo
  - Password: ••••••••••

React builds credential string:
  oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/?service_name=ORCLPDB
```

**2. User clicks "Test Connection"**
```
React → POST /api/test-connection
  Body: {
    db_type: "oracle",
    credentials: "oracle+oracledb://cnps_demo:****@localhost:1521/?service_name=ORCLPDB",
    host: "localhost",
    port: 1521,
    db_name: "ORCLPDB"
  }
```

**3. Backend processes connection test**
```
FastAPI receives test-connection request:

Step 3a: enrich_connection_payload()
  - detect_db_type() → "oracle"
  - normalize_credentials() → ensures "oracle+oracledb://" prefix
  - parse_connection_uri() → extracts host, port, db_name

Step 3b: create_engine()
  - Creates SQLAlchemy engine with:
    URL: oracle+oracledb://cnps_demo:***@localhost:1521/?service_name=ORCLPDB
    connect_args: { tcp_connect_timeout: 10 }
    pool_pre_ping: true

Step 3c: engine.connect()
  - oracledb thin driver establishes TCP connection to localhost:1521
  - Oracle listener routes to ORCLPDB service
  - Authenticates with cnps_demo/cnps_demo_2026
  - Executes: SELECT 1 FROM DUAL

Step 3d: Returns result
  - Success: { status: "success", message: "Connection verified!" }
  - Error: { status: "error", message: "DPY-6003: ..." }
```

**4. User clicks "Save Connection"**
```
React → POST /api/settings/connection
  Body: {
    db_type: "oracle",
    credentials: "...",
    host: "localhost",
    port: 1521,
    db_name: "ORCLPDB",
    connection_method: "direct"
  }

Backend:
  Step 4a: encrypt_credentials() uses AES to encrypt the connection string
  Step 4b: Stores in Supabase table: database_connections
    {
      user_id: "uuid",
      db_type: "oracle",
      credentials: "<encrypted blob>",
      host: "localhost",
      port: 1521,
      db_name: "ORCLPDB",
      read_only: true
    }
  Step 4c: Logs change to audit_service
  Step 4d: Returns { status: "success" }
```

---

# 3. ETL PIPELINE FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐     ┌─────────────┐
│  Target   │────▶│  FastAPI   │────▶│  Supabase   │     │  FastAPI  │     │  React      │
│  Database │     │ ETL Engine │     │ kpi_results │────▶│  /api/    │────▶│  Dashboard  │
│ (Oracle)  │     │            │     │ anomaly_... │     │  summary  │     │  UI         │
└──────────┘     └───────────┘     └────────────┘     └──────────┘     └─────────────┘
```

### Step-by-Step:

**1. Trigger ETL (Manual or Scheduled)**

**Manual:**
```
User clicks "Sync Now" in Dashboard or Settings

React → POST /api/etl/trigger
```

**Scheduled (Automatic):**
```
Every 1 minute, APScheduler runs process_scheduled_etl():
  1. Queries Supabase: SELECT * FROM user_preferences WHERE sync_time = NOW()
  2. Queries Supabase: SELECT * FROM departments WHERE heartbeat_time = NOW()
  3. For each match, triggers ETL for that user/department
```

**2. Backend runs ETL pipeline**
```
FastAPI receives trigger:

Step 2a: Load user's database connection
  - Queries Supabase: database_connections WHERE user_id = ?
  - decrypt_credentials() to get raw connection string

Step 2b: Create SQLAlchemy engine to target database
  Engine connects to: oracle+oracledb://cnps_demo:***@localhost:1521/?service_name=ORCLPDB

Step 2c: Introspect target database schema
  - Queries: SELECT table_name FROM user_tables
  - For each table: DESCRIBE or SELECT column_name, data_type FROM user_tab_columns
  - Builds schema map: { "CONTRIBUTIONS": {"columns": [...], "row_count": 144669} }

Step 2d: Execute KPI calculations based on schema
  For Oracle, uses Oracle-specific SQL syntax:

  -- Total Contributions
  SELECT SUM(contribution_amount) FROM contributions WHERE payment_status = 'paid'

  -- Pension Disbursement  
  SELECT SUM(pension_amount) FROM pension_payments

  -- Contribution Count
  SELECT COUNT(*) FROM contributions

  -- Regional Distribution
  SELECT regional_code, SUM(contribution_amount) 
  FROM contributions GROUP BY regional_code

Step 2e: Calculate derived KPIs
  Python calculations:
    - dod_pct = ((today_value - yesterday_value) / yesterday_value) * 100
    - wow_pct = ((this_week - last_week) / last_week) * 100
    - avg_7d = rolling average of last 7 days

Step 2f: Run anomaly detection
  Z-score analysis:
    - Calculate mean and stddev for each KPI
    - z = (value - mean) / stddev
    - Flag |z| > 2 as WARNING, |z| > 3 as CRITICAL

  Pattern checks:
    - Missing data (gaps in time series)
    - Duplicate records
    - Late payments (overdue > 30 days)
    - Regional coverage gaps

Step 2g: Store results in Supabase
  INSERT INTO kpi_results (user_id, kpi_name, value, dod_pct, wow_pct, status, recorded_at)
  VALUES (?, ?, ?, ?, ?, ?, NOW())
  
  INSERT INTO anomaly_records (user_id, kpi_name, severity, deviation, context, detected_at)
  VALUES (?, ?, ?, ?, ?, NOW())

Step 2h: Generate AI Narrative
  - Collects all KPI results
  - Calls Groq API (LLM) with KPI data
  - Returns professional narrative (no markdown)
  - Stores in Supabase: daily_reports

Step 2i: Update sync status
  UPDATE user_preferences SET last_sync = NOW() WHERE user_id = ?
```

**3. Dashboard loads data**
```
React mounts Dashboard page:

Step 3a: GET /api/summary
  Headers: { Authorization: "Bearer <jwt>" }

Backend:
  1. Check cache (Redis or in-memory) for key "summary:{user_id}"
  2. If cached and TTL < 120s, return cached
  3. Else:
     - Query Supabase: kpi_results WHERE user_id = ? LIMIT 25
     - Query Supabase: anomaly_records WHERE user_id = ? LIMIT 25
     - Query Supabase: daily_reports WHERE user_id = ? LIMIT 10
     - Parse KPIResult objects (filter legacy demo data)
     - Build DashboardSummary object
  4. Cache result for 120 seconds
  5. Return JSON

React receives:
{
  "kpis": [
    { "kpi_name": "total_contributions", "value": 154000000, "dod_pct": 3.2, "status": "NORMAL" },
    { "kpi_name": "pension_disbursement", "value": 45000000, "dod_pct": -1.1, "status": "NORMAL" }
  ],
  "anomalies": [...],
  "narrative": "Executive Summary: Total contributions reached 154M XAF...",
  "last_refreshed": "2026-06-22"
}

Step 3b: GET /api/kpis/series
  - Returns time-series data for charts
  - { "series": { "total_contributions": [{"t": "2026-01", "value": 140000}, ...] } }

Step 3c: Render dashboard
  - KPI cards with values, sparklines, status colors
  - Anomaly alerts list
  - AI narrative section
  - Validation summary
```

---

# 4. AI ANALYST — GOAL ANALYSIS FLOW (WITH SEQUENCE DIAGRAM)

## Complete Sequence Diagram

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────┐
│  User    │────▶│  React    │────▶│  FastAPI   │────▶│  Supabase │     │  Groq AI    │────▶│  Target   │
│          │     │ AIAnalyst │     │ /api/      │     │ (Metadata)│     │  (LLM)      │     │ Database  │
│          │     │  Page     │     │ analysis   │     │           │     │             │     │ (Oracle)  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └─────────────┘     └──────────┘
     │                │                │                │                │                   │
     │ 1. Enter goal  │                │                │                │                   │
     │────────────────│ POST /run      │                │                │                   │
     │                │────────────────│────────────────│                │                   │
     │                │                │ 2. Validate    │                │                   │
     │                │                │    auth & role │                │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 3. Create run  │                │                   │
     │                │                │    record      │                │                   │
     │                │                │ (status:planning)│              │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 4. Load DB     │                │                   │
     │                │                │    connection  │                │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 5. Introspect  │                │                   │
     │                │                │    schema      │                │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 6. Generate    │                │                   │
     │                │                │    SQL plan    │                │                   │
     │                │                │────────────────────────────────────▶│                   │
     │                │                │                │ 7. LLM plans   │                   │
     │                │                │                │    SQL query   │                   │
     │                │                │                │◀────────────────────────────────────│
     │                │                │ 8. Validate    │                │                   │
     │                │                │    SQL (read-  │                │                   │
     │                │                │    only check) │                │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 9. Execute SQL │                │                   │
     │                │                │────────────────│────────────────│                   │
     │                │                │                │                │                   │
     │                │                │                │ 10. Query data │                   │
     │                │                │                │◀────────────────────────────────────│
     │                │                │ 11. Build      │                │                   │
     │                │                │     chart spec │                │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 12. Generate   │                │                   │
     │                │                │     insights   │                │                   │
     │                │                │────────────────────────────────────▶│                   │
     │                │                │                │ 13. LLM        │                   │
     │                │                │                │     explains   │                   │
     │                │                │                │◀────────────────────────────────────│
     │                │                │ 14. Update run │                │                   │
     │                │                │     (completed)│                │                   │
     │                │                │────────────────│                │                   │
     │                │                │ 15. Store KPI  │                │                   │
     │                │                │     snapshot   │                │                   │
     │                │                │────────────────│                │                   │
     │ 16. Display   │◀───────────────│ 17. Return     │                │                   │
     │     results   │                │     results    │                │                   │
     │◀───────────────│                │                │                │                   │
     │                │                │                │                │                   │
     │ 18. View SQL   │                │                │                │                   │
     │     & chart   │                │                │                │                   │
     │◀───────────────│                │                │                │                   │
```

### Step-by-Step Detailed Flow:
       │               │                │                │                  │
       │  Enter goal   │                │                │                  │
       ├──────────────▶│   POST        │                │                  │
       │               ├──────────────▶│  Analyze goal   │                  │
       │               │               ├────────────────▶│                  │
       │               │               │  Query Oracle   │                  │
       │               │               │◀────────────────┤                  │
       │               │               │  Results        │                  │
       │               │               ├────────────────────────────────────▶│
       │               │               │  Build prompt    │                  │
       │               │               │◀────────────────────────────────────┤
       │               │               │  AI Response     │                  │
       │               │◀──────────────┤                  │                  │
       │               │  Display      │                  │                  │
       │◀──────────────┤  results      │                  │                  │
```

### Phase 1: User Input & Authentication

**1. User navigates to AI Analyst page**
```
React renders AIAnalystPage.jsx

Page has 2 tabs:
  - "Goal Analysis" (enter analytical goals)
  - "Analysis History" (past analysis runs)
```

### Phase 2: Analysis Planning

**2. User enters a goal and runs analysis**
```
User types: "Show me total contributions by region for 2024, highlighting collection rates"

React → POST /api/analysis/run
  Body: {
    goal_text: "Show me total contributions by region for 2024...",
    user_id: "<jwt-user-id>"
  }
```

### Phase 3: AI Planning & SQL Generation

**3. Backend processes analysis**

```
FastAPI enters analysis_engine.run_analysis():

Step 3a: Validate authentication & authorization
  - require_role(["manager", "admin"]) validates JWT
  - Extracts user_id from token
  - Checks user role in Supabase

Step 3b: Create analysis run record
  INSERT INTO analysis_runs (user_id, goal_text, goal_type, status, started_at)
  VALUES (user_id, goal_text, "natural_language", "planning", NOW())
  
  Returns: run_id for tracking

Step 3c: Load user's database connection from Supabase
  - Decrypt credentials
  - Create SQLAlchemy engine

Step 3b: Introspect schema (get table/column info)
  SELECT table_name, column_name, data_type 
  FROM user_tab_columns 
  ORDER BY table_name, column_id

  Returns schema context like:
  Tables: CONTRIBUTIONS(contribution_date, contribution_amount, regional_code, ...)
          EMPLOYERS(name, sector, employee_count, ...)

Step 3d: Generate SQL using AI (Groq LLM)
  Model: qwen2.5-72b-instruct (with fallback chain: gpt-oss-120b, qwen2.5-27b, llama-3.1-8b, gemma2-9b)
  
  Prompt to Groq:
    System: "You are a CNPS Oracle SQL expert. Generate read-only SELECT queries.
             Use Oracle 19c syntax: FETCH FIRST N ROWS ONLY (not LIMIT),
             TRUNC(date,'MM') for month truncation, SYSDATE for current date."
    
    User: f"""
    Analysis Goal: {goal_text}
    
    Database Schema:
    {schema_hint}
    
    Generate a JSON response:
    {{
      "sql": "<Oracle SELECT query>",
      "summary_hint": "<one-line summary>",
      "chart_type": "bar|line|pie|table",
      "x_column": "<column for x-axis>",
      "y_column": "<column for y-axis>"
    }}
    """
  
  Groq returns:
    {
      "sql": "SELECT c.regional_code, COUNT(*) as payment_count, SUM(c.contribution_amount) as total_amount FROM contributions c WHERE EXTRACT(YEAR FROM c.contribution_date) = 2024 GROUP BY c.regional_code ORDER BY total_amount DESC FETCH FIRST 10 ROWS ONLY",
      "summary_hint": "Total contributions by region for 2024",
      "chart_type": "bar",
      "x_column": "regional_code",
      "y_column": "total_amount"
    }

Step 3e: Validate SQL (security check)
  _validate_readonly_sql(sql):
    - Must start with SELECT, WITH, or PRAGMA
    - No forbidden keywords: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
    - No semicolons (single statement only)
    - Raises ValueError if validation fails

Step 3f: Execute SQL against target database
  engine.execute(validated_sql)
  
  Oracle returns:
    [
      { regional_code: "DOU", payment_count: 15000, total_amount: 450000000, avg_amount: 30000 },
      { regional_code: "YAO", payment_count: 12000, total_amount: 380000000, avg_amount: 31666 },
      { regional_code: "GAR", payment_count: 8500, total_amount: 210000000, avg_amount: 24705 },
      ...
    ]
```
  Sends to Groq LLM:
    System Prompt:
      "You are an Oracle SQL expert. Convert this analytical goal into
       Oracle-compatible SQL. Use FETCH FIRST N ROWS ONLY instead of LIMIT.
       Return ONLY the SQL query, no explanation."
    
    User Message:
      Goal: "Show me total contributions by region for 2024..."
      Schema: [table definitions]
      Database: Oracle 19c

  Groq returns SQL:
    SELECT c.regional_code, COUNT(*) as payment_count,
           SUM(c.contribution_amount) as total_amount,
           ROUND(AVG(c.contribution_amount), 2) as avg_amount
    FROM contributions c
    WHERE EXTRACT(YEAR FROM c.contribution_date) = 2024
    GROUP BY c.regional_code
    ORDER BY total_amount DESC

Step 3d: Execute SQL against Oracle database
  engine.execute(SQL_above)
  Returns: [
    { regional_code: "DOU", payment_count: 15000, total_amount: 450000000, avg_amount: 30000 },
    { regional_code: "YAO", payment_count: 12000, total_amount: 380000000, avg_amount: 31666 },
    ...
  ]

Step 3e: Generate insights from results
  Sends to Groq LLM:
    System Prompt:
      "Analyze these results and provide insights in plain text.
       No markdown, no asterisks. Professional tone."
    
    Data: [query results]

  Groq returns insights:
    "Douala region leads with 450M XAF in contributions across 15,000 payments, 
     representing 32% of total. Yaoundé follows with 380M XAF..."
    
Step 3f: Store analysis run
  INSERT INTO analysis_runs (user_id, goal_text, sql_generated, result_data, 
                             result_summary, status, started_at, completed_at)
  VALUES (...)

Step 3g: Return results to frontend
  Return: {
    status: "completed",
    sql_generated: "SELECT c.regional_code...",
    result_data: [rows],
    result_summary: "Douala region leads with 450M XAF...",
    columns: ["regional_code", "payment_count", "total_amount", "avg_amount"],
    row_count: 10
  }
```

### Phase 4: Insight Generation & Storage

**4. Generate AI insights from results**

```
Step 4a: Build chart specification
  build_chart_from_rows(rows, columns, chart_type="bar")
  - Auto-detects best chart type if not specified
  - Creates Recharts-compatible spec:
    {
      "type": "bar",
      "data": rows,
      "xKey": "regional_code",
      "yKey": "total_amount",
      "title": "Total Contributions by Region (2024)"
    }

Step 4b: Generate insights using Groq LLM
  Prompt:
    System: "You are a CNPS business analyst. Explain these results in plain French.
             No markdown, no asterisks. Professional tone. Max 3 sentences."
    
    User: f"""
    Goal: {goal_text}
    SQL: {sql}
    Results: {json.dumps(rows[:10])}
    
    Provide:
    1. What this means (plain language)
    2. Key insights (bullet points)
    3. Recommended actions
    """
  
  Groq returns:
    "Douala region leads with 450M XAF (32% of total), followed by Yaoundé at 380M XAF (27%).
     Garoua shows lower performance at 210M XAF (15%). Consider targeted collection
     efforts in underperforming regions. Review regional staffing levels in GAR."

Step 4c: Store complete analysis run
  UPDATE analysis_runs SET
    status = "completed",
    plan_json = {sql, chart_type, summary_hint},
    result_summary = insights,
    chart_json = chart_spec,
    metrics_json = {row_count, columns, sample_rows, explanation},
    completed_at = NOW()
  WHERE id = run_id

Step 4d: Publish primary metric to dashboard
  INSERT INTO kpi_results (user_id, kpi_name, value, status, source, recorded_at)
  VALUES (user_id, "custom_analysis", first_row_value, "normal", "goal_run", NOW())
  
  This makes the result visible on the dashboard as a KPI
```

### Phase 5: Frontend Display

**5. Frontend displays results**
```
React receives analysis results:

Step 4a: Render data table
  <table>
    <thead><th>Region</th><th>Payments</th><th>Total Amount</th></thead>
    <tbody>
      <tr><td>DOU</td><td>15,000</td><td>450,000,000 XAF</td></tr>
      ...
    </tbody>
  </table>

Step 4b: Auto-generate chart
  Chart type: Bar chart (detected from regional → numeric data)
  X-axis: regional_code
  Y-axis: total_amount
  Renders with Recharts

Step 4c: Display AI insights
  <div class="insights">
    <p>Douala region leads with 450M XAF in contributions...</p>
  </div>

Step 4d: Show generated SQL (expandable)
  <details>
    <summary>View Generated SQL</summary>
    <pre>SELECT c.regional_code...</pre>
  </details>
```

---

# 5. NATURAL LANGUAGE QUERY (NLQ) FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐     ┌─────────────┐
│  User    │────▶│  React    │────▶│  FastAPI   │────▶│  Target   │     │  Groq AI    │
│  Types   │     │  NLQPage  │     │ /api/nlq   │     │ Database  │────▶│  (LLM)      │
│  Query   │     │           │     │            │     │ (Oracle)  │     │             │
└──────────┘     └──────────┘     └───────────┘     └──────────┘     └─────────────┘
```

### Step-by-Step:

**1. User asks a question in natural language**
```
User types: "Which employers have the most overdue payments?"

React → POST /api/nlq
  Body: { question: "Which employers have the most overdue payments?" }
```

**2. Backend processes NLQ**
```
FastAPI enters nlq_service.run_nlq():

Step 2a: Load schema from target database
  - Introspect tables and columns (cached for 5 min)
  - Build schema context string

Step 2b: Generate SQL from question
  Send to Groq LLM:
    System: "Convert to Oracle SQL. Use FETCH FIRST N ROWS ONLY. 
             Only return SQL, no explanation."
    Schema: [table definitions]
    Question: "Which employers have the most overdue payments?"

  Groq returns:
    SELECT e.name, COUNT(*) as overdue_count, 
           SUM(c.contribution_amount) as total_overdue
    FROM contributions c
    JOIN employers e ON c.employer_id = e.id
    WHERE c.payment_status = 'overdue'
    GROUP BY e.name
    ORDER BY total_overdue DESC
    FETCH FIRST 10 ROWS ONLY

Step 2c: Validate SQL is read-only
  validate_sql_read_only():
    - Must start with SELECT, WITH, EXPLAIN, DESCRIBE, SHOW, PRAGMA
    - No DROP, ALTER, CREATE, DELETE, INSERT, UPDATE, TRUNCATE
    - No UNION with DDL/DML
    - Single statement only (no semicolons in middle)

Step 2d: Execute SQL against target database
  engine.execute(validated_sql)
  Returns rows

Step 2e: Return results
  Return: {
    sql: "SELECT e.name...",
    columns: ["name", "overdue_count", "total_overdue"],
    rows: [
      {"name": "Late Payer Industries SA", "overdue_count": 120, "total_overdue": 45000000},
      ...
    ]
  }
```

**3. Frontend visualizes results**
```
React receives NLQ results:

Step 3a: Determine chart type automatically
  - If 2 columns and one is numeric → Bar chart
  - If temporal data → Line chart
  - If categorical → Pie/bar chart

Step 3b: Render chart + table
  <ResponsiveContainer>
    <BarChart data={rows}>
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip />
      <Bar dataKey="total_overdue" fill="#ef4444" />
    </BarChart>
  </ResponsiveContainer>
  <table>...</table>

Step 3c: Show generated SQL (collapsible)
  SQL shown in <code> block with copy button
```

---

# 6. AI NARRATIVE GENERATION FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────────┐     ┌──────────┐
│ Dashboard│────▶│  React    │────▶│  FastAPI   │────▶│  Groq AI     │────▶│  Supabase │
│ Generate │     │  Generate │     │ /api/      │     │  llama-3.3   │     │ daily_    │
│ Report   │     │  Report   │     │ report     │     │  70B         │     │ reports   │
└──────────┘     └──────────┘     └───────────┘     └──────────────┘     └──────────┘
```

### Step-by-Step:

**1. User clicks "Generate Report"**

**2. Backend collects all KPI data**
```
FastAPI:
  Step 2a: Query kpi_results for latest KPIs
  Step 2b: Query anomaly_records for active anomalies
  Step 2c: Query validation_logs for data quality issues
  Step 2d: Build comprehensive data package
```

**3. Call Groq API for narrative generation**
```
Send to Groq:
  System Prompt:
    "You are a professional data analyst. Generate a concise executive report.
     IMPORTANT: Use PLAIN TEXT only. No markdown formatting, no asterisks,
     no bullet points with *, no bold markers. Use clean paragraph structure.
     Write like a professional business report in Microsoft Word."

  User Message: [KPI data + anomalies]

  Groq returns:
    "Executive Report
     
     Overview
     Total contributions reached 154 million XAF this period, showing a 3.2% 
     increase from the previous period. This growth is driven primarily by the 
     Douala and Yaoundé regions which account for 62% of total collections.
     
     Key Findings
     Collection rates remain strong at 94.5% overall. However, the Garoua region 
     shows a declining trend at 87.2%, down 2.1 percentage points. Two employers 
     in the construction sector account for 45% of overdue payments.
     
     Anomalies Detected
     A duplicate contribution record was identified for employee INS-030000 in 
     the Douala region. This has been flagged for review.
     
     Recommendations
     Consider targeted collection enforcement in Garoua. Review the construction 
     sector payment schedules. Investigate potential data entry issues causing 
     duplicate records."

  Response is clean text - no **, no *, no __, no # headings
```

**4. Store report in Supabase**
```
INSERT INTO daily_reports (user_id, report_date, narrative, kpi_summary)
VALUES (?, CURRENT_DATE, clean_text, json_data)
```

**5. Return to frontend**
```
{
  "narrative": "Executive Report\n\nOverview\nTotal contributions...",
  "report_date": "2026-06-22",
  "format": "plain_text"
}
```

**6. Frontend displays narrative**
```
React renders:
  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
    {narrative.split('\n\n').map((para, i) => (
      <p key={i} style={{ marginBottom: '12px' }}>{para}</p>
    ))}
  </div>

Result: Clean paragraphs, no asterisks, professional formatting
```

---

# 7. ADMIN → SEMANTIC TEMPLATE ASSIGNMENT FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐     ┌──────────────┐
│  Admin   │────▶│  React    │────▶│  FastAPI   │────▶│  Supabase │     │  Manager     │
│  Creates │     │ Admin     │     │ /api/admin │     │ semantic_ │────▶│  Settings    │
│ Template │     │ Semantic  │     │ /semantic  │     │ templates │     │  → sees      │
│          │     │           │     │            │     │           │     │  template    │
└──────────┘     └──────────┘     └───────────┘     └──────────┘     └──────────────┘
```

### Step-by-Step:

**1. Admin creates semantic template**
```
React → POST /api/admin/semantic/templates
  Body: {
    name: "CNPS National Standard",
    description: "Standard KPIs for CNPS regional offices"
  }

Backend:
  INSERT INTO semantic_templates (name, description, created_by)
  VALUES ('CNPS National Standard', '...', 'admin-uuid')
  
  Returns: { template: { id: "tmpl-123", name: "CNPS National Standard" } }
```

**2. Admin adds fields to template**
```
React → POST /api/admin/semantic/templates/tmpl-123/fields
  Body: { global_field_name: "total_contributions", data_type: "number", required: true }

Backend:
  INSERT INTO semantic_fields (template_id, global_field_name, data_type, required)
  VALUES ('tmpl-123', 'total_contributions', 'number', true)

Repeat for each field:
  - pension_disbursement (number, required)
  - collection_rate (percentage, required)
  - at_mp_frequency (number, optional)
```

**3. Admin assigns template to department**
```
React → PUT /api/admin/departments/dept-456
  Body: { template_id: "tmpl-123" }

Backend:
  UPDATE departments SET template_id = 'tmpl-123' WHERE id = 'dept-456'
```

**4. Manager in that department sees template in Settings**
```
React → GET /api/semantic/my-template

Backend:
  1. Get user's role: SELECT department_id FROM user_roles WHERE user_id = ?
  2. Get department: SELECT template_id FROM departments WHERE id = ?
  3. Get template: SELECT * FROM semantic_templates WHERE id = ?
  4. Get fields: SELECT * FROM semantic_fields WHERE template_id = ?
  5. Get user's existing mappings: SELECT * FROM field_mappings WHERE user_id = ?
  6. Return: { department, template, fields: [...], mappings: [...] }
```

**5. Manager maps fields to database columns**
```
React → POST /api/semantic/mappings
  Body: {
    template_field_id: "field-1",
    local_column_name: "contributions.contribution_amount",
    transformation_rule: { aggregation: "SUM" }
  }

Backend:
  UPSERT INTO field_mappings (user_id, template_field_id, local_column_name, transformation_rule)
  VALUES ('user-uuid', 'field-1', 'contributions.contribution_amount', '{"aggregation": "SUM"}')
  ON CONFLICT (user_id, template_field_id) DO UPDATE
```

**6. Validate mappings**
```
React → GET /api/semantic/mappings/validate

Response:
{
  "valid": true,
  "total_fields": 5,
  "mapped_fields": 5,
  "missing_required": [],
  "missing_optional": []
}
```

---

# 8. CUSTOM REPORT GENERATION FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐     ┌──────────────┐
│  User    │────▶│  React    │────▶│  FastAPI   │────▶│  Target   │     │  PDF/Excel   │
│ Configures│     │ Custom    │     │ /api/      │     │ Database  │────▶│  Download    │
│ Report   │     │ Report    │     │ report     │     │ (Oracle)  │     │              │
└──────────┘     └──────────┘     └───────────┘     └──────────┘     └──────────────┘
```

### Step-by-Step:

**1. User defines custom report parameters**
```
React → POST /api/reports/custom
  Body: {
    title: "Q1 2026 Regional Performance Review",
    metrics: ["total_contributions", "collection_rate", "employer_count"],
    dimensions: ["regional_code", "sector"],
    date_range: { from: "2026-01-01", to: "2026-03-31" },
    chart_type: "bar",
    include_narrative: true
  }
```

**2. Backend processes custom report**
```
FastAPI enters custom_report_service.generate_custom_report():

Step 2a: Build and execute SQL
  SELECT c.regional_code, e.sector,
         SUM(c.contribution_amount) as total_contributions,
         ROUND(SUM(CASE WHEN c.payment_status = 'paid' THEN 1 ELSE 0 END) 
               / COUNT(*) * 100, 2) as collection_rate,
         COUNT(DISTINCT c.employer_id) as employer_count
  FROM contributions c
  JOIN employers e ON c.employer_id = e.id
  WHERE c.contribution_date BETWEEN '2026-01-01' AND '2026-03-31'
  GROUP BY c.regional_code, e.sector
  ORDER BY c.regional_code, total_contributions DESC

Step 2b: Execute against target database
  Returns structured data

Step 2c: Generate chart specification
  Chart config: { type: "bar", x: "regional_code", y: "total_contributions", 
                  color: "sector", title: "Q1 2026 by Region and Sector" }

Step 2d: Generate narrative (if requested)
  Call Groq API with report data
  Returns executive summary text

Step 2e: Return report data
  Return: { data: [...], chart: {...}, narrative: "..." }
```

**3. Frontend renders report preview**
```
React:
  - Renders data table
  - Renders chart with Recharts
  - Shows AI narrative
  - "Export as PDF" and "Export as Excel" buttons
```

**4. Export functionality**
```
PDF:
  React → GET /api/reports/{id}/download/pdf
  Backend: generate HTML → wkhtmltopdf → returns PDF bytes
  Frontend: const blob = new Blob([pdfBytes], { type: 'application/pdf' })
            const url = URL.createObjectURL(blob)
            window.open(url)

Excel:
  React → GET /api/reports/{id}/download/excel
  Backend: create_workbook() → openpyxl → returns XLSX bytes
  Frontend: download as .xlsx file
```

---

# 9. SCHEDULED REPORT EMAIL FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐     ┌────────────┐
│  APSchd. │────▶│  FastAPI  │────▶│  Generate  │────▶│  Brevo   │────▶│  Email     │
│  Timer   │     │  Runs     │     │  Report +  │     │  API     │     │  Inbox     │
│          │     │  ETL      │     │  HTML      │     │          │     │            │
└──────────┘     └──────────┘     └───────────┘     └──────────┘     └────────────┘
```

### Step-by-Step:

**1. Scheduler triggers at configured time (e.g., 06:00 daily)**

**2. Backend generates the report**
```
Step 2a: Run ETL for the user
Step 2b: Generate AI narrative
Step 2c: Generate professional HTML email
  Uses: generate_professional_html_email()
  Creates: 
    <!DOCTYPE html>
    <html>
      <body style="font-family: Arial, sans-serif;">
        <div class="header" style="background: #1a3a5c; color: white; padding: 20px;">
          <h1>Daily Analytics Report</h1>
        </div>
        <div class="content">
          <h2>Executive Summary</h2>
          <p>[AI Narrative here - clean text, no markdown]</p>
          
          <h2>KPI Overview</h2>
          <table style="border-collapse: collapse; width: 100%;">
            <tr><th>KPI</th><th>Value</th><th>Change</th></tr>
            <tr><td>Total Contributions</td><td>154,000,000</td><td>▲ 3.2%</td></tr>
          </table>
          
          <h2>Anomalies</h2>
          <p>[Anomaly descriptions]</p>
        </div>
        <div class="footer">
          <p>Generated by Enterprise Analytics Platform</p>
          <p><a href="{unsubscribe_url}">Unsubscribe</a></p>
        </div>
      </body>
    </html>
```

**3. Send email via Brevo API**
```
FastAPI → POST https://api.brevo.com/v3/smtp/email
  Headers: { api-key: "xkeysib-..." }
  Body: {
    sender: { name: "CNPS Analytics", email: "noreply@cnps.cm" },
    to: [{ email: "manager@cnps.cm" }],
    subject: "Daily Analytics Report - June 22, 2026",
    htmlContent: "<html>...</html>"
  }

Brevo response: { messageId: "<long-id>" }
```

**4. User receives email with professional report**

---

# 10. DATA VALIDATION FLOW

```
┌──────────┐     ┌───────────┐     ┌────────────┐     ┌──────────┐
│  ETL     │────▶│  FastAPI  │────▶│  Supabase  │────▶│  React   │
│  Runs    │     │ Validation│     │ validation │     │ Valid-   │
│          │     │  Service  │     │ _logs      │     │ ation    │
│          │     │           │     │            │     │ Page     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

### Validation Checks Performed During ETL:

**1. Staleness Check**
```
Query: SELECT MAX(contribution_date) FROM contributions
If MAX(date) < NOW() - 30 days:
  → Flag: WARNING - "No contributions in 30+ days for region DOU"
```

**2. Duplicate Detection**
```
Query: SELECT contribution_date, employee_id, amount, COUNT(*)
        FROM contributions
        GROUP BY contribution_date, employee_id, amount
        HAVING COUNT(*) > 1
If duplicates found:
  → Flag: CRITICAL - "5 duplicate contribution records detected"
```

**3. Completeness Check**
```
Query: SELECT COUNT(*) FROM insured_workers WHERE status IS NULL
If missing values:
  → Flag: WARNING - "15 workers missing employment status"
```

**4. Regional Coverage**
```
Query: SELECT r.code, COUNT(c.id) as contributions
        FROM regional_offices r
        LEFT JOIN contributions c ON r.code = c.regional_code
        WHERE c.contribution_date >= NOW() - 90 days
        GROUP BY r.code
If any region has 0 contributions in 90 days:
  → Flag: WARNING - "Maroua region has no data for 90+ days"
```

**5. Storage in Supabase**
```
INSERT INTO validation_logs (user_id, check_type, status, message, details, created_at)
VALUES ('user-uuid', 'staleness', 'warning', 'No contributions...', '{"region": "MAR"}', NOW())
```

**6. Display in Validation Page**
```
React → GET /api/validation/logs
  Returns: { logs: [{ check_type: "staleness", status: "warning", ... }] }

Renders:
  <div class={`alert ${log.status}`}>
    <AlertTriangle size={16} />
    <span>{log.check_type}: {log.message}</span>
  </div>
```

---

# 11. THEME TOGGLE FLOW

```
┌──────────┐     ┌───────────┐     ┌──────────────┐
│  User    │────▶│  React    │────▶│  CSS Variables│
│  Toggles │     │  App.jsx  │     │  Change      │
│  Theme   │     │           │     │  Everywhere  │
└──────────┘     └──────────┘     └──────────────┘
```

### Step-by-Step:

**1. User clicks sun/moon icon in navbar**

**2. React toggles dark/light state**
```
App.jsx:
  const [isDark, setIsDark] = useState(true)
  
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.remove('light-theme')
      localStorage.setItem('ea-theme', 'dark')
    } else {
      document.documentElement.classList.add('light-theme')
      localStorage.setItem('ea-theme', 'light')
    }
  }, [isDark])
```

**3. CSS variables switch globally**
```
:root (dark - default):
  --bg-color: #0a0f1a
  --surface-color: #141b2d
  --text-primary: #f0f4f8
  --text-secondary: #94a3b8
  --border-color: rgba(255,255,255,0.08)
  --primary-color: #3b82f6

.light-theme:
  --bg-color: #f8fafc
  --surface-color: #ffffff
  --text-primary: #0f172a
  --text-secondary: #64748b
  --border-color: rgba(0,0,0,0.1)
  --primary-color: #2563eb
```

**4. Every component using var(--bg-color) etc. updates instantly**

---

# 12. COMPLETE DATA FLOW MAP

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + Vite)                        │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Dashboard │  │Analyst   │  │Settings  │  │Admin     │  │Query/NLQ │  │
│  │Page      │  │Page      │  │Page      │  │Pages     │  │Page      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │             │         │
│  ┌────▼─────────────▼─────────────▼─────────────▼─────────────▼──────┐  │
│  │                    API Layer (lib/api.js)                         │  │
│  │  GET/POST/PUT/DELETE to /api/* with Bearer token                  │  │
│  └────────────────────────────┬───────────────────────────────────────┘  │
└───────────────────────────────┼──────────────────────────────────────────┘
                                │
                    HTTPS (localhost:8000)
                                │
┌───────────────────────────────┼──────────────────────────────────────────┐
│                    BACKEND (FastAPI + Uvicorn)                           │
│                                                                          │
│  ┌────────────────────────────▼──────────────────────────────────────┐  │
│  │                        main.py                                     │  │
│  │  - Authentication middleware (JWT decode)                          │  │
│  │  - SQL injection prevention                                        │  │
│  │  - CORS + security headers                                         │  │
│  │  - Rate limiting + CSRF protection                                 │  │
│  └──┬───────────┬───────────┬───────────┬───────────┬─────────────────┘  │
│     │           │           │           │           │                    │
│  ┌──▼──┐  ┌─────▼───┐  ┌──▼─────┐  ┌──▼───┐  ┌────▼─────┐           │
│  │ETL  │  │Analysis │  │NLQ     │  │Email │  │Semantic  │           │
│  │Svc  │  │Engine   │  │Service │  │Svc   │  │Router    │           │
│  └──┬──┘  └─────┬───┘  └──┬─────┘  └──┬───┘  └────┬─────┘           │
│     │           │         │           │           │                    │
│  ┌──▼───────────▼─────────▼───────────▼───────────▼───────────────┐  │
│  │                    connection_utils.py                          │  │
│  │  - detect_db_type() → normalize_credentials() → create_engine() │  │
│  │  - sqlalchemy_engine_kwargs() → enrich_connection_payload()     │  │
│  └────────────────────────────┬────────────────────────────────────┘  │
│                               │                                       │
│  ┌────────────────────────────▼────────────────────────────────────┐  │
│  │                    Oracle SQLAlchemy Engine                      │  │
│  │  oracle+oracledb://user:pass@host:1521/?service_name=ORCLPDB    │  │
│  │  connect_args: { tcp_connect_timeout: 10 }, pool_pre_ping: True │  │
│  └────────────────────────────┬────────────────────────────────────┘  │
└───────────────────────────────┼──────────────────────────────────────────┘
                                │
                    TCP/IP (Oracle SQL*Net Protocol)
                                │
┌───────────────────────────────┼──────────────────────────────────────────┐
│                    TARGET DATABASE (Oracle 19c PDB)                      │
│                                                                          │
│  ┌────────────────────────────▼──────────────────────────────────────┐  │
│  │                    ORCLPDB Pluggable Database                      │  │
│  │                                                                     │  │
│  │  Tables:                                                            │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ CONTRIBUTIONS     (150K rows - payment records)              │  │  │
│  │  │ EMPLOYERS         (500 rows - company info)                  │  │  │
│  │  │ PENSION_PAYMENTS  (2K rows - pension disbursements)          │  │  │
│  │  │ REGIONAL_OFFICES  (10 rows - regional HQs)                   │  │  │
│  │  │ WORKPLACE_ACCIDENTS (800 rows - AT/MP claims)                │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

SUPABASE (Cloud - Auth + Metadata Storage):
  ┌────────────────────────────────────────────────────────────────────┐
  │  auth.users         - User accounts + JWT authentication          │
  │  user_roles         - Role assignments (admin/manager/viewer)    │
  │  departments        - Department configuration                   │
  │  database_connections - Encrypted connection strings             │
  │  kpi_results        - Computed KPI values                        │
  │  anomaly_records    - Detected anomalies                         │
  │  daily_reports      - AI-generated narratives                    │
  │  analysis_runs      - Goal analysis history                      │
  │  validation_logs    - Data quality checks                        │
  │  semantic_templates - Global field definitions                   │
  │  semantic_fields    - Template fields                             │
  │  field_mappings     - User-specific column mappings              │
  │  notification_recipients - Email recipients                      │
  └────────────────────────────────────────────────────────────────────┘

GROQ AI (Cloud - LLM):
  ┌────────────────────────────────────────────────────────────────────┐
  │  Primary Model: qwen2.5-72b-instruct                              │
  │  Fallback Chain: gpt-oss-120b → qwen2.5-27b-instruct →           │
  │                  llama-3.1-8b-instant → gemma2-9b-it              │
  │  Purpose:                                                          │
  │  - Natural Language → SQL conversion (NLQ)                        │
  │  - Goal analysis interpretation (Analyst)                          │
  │  - Narrative/report generation (Dashboard)                         │
  │  - Auto-fallback on model decommission/deprecation                 │
  └────────────────────────────────────────────────────────────────────┘

BREVO (Cloud - Email):
  ┌────────────────────────────────────────────────────────────────────┐
  │  Purpose: Send scheduled reports via SMTP                         │
  │  Rate: 300 emails/day (free tier)                                  │
  └────────────────────────────────────────────────────────────────────┘
```

---

# 13. REQUEST FLOW PATTERNS

### Pattern A: Read Data (GET)
```
Browser → Vite Dev Server → React Component
  → useEffect() calls apiJson('/api/resource')
    → api.js: GET /api/resource with Bearer token
      → FastAPI route handler
        → require_role middleware (decodes JWT, checks role)
        → resolve_user_id (gets user from token)
        → Business logic (query Supabase or target DB)
        → Return JSON response
      ← FastAPI responds
    ← api.js returns parsed JSON
  ← React setState with data
  ← React re-renders with data
```

### Pattern B: Write Data (POST/PUT/DELETE)
```
Browser → React Form
  → User fills and submits
  → handleSubmit() calls apiFetch('/api/resource', { method: 'POST', body })
    → api.js: POST with JSON body and Bearer token
      → FastAPI route handler
        → require_role middleware
        → Validate input (Pydantic models)
        → Business logic (insert/update Supabase or target DB)
        → Log change to audit_service
        → Return success response
      ← FastAPI responds
    ← api.js returns result
  ← React shows success/error message
  ← React refetches data if needed
```

### Pattern C: Complex Query (NLQ/Analysis)
```
Browser → React NLQ input
  → User types question
  → handleSubmit() calls apiJson('/api/nlq', { method: 'POST', body })
    → FastAPI nlq_service.run_nlq()
      → Load schema from target DB (introspect tables)
      → Call Groq API: convert question → SQL
      → Validate SQL (read-only check)
      → Execute SQL against target DB
      → Return results
    ← FastAPI responds
  ← React receives data + columns
  ← React auto-generates chart + table
  ← React shows generated SQL (collapsible)
```

---

# 14. ERROR HANDLING PATTERNS

### Frontend Error Handling
```
api.js:
  try {
    const response = await fetch(url, options)
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error(`API Error [${url}]:`, error)
    throw error  // Propagate to component
  }

Component:
  catch (error) {
    setError(error.message)
    // OR
    alert(`Operation failed: ${error.message}`)
  }
```

### Backend Error Handling
```
FastAPI:
  @app.exception_handler(Exception)
  async def general_exception_handler(request, exc):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(
      status_code=500,
      content={ "detail": "Internal server error" }
    )

  Route handler:
    try:
      result = await do_something()
      return result
    except HTTPException:
      raise  # Re-raise known HTTP errors
    except Exception as e:
      logger.error(f"Route failed: {e}")
      raise HTTPException(status_code=500, detail=str(e))
```

### Database Error Handling
```
connection_utils.py:
  try:
    engine = create_engine(url)
    with engine.connect() as conn:
      conn.execute(text("SELECT 1"))
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": f"Database Error: {str(e)}"}
  finally:
    if engine: engine.dispose()
```

---

# 15. DEPENDENCY MAP

```
┌─────────────────────────────────────────────────────────────────────┐
│                        System Dependencies                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  FRONTEND:                                                           │
│    React 18 → React Router 6 → Recharts 2 → Vite 5                  │
│    → lucide-react (icons) → Supabase JS client                       │
│                                                                     │
│  BACKEND:                                                            │
│    FastAPI → Uvicorn → SQLAlchemy 2.0 → oracledb (Oracle driver)    │
│    → Supabase Python client → httpx (HTTP client)                   │
│    → APScheduler (cron jobs) → Groq SDK (AI/LLM)                    │
│    → openpyxl (Excel export) → cryptography (AES encryption)        │
│    → python-dotenv (env management)                                  │
│                                                                     │
│  EXTERNAL SERVICES:                                                  │
│    Supabase (Auth + PostgreSQL + Storage)                            │
│    Groq Cloud (LLM: qwen2.5-72b-instruct with auto-fallback)       │
│    Brevo (Email delivery)                                            │
│    Target Database (Oracle 19c, MySQL, PostgreSQL, SQLite, etc.)     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

**Last Updated:** 2026-06-22  
**Version:** 2.0.0  
**Status:** Complete ✅