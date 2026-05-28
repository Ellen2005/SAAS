# Customer Net Promoter Score (CNPS) Manual Testing & Simulation Guide — PostgreSQL Edition

This guide provides a comprehensive manual testing walk-through for a Customer Net Promoter Score (CNPS) analytical pipeline using a bulky, 1,589-record PostgreSQL database. It simulates a corporate customer success department with two distinct operational roles:

1. **The System Administrator (Admin)**: Declares the required global semantic metrics, builds the template schema, and governs the standards.
2. **The Business Analyst (Manager)**: Connects the data source, triggers schema-to-dashboard sync, configures business tone directives, and runs natural language queries to gain insights.

---

## 1. Prerequisites & Database Setup

To perform the manual testing, you need to generate and populate the PostgreSQL database.

### Step 1.1: Create PostgreSQL Database and Tables

1. Open a PostgreSQL terminal or use a client (e.g., pgAdmin, DBeaver).
2. Create a new database:
   ```bash
   createdb cnps_sample
   psql -d cnps_sample
   ```

3. Create the schema and tables:
   ```sql
   -- Create ENUM types
   CREATE TYPE company_type_enum AS ENUM ('Enterprise', 'Mid-Market', 'SMB');
   CREATE TYPE channel_enum AS ENUM ('Email', 'Web', 'In-App');

   -- Create customers table
   CREATE TABLE customers (
     id SERIAL PRIMARY KEY,
     name VARCHAR(255) NOT NULL,
     email VARCHAR(255) UNIQUE NOT NULL,
     company_type company_type_enum DEFAULT 'Mid-Market',
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Create nps_feedback table
   CREATE TABLE nps_feedback (
     id SERIAL PRIMARY KEY,
     customer_id INT NOT NULL,
     score INT CHECK (score >= 0 AND score <= 10),
     feedback_text TEXT,
     segment VARCHAR(100),
     channel channel_enum DEFAULT 'Web',
     submitted_at DATE NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
   );

   -- Create indexes for performance
   CREATE INDEX idx_nps_feedback_submitted_at ON nps_feedback(submitted_at);
   CREATE INDEX idx_nps_feedback_customer_id ON nps_feedback(customer_id);
   CREATE INDEX idx_customers_created_at ON customers(created_at);

   -- Create materialized view for NPS summary
   CREATE MATERIALIZED VIEW v_nps_summary AS
   SELECT 
     DATE(n.submitted_at) as nps_date,
     COUNT(*) as total_responses,
     ROUND(100.0 * SUM(CASE WHEN n.score >= 9 THEN 1 ELSE 0 END) / COUNT(*), 2) as promoters_pct,
     ROUND(100.0 * SUM(CASE WHEN n.score >= 7 AND n.score <= 8 THEN 1 ELSE 0 END) / COUNT(*), 2) as passives_pct,
     ROUND(100.0 * SUM(CASE WHEN n.score <= 6 THEN 1 ELSE 0 END) / COUNT(*), 2) as detractors_pct,
     ROUND(100.0 * (SUM(CASE WHEN n.score >= 9 THEN 1 ELSE 0 END) - SUM(CASE WHEN n.score <= 6 THEN 1 ELSE 0 END)) / COUNT(*), 2) as nps_score
   FROM nps_feedback n
   GROUP BY DATE(n.submitted_at)
   ORDER BY nps_date DESC;
   ```

### Step 1.2: Populate with Sample Data

Run the following SQL to insert 120 customers and 1,589 NPS feedback records:

