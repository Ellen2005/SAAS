# Customer Net Promoter Score (CNPS) Manual Testing & Simulation Guide — MySQL Edition

This guide provides a comprehensive manual testing walk-through for a Customer Net Promoter Score (CNPS) analytical pipeline using a bulky, 1,589-record MySQL database. It simulates a corporate customer success department with two distinct operational roles:

1. **The System Administrator (Admin)**: Declares the required global semantic metrics, builds the template schema, and governs the standards.
2. **The Business Analyst (Manager)**: Connects the data source, triggers schema-to-dashboard sync, configures business tone directives, and runs natural language queries to gain insights.

---

## 1. Prerequisites & Database Setup

To perform the manual testing, you need to generate and populate the MySQL database.

### Step 1.1: Create MySQL Database and Tables

1. Open MySQL command line or a MySQL client (e.g., MySQL Workbench, phpMyAdmin).
2. Create a new database:
   ```sql
   CREATE DATABASE cnps_sample;
   USE cnps_sample;
   ```

3. Create the tables:
   ```sql
   CREATE TABLE customers (
     id INT AUTO_INCREMENT PRIMARY KEY,
     name VARCHAR(255) NOT NULL,
     email VARCHAR(255) UNIQUE NOT NULL,
     company_type ENUM('Enterprise', 'Mid-Market', 'SMB') DEFAULT 'Mid-Market',
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE nps_feedback (
     id INT AUTO_INCREMENT PRIMARY KEY,
     customer_id INT NOT NULL,
     score INT CHECK (score >= 0 AND score <= 10),
     feedback_text TEXT,
     segment VARCHAR(100),
     channel ENUM('Email', 'Web', 'In-App') DEFAULT 'Web',
     submitted_at DATE NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
     INDEX idx_submitted_at (submitted_at),
     INDEX idx_customer_id (customer_id)
   );

   CREATE VIEW v_nps_summary AS
   SELECT 
     DATE(n.submitted_at) as nps_date,
     COUNT(*) as total_responses,
     AVG(CASE WHEN n.score >= 9 THEN 1 ELSE 0 END) * 100 as promoters_pct,
     AVG(CASE WHEN n.score >= 7 AND n.score <= 8 THEN 1 ELSE 0 END) * 100 as passives_pct,
     AVG(CASE WHEN n.score <= 6 THEN 1 ELSE 0 END) * 100 as detractors_pct,
     (AVG(CASE WHEN n.score >= 9 THEN 1 ELSE 0 END) - AVG(CASE WHEN n.score <= 6 THEN 1 ELSE 0 END)) * 100 as nps_score
   FROM nps_feedback n
   GROUP BY DATE(n.submitted_at)
   ORDER BY nps_date;
   ```

### Step 1.2: Populate with Sample Data

Run the following SQL to insert 120 customers and 1,589 NPS feedback records:

```sql
-- Insert 120 customers
INSERT INTO customers (name, email, company_type) VALUES
('Acme Corp', 'contact@acme.com', 'Enterprise'),
('Beta Industries', 'support@beta.com', 'Mid-Market'),
('Gamma Solutions', 'info@gamma.com', 'SMB'),
('Delta Tech', 'admin@delta.com', 'Enterprise'),
('Epsilon Partners', 'hello@epsilon.com', 'Mid-Market');
-- ... (repeat pattern for 120 total customers)

-- Insert 1,589 NPS feedback records spanning the last 30 days
INSERT INTO nps_feedback (customer_id, score, feedback_text, segment, channel, submitted_at) 
SELECT 
  (ABS(RAND() * 120) + 1) as customer_id,
  FLOOR(RAND() * 11) as score,
  CASE 
    WHEN FLOOR(RAND() * 11) >= 9 THEN 'Great product, easy to use.'
    WHEN FLOOR(RAND() * 11) >= 7 THEN 'Good experience overall.'
    ELSE 'Had some issues but support helped.'
  END as feedback_text,
  CASE WHEN RAND() > 0.5 THEN 'Enterprise' ELSE 'Mid-Market' END as segment,
  CASE FLOOR(RAND() * 3) 
    WHEN 0 THEN 'Email'
    WHEN 1 THEN 'Web'
    ELSE 'In-App'
  END as channel,
  DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 30) DAY) as submitted_at
FROM (
  SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION 
  SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION
  SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION
  SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION SELECT 20
) t
CROSS JOIN (
  SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION
  SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
) t2
CROSS JOIN (
  SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION
  SELECT 6 UNION SELECT 7 UNION SELECT 8
) t3
LIMIT 1589;
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

In this phase, you switch to the **Manager** role to connect the MySQL database, trigger sync, and generate reports.

### Step 3.1: Connecting the Database

1. Navigate to the **Settings** page.
2. Under **Database Connection**, select **MySQL** as the Database Type.
3. Enter the connection string:
   ```txt
   mysql+pymysql://root:password@localhost:3306/cnps_sample
   ```
   *(Replace `root` and `password` with your actual MySQL credentials)*
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
   - *Status indication*: The button text changes to `Syncing Schema...` as it introspects the MySQL database, suggests field maps, runs suggested quality checks, and generates summaries.
4. **Verification**: When complete, a beautiful, high-contrast dismissal banner appears at the top:
   `"Schema Sync Successful! Successfully mapped and synced 10 KPI(s) from your connected database. (Skipped 0, Failed 0)"`
5. Click **Dismiss** to close the banner.
6. The **7-Day Forecast** chart is now visible, rendering real, non-mock mathematical calculations derived directly from customer feedback volumes.

---

## 5. Phase 4: Natural Language Query Testing

### Step 4.1: Run NLQ Queries

1. Navigate to the **Query** page (Natural Language Query).
2. Try the following queries:
   - `"How many customers gave us a score of 9 or higher?"`
   - `"Show me the NPS trend over the last 30 days"`
   - `"Which channel receives the most feedback?"`
   - `"What's the average NPS score by segment?"`
3. Verify that the assistant shows:
   - Generated SQL query
   - Result table with data
   - Optional chart visualization

---

## 6. Verification: AI-Driven Narrative Performance

The newly generated **AI Narrative** now dynamically adapts to the data:
- **No Mock KPIs**: Legacy items like `net_revenue` are completely hidden.
- **No Warning Noise**: The narrative completely avoids boilerplate warnings.
- **Real Data Analysis**: The narrative summarizes the operational context of your CNPS database.

### Expected Narrative Example:
> **Connected Database Overview — Staging Run**
> 
> Your MySQL database contains **120 customers** with **1,589 NPS feedback records** spanning the last 30 days. The average NPS score is **68**, with **42% promoters** (score 9-10), **28% passives** (score 7-8), and **30% detractors** (score 0-6). Enterprise customers show higher satisfaction (**NPS 72**) compared to Mid-Market (**NPS 65**). The primary feedback channel is Web (**45% of responses**).

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Verify MySQL is running and credentials are correct |
| "No KPIs found" | Run the "Sync Schema" button on the Dashboard to map fields |
| "Query error" | Check that table names and column names match your MySQL schema |
| "Empty charts" | Ensure at least 7 days of data is present in `nps_feedback` table |

---

## 8. Advanced: Custom Analysis Queries

Once connected, you can run more complex queries:

```sql
-- NPS by company type over time
SELECT 
  c.company_type,
  DATE(n.submitted_at) as feedback_date,
  COUNT(*) as count,
  AVG(n.score) as avg_score
FROM nps_feedback n
JOIN customers c ON n.customer_id = c.id
GROUP BY c.company_type, DATE(n.submitted_at)
ORDER BY feedback_date DESC;

-- Top detractor feedback
SELECT 
  c.name,
  n.score,
  n.feedback_text,
  n.submitted_at
FROM nps_feedback n
JOIN customers c ON n.customer_id = c.id
WHERE n.score <= 6
ORDER BY n.submitted_at DESC
LIMIT 10;
```

Try these in the **Query** page using natural language!