```sql
-- Insert 120 customers using generate_series
INSERT INTO customers (name, email, company_type) 
SELECT 
  'Customer ' || i::text as name,
  'customer' || i::text || '@example.com' as email,
  (ARRAY['Enterprise', 'Mid-Market', 'SMB'])[((i-1) % 3) + 1]::company_type_enum as company_type
FROM generate_series(1, 120) as i;

-- Insert 1,589 NPS feedback records spanning the last 30 days
INSERT INTO nps_feedback (customer_id, score, feedback_text, segment, channel, submitted_at)
SELECT 
  (i % 120) + 1 as customer_id,
  (random() * 11)::int as score,
  CASE 
    WHEN (random() * 11)::int >= 9 THEN 'Great product, easy to use.'
    WHEN (random() * 11)::int >= 7 THEN 'Good experience overall.'
    ELSE 'Had some issues but support helped.'
  END as feedback_text,
  CASE WHEN random() > 0.5 THEN 'Enterprise' ELSE 'Mid-Market' END as segment,
  (ARRAY['Email', 'Web', 'In-App'])[((i-1) % 3) + 1]::channel_enum as channel,
  CURRENT_DATE - (random() * 30)::int as submitted_at
FROM generate_series(1, 1589) as i;

-- Verify the data
REFRESH MATERIALIZED VIEW v_nps_summary;
```

**Verification**:
- Run: `SELECT COUNT(*) FROM customers;` — Should show **120**
- Run: `SELECT COUNT(*) FROM nps_feedback;` — Should show **1589**
- Run: `SELECT * FROM v_nps_summary LIMIT 5;` — Should show NPS trends

---

## 2. Phase 1: The Administrator's Workflow (Governance)

In this phase, you log in as the **Admin** to configure the global KPI metrics and definitions that govern the entire department.

### Step 2.1: Declaring the Customer Satisfaction KPI Template

1. Open the web app and navigate to **Templates / Global Mappings** (under the Admin sidebar).
2. Click **Create Template** and name it `Customer Feedback Core`.
3. Declare the following fields under the semantic schema:

| Field Name | Data Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `score` | `integer` | **Yes** | NPS Score between 0 and 10 |
| `feedback_text` | `text` | No | Customer written feedback |
| `segment` | `text` | No | Customer category (Enterprise, Mid-Market, SMB) |
| `channel` | `text` | No | Submitting channel (Email, Web, In-App) |
| `submitted_at` | `date` | **Yes** | Date when the rating was submitted |

---

## 3. Phase 2: The Manager's Workflow (Integration & Analysis)

In this phase, you switch to the **Manager** role to connect the PostgreSQL database, trigger sync, and generate reports.

### Step 3.1: Connecting the Database

1. Navigate to the **Settings** page.
2. Under **Database Connection**, select **PostgreSQL** as the Database Type.
3. Enter the connection string:
   ```txt
   postgresql://postgres:password@localhost:5432/cnps_sample
   ```
   *(Replace `postgres` and `password` with your actual PostgreSQL credentials; use `localhost` or your server IP)*
4. Click **Test Connection**. You should see a green badge indicating:
   `"Connection verified!"`
5. Click **Save Details** to store the credentials.

### Step 3.2: Setting Strategic Narrative Instructions

1. Scroll down to **User Preferences / Report Configuration**.
2. Select your preferred tone (e.g., **Insight-Driven**).
3. Under **Strategic Analysis Instruction**, input the following focus:
   ```txt
   Analyze the overall sentiment. Specifically focus on whether Enterprise customers are happy with speed, stability, and dashboard performance. Identify any detractors complaining about bugs or UI.
   ```
4. Click **Save Preferences**.

---

## 4. Phase 3: Dashboard Schema Sync (One-Click Dashboard Update)

With the new feature, schema synchronization is fully automated!

### Step 4.1: Direct Dashboard Synchronization

1. Go back to the **Dashboard** page.
2. Note that the **7-Day Forecast** chart is intelligently hidden because there is no timeseries KPI feed loaded yet.
3. Click the new primary button: **Sync Schema** (styled with a smooth purple linear gradient).
   - *Micro-animation*: The refresh icon will spin dynamically.
   - *Status indication*: The button text changes to `Syncing Schema...` as it introspects the PostgreSQL database, suggests field maps, runs suggested quality checks, and generates summaries.
4. **Verification**: When complete, a beautiful, high-contrast dismissal banner appears at the top:
   `"Schema Sync Successful! Successfully mapped and synced 10 KPI(s) from your connected database. (Skipped 0, Failed 0)"`
5. Click **Dismiss** to close the banner.
6. The **7-Day Forecast** chart is now visible, rendering real, non-mock mathematical calculations derived directly from customer feedback volumes.

---

## 5. Phase 4: Natural Language Query Testing

### Step 5.1: Run NLQ Queries

1. Navigate to the **Query** page (Natural Language Query).
2. Try the following queries:
   - `"How many customers gave us a score of 9 or higher?"`
   - `"Show me the NPS trend over the last 30 days"`
   - `"Which channel receives the most feedback?"`
   - `"What's the average NPS score by segment?"`
   - `"List customers who gave a score of 10"`
3. Verify that the assistant shows:
   - Generated SQL query (PostgreSQL syntax)
   - Result table with data
   - Optional chart visualization

---

## 6. Verification: AI-Driven Narrative Performance

The newly generated **AI Narrative** now dynamically adapts to the data:
- **No Mock KPIs**: Legacy items like `net_revenue` are completely hidden.
- **No Warning Noise**: The narrative completely avoids boilerplate warnings.
- **Real Data Analysis**: The narrative summarizes the operational context of your CNPS database.
- **PostgreSQL-Specific Insights**: Uses materialized views and advanced PostgreSQL functions for performance.

### Expected Narrative Example:
> **Connected Database Overview — Staging Run**
> 
> Your PostgreSQL database contains **120 customers** with **1,589 NPS feedback records** spanning the last 30 days. The average NPS score is **68**, with **42% promoters** (score 9-10), **28% passives** (score 7-8), and **30% detractors** (score 0-6). Enterprise customers show higher satisfaction (**NPS 72**) compared to Mid-Market (**NPS 65**). The primary feedback channel is Web (**45% of responses**).

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| "connection refused" | Verify PostgreSQL is running: `psql --version` and check credentials |
| "database does not exist" | Create it: `createdb cnps_sample` |
| "permission denied for schema public" | Check user privileges: `GRANT ALL ON SCHEMA public TO your_user;` |
| "No KPIs found" | Run the "Sync Schema" button on the Dashboard to map fields |
| "Materialized view not found" | Run: `REFRESH MATERIALIZED VIEW v_nps_summary;` |
| "Empty charts" | Ensure at least 7 days of data: `SELECT MIN(submitted_at), MAX(submitted_at) FROM nps_feedback;` |

---

## 8. Advanced: Custom Analysis Queries

Once connected, you can run more complex queries:

```sql
-- NPS by company type over time (with window functions)
SELECT 
  c.company_type,
  DATE(n.submitted_at) as feedback_date,
  COUNT(*) as count,
  ROUND(AVG(n.score::numeric), 2) as avg_score,
  ROW_NUMBER() OVER (PARTITION BY c.company_type ORDER BY DATE(n.submitted_at) DESC) as rank_by_type
FROM nps_feedback n
JOIN customers c ON n.customer_id = c.id
GROUP BY c.company_type, DATE(n.submitted_at)
ORDER BY feedback_date DESC;

-- Top detractor feedback with customer details
SELECT 
  c.name,
  c.company_type,
  n.score,
  n.feedback_text,
  n.channel,
  n.submitted_at
FROM nps_feedback n
JOIN customers c ON n.customer_id = c.id
WHERE n.score <= 6
ORDER BY n.submitted_at DESC
LIMIT 10;

-- NPS cohort analysis
SELECT 
  DATE_TRUNC('week', n.submitted_at)::date as week_start,
  c.company_type,
  COUNT(*) as response_count,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n.score) as median_score
FROM nps_feedback n
JOIN customers c ON n.customer_id = c.id
GROUP BY DATE_TRUNC('week', n.submitted_at), c.company_type
ORDER BY week_start DESC, company_type;
```

Try these in the **Query** page using natural language!

---

## 9. Performance Optimization Tips

- **For large datasets**: Create additional indexes on frequently queried columns:
  ```sql
  CREATE INDEX idx_nps_feedback_score ON nps_feedback(score);
  CREATE INDEX idx_nps_feedback_channel ON nps_feedback(channel);
  ```

- **Monitor query performance**:
  ```sql
  EXPLAIN ANALYZE SELECT ... FROM nps_feedback WHERE score >= 9;
  ```

- **Refresh materialized view periodically**:
  ```sql
  REFRESH MATERIALIZED VIEW CONCURRENTLY v_nps_summary;
  ```
