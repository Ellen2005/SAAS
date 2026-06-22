# CNPS Oracle 19C - Power BI Equivalent Test Scenarios
## Complete SQL Test Queries for SAAS System

This document provides Power BI-style business scenarios mapped to SQL queries that work with the CNPS Oracle 19C database. Each scenario shows the Power BI equivalent and the SQL query to paste into SAAS "Ask Your Data" or Custom Chart builder.

---

## 1. Sales Dashboard - Product Sales by Region and Month

### Power BI Equivalent: Line Chart + Bar Chart + Map
**Business Question:** Track product sales by region and month.

```sql
SELECT 
    r.region_name,
    TO_CHAR(s.sale_date, 'YYYY-MM') AS month,
    SUM(s.amount) AS total_sales,
    COUNT(s.id) AS quantity_sold,
    AVG(s.amount) AS avg_sale_value
FROM sales s
JOIN regions r ON s.region_id = r.id
GROUP BY r.region_name, TO_CHAR(s.sale_date, 'YYYY-MM')
ORDER BY r.region_name, month;
```

**SAAS NLQ:** "Show me total sales by region per month as a bar chart"

---

## 2. Marketing Campaign Performance

### Power BI Equivalent: Funnel Chart + Trend Line
**KPIs:** Leads Generated, Conversion Rate, Cost per Lead, ROI

```sql
SELECT 
    c.campaign_name,
    c.leads_generated,
    c.conversions,
    ROUND((c.conversions / NULLIF(c.leads_generated, 0)) * 100, 2) AS conversion_rate,
    c.total_spend,
    ROUND(c.total_spend / NULLIF(c.leads_generated, 0), 2) AS cost_per_lead,
    c.revenue_generated,
    ROUND(((c.revenue_generated - c.total_spend) / NULLIF(c.total_spend, 0)) * 100, 2) AS roi_percentage
FROM campaigns c
ORDER BY c.roi_percentage DESC;
```

**SAAS NLQ:** "Show marketing campaign performance with conversion funnel"

**Power BI Visual:** Funnel Chart → Lead → Click → Conversion → Purchase

```sql
-- Funnel Analysis
SELECT 'Visitors' AS stage, COUNT(*) AS count FROM website_visits
UNION ALL
SELECT 'Sign-ups', COUNT(*) FROM users WHERE created_at >= SYSDATE - 30
UNION ALL
SELECT 'Activations', COUNT(*) FROM user_activities WHERE first_action_date IS NOT NULL
UNION ALL
SELECT 'Purchases', COUNT(*) FROM orders WHERE order_date >= SYSDATE - 30;
```

---

## 3. Customer Retention / Churn Dashboard (SaaS)

### Power BI Equivalent: Cohort Analysis + Retention Funnel
**KPIs:** Churn Rate, Retention Rate, Active Users, MRR, CLV

```sql
-- Monthly Recurring Revenue (MRR) Trend
SELECT 
    TO_CHAR(subscription_date, 'YYYY-MM') AS month,
    COUNT(DISTINCT customer_id) AS active_customers,
    SUM(monthly_fee) AS mrr,
    ROUND(AVG(monthly_fee), 2) AS arpu
FROM subscriptions
WHERE status = 'active'
GROUP BY TO_CHAR(subscription_date, 'YYYY-MM')
ORDER BY month;

-- Churn Rate by Month
SELECT 
    TO_CHAR(churn_date, 'YYYY-MM') AS month,
    COUNT(*) AS churned_customers,
    LAG(COUNT(*), 1) OVER (ORDER BY TO_CHAR(churn_date, 'YYYY-MM')) AS prev_month_churn,
    ROUND((COUNT(*) - LAG(COUNT(*), 1) OVER (ORDER BY TO_CHAR(churn_date, 'YYYY-MM'))) 
        / NULLIF(LAG(COUNT(*), 1) OVER (ORDER BY TO_CHAR(churn_date, 'YYYY-MM')), 0) * 100, 2) AS churn_growth_pct
FROM customer_churn
GROUP BY TO_CHAR(churn_date, 'YYYY-MM')
ORDER BY month;
```

---

## 4. Sales Performance - Regional Sales Team

### Power BI Equivalent: Leaderboard + Map + Gauge Chart
**KPIs:** Total Sales, Target Achievement %, Top Reps, Monthly Growth

```sql
-- Sales Leaderboard
SELECT 
    e.first_name || ' ' || e.last_name AS sales_rep,
    e.region,
    SUM(s.amount) AS total_sales,
    e.sales_target,
    ROUND((SUM(s.amount) / NULLIF(e.sales_target, 0)) * 100, 2) AS target_achievement_pct,
    RANK() OVER (ORDER BY SUM(s.amount) DESC) AS rank
FROM sales s
JOIN employees e ON s.sales_rep_id = e.id
WHERE s.sale_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY e.first_name, e.last_name, e.region, e.sales_target
ORDER BY total_sales DESC;

-- Monthly Growth
SELECT 
    TO_CHAR(sale_date, 'YYYY-MM') AS month,
    SUM(amount) AS monthly_sales,
    LAG(SUM(amount), 1) OVER (ORDER BY TO_CHAR(sale_date, 'YYYY-MM')) AS prev_month,
    ROUND((SUM(amount) - LAG(SUM(amount), 1) OVER (ORDER BY TO_CHAR(sale_date, 'YYYY-MM'))) 
        / NULLIF(LAG(SUM(amount), 1) OVER (ORDER BY TO_CHAR(sale_date, 'YYYY-MM')), 0) * 100, 2) AS growth_pct
FROM sales
WHERE sale_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY TO_CHAR(sale_date, 'YYYY-MM')
ORDER BY month;
```

---

## 5. Funnel Analysis - Customer Journey

### Power BI Equivalent: Funnel Chart + Drop-off Analysis
**Stages:** Visitors → Sign-ups → Activation → Purchase

```sql
-- Complete Funnel with Drop-off Rates
WITH funnel AS (
    SELECT '1-Website Visitors' AS stage, COUNT(*) AS count FROM page_visits WHERE visit_date >= SYSDATE - 30
    UNION ALL
    SELECT '2-Sign-Ups', COUNT(*) FROM users WHERE created_at >= SYSDATE - 30
    UNION ALL
    SELECT '3-Activations', COUNT(*) FROM user_preferences WHERE setup_completed = 'Y' AND created_at >= SYSDATE - 30
    UNION ALL
    SELECT '4-First Purchase', COUNT(*) FROM orders WHERE order_date >= SYSDATE - 30
)
SELECT 
    stage,
    count,
    LAG(count, 1) OVER (ORDER BY stage) AS previous_stage_count,
    ROUND(count / NULLIF(LAG(count, 1) OVER (ORDER BY stage), 0) * 100, 2) AS conversion_pct,
    100 - ROUND(count / NULLIF(LAG(count, 1) OVER (ORDER BY stage), 0) * 100, 2) AS dropoff_pct
FROM funnel;
```

---

## 6. Revenue Drop Analysis - Root Cause

### Power BI Equivalent: Waterfall Chart + Variance Analysis
**Business Question:** Why did revenue drop suddenly?

```sql
-- Revenue Variance by Region (Waterfall)
SELECT 
    'Total' AS dimension,
    'Previous Period' AS label,
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -2) AND ADD_MONTHS(SYSDATE, -1) THEN amount ELSE 0 END) AS previous_value,
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -1) AND SYSDATE THEN amount ELSE 0 END) AS current_value,
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -1) AND SYSDATE THEN amount ELSE 0 END) -
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -2) AND ADD_MONTHS(SYSDATE, -1) THEN amount ELSE 0 END) AS variance
FROM sales
UNION ALL
SELECT 'Region', region_name,
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -2) AND ADD_MONTHS(SYSDATE, -1) THEN amount ELSE 0 END),
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -1) AND SYSDATE THEN amount ELSE 0 END),
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -1) AND SYSDATE THEN amount ELSE 0 END) -
    SUM(CASE WHEN sale_date BETWEEN ADD_MONTHS(SYSDATE, -2) AND ADD_MONTHS(SYSDATE, -1) THEN amount ELSE 0 END) AS variance
FROM sales s
JOIN regions r ON s.region_id = r.id
GROUP BY region_name
ORDER BY dimension, variance;
```

---

## 7. CNPS-Specific: Contribution Collection by Region

### Power BI Equivalent: Map + Bar Chart
**KPIs:** Collection Rate, Total Contributions, Employer Compliance

```sql
-- Contribution Collection by Region (Last 6 months)
SELECT 
    r.region_name,
    COUNT(DISTINCT e.id) AS total_employers,
    SUM(c.amount_due) AS total_due,
    SUM(c.amount_paid) AS total_collected,
    ROUND((SUM(c.amount_paid) / NULLIF(SUM(c.amount_due), 0)) * 100, 2) AS collection_rate_pct,
    SUM(c.amount_due) - SUM(c.amount_paid) AS outstanding_balance,
    ROUND(AVG(c.days_to_payment), 1) AS avg_days_to_pay
FROM contributions c
JOIN employers e ON c.employer_id = e.id
JOIN regions r ON e.region_id = r.id
WHERE c.due_date >= ADD_MONTHS(SYSDATE, -6)
GROUP BY r.region_name
ORDER BY collection_rate_pct DESC;
```

---

## 8. CNPS Pension Disbursement Analysis

### Power BI Equivalent: Area Chart + KPI Cards
**KPIs:** Total Disbursed, Beneficiaries, Avg Pension, Processing Time

```sql
-- Pension Disbursement Monthly Trend
SELECT 
    TO_CHAR(p.disbursement_date, 'YYYY-MM') AS month,
    COUNT(DISTINCT p.beneficiary_id) AS total_beneficiaries,
    SUM(p.amount) AS total_disbursed,
    ROUND(AVG(p.amount), 2) AS avg_pension_amount,
    ROUND(AVG(p.processing_days), 1) AS avg_processing_days
FROM pension_disbursements p
WHERE p.disbursement_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY TO_CHAR(p.disbursement_date, 'YYYY-MM')
ORDER BY month;
```

---

## 9. Workplace Accident (AT/MP) Claims Analysis

### Power BI Equivalent: Radar Chart + Trend Lines
**KPIs:** Claims Count, Severity Rate, Avg Settlement, Processing Time

```sql
-- AT/MP Claims by Severity and Region
SELECT 
    r.region_name,
    a.severity_level,
    COUNT(*) AS claim_count,
    ROUND(AVG(a.settlement_amount), 2) AS avg_settlement,
    ROUND(AVG(a.processing_days), 1) AS avg_processing_days,
    SUM(a.settlement_amount) AS total_settlement
FROM atmp_claims a
JOIN employers e ON a.employer_id = e.id
JOIN regions r ON e.region_id = r.id
WHERE a.incident_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY r.region_name, a.severity_level
ORDER BY claim_count DESC;
```

---

## 10. Executive Dashboard - All KPIs in One View

### Power BI Equivalent: Composite Dashboard
**Purpose:** Executive overview with all critical metrics

```sql
-- Executive KPI Summary
SELECT 
    'Total Contributions (YTD)' AS kpi_name,
    TO_CHAR(SUM(amount_paid), 'FML999G999G999') AS kpi_value,
    ROUND((SUM(amount_paid) / NULLIF(SUM(amount_due), 0)) * 100, 2) AS metric
FROM contributions
WHERE due_date >= TRUNC(SYSDATE, 'YEAR')
UNION ALL
SELECT 'Active Employers', TO_CHAR(COUNT(*), 'FM999G999'), NULL
FROM employers WHERE status = 'ACTIVE'
UNION ALL
SELECT 'Total Beneficiaries', TO_CHAR(COUNT(*), 'FM999G999'), NULL
FROM beneficiaries WHERE status = 'ACTIVE'
UNION ALL
SELECT 'Pension Disbursed (YTD)', TO_CHAR(SUM(amount), 'FML999G999G999'), NULL
FROM pension_disbursements
WHERE disbursement_date >= TRUNC(SYSDATE, 'YEAR')
UNION ALL
SELECT 'Claims Pending', TO_CHAR(COUNT(*), 'FM999'), NULL
FROM atmp_claims WHERE status = 'PENDING'
UNION ALL
SELECT 'Collection Rate', NULL, 
    ROUND((SUM(CASE WHEN c.status = 'PAID' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)) * 100, 2)
FROM contributions c
WHERE c.due_date BETWEEN ADD_MONTHS(SYSDATE, -12) AND SYSDATE;
```

---

## 11. Cohort Analysis - Employer Retention

### Power BI Equivalent: Cohort Matrix
**Business Question:** Do employers stay active after their first contribution?

```sql
-- Employer Retention Cohort
WITH cohorts AS (
    SELECT 
        e.id,
        TO_CHAR(e.first_contribution_date, 'YYYY-MM') AS cohort_month,
        EXTRACT(MONTH FROM (c.due_date - e.first_contribution_date)) AS month_offset
    FROM employers e
    JOIN contributions c ON e.id = c.employer_id
    WHERE e.first_contribution_date IS NOT NULL
)
SELECT 
    cohort_month,
    COUNT(DISTINCT id) AS cohort_size,
    COUNT(DISTINCT CASE WHEN month_offset >= 1 THEN id END) AS month_1,
    COUNT(DISTINCT CASE WHEN month_offset >= 3 THEN id END) AS month_3,
    COUNT(DISTINCT CASE WHEN month_offset >= 6 THEN id END) AS month_6,
    COUNT(DISTINCT CASE WHEN month_offset >= 12 THEN id END) AS month_12
FROM cohorts
GROUP BY cohort_month
ORDER BY cohort_month;
```

---

## 12. How to Use These Queries in SAAS

### Option A: Ask Your Data (NLQ)
1. Go to **Ask Your Data**
2. Type natural language: "Show total contributions by region for last 6 months as a bar chart"
3. The AI generates the SQL automatically

### Option B: Custom Chart
1. Select **Chart Type** from the dropdown:
   - `bar` → Bar Chart (vertical)
   - `line` → Line Chart (trends)
   - `pie` → Pie Chart (distribution)
   - `area` → Area Chart (cumulative)
   - `funnel` → Funnel Chart (conversion stages)
   - `waterfall` → Waterfall Chart (variance)
   - `radar` → Radar Chart (multi-metric comparison)
   - `scatter` → Scatter Plot (correlation)
   - `treemap` → Treemap (hierarchical)
   - `groupedBar` → Grouped Bar Chart (comparison)
   - `stackedBar` → Stacked Bar Chart (composition)
   - `composed` → Composed (bar + line)
   - `radialBar` → Radial Bar Chart
   - `gauge` → Gauge / Progress Bars
   - `heatmap` → Heatmap (intensity)
   - `histogram` → Distribution
   - `doughnut` → Doughnut Chart

2. Optionally paste **SQL** directly
3. Click **Build Chart**

### Option C: Dashboard Analytics Tab
The Analytics tab shows everything automatically — KPI cards, forecasts, anomalies, and validation warnings.

---

## 13. Quick Reference: Power BI vs SAAS

| Power BI Feature | SAAS Equivalent | How to Access |
|-----------------|-----------------|---------------|
| Bar/Column Chart | Bar, GroupedBar, StackedBar | NLQ or Chart Builder |
| Line Chart | Line, Area, Composed | NLQ or Chart Builder |
| Pie/Donut Chart | Pie, Doughnut | NLQ or Chart Builder |
| Funnel Chart | Funnel | NLQ or Chart Builder |
| Waterfall Chart | Waterfall | NLQ or Chart Builder |
| Scatter/Bubble | Scatter, Bubble | NLQ or Chart Builder |
| Radar Chart | Radar | NLQ or Chart Builder |
| Treemap | Treemap | NLQ or Chart Builder |
| Gauge | Gauge | NLQ or Chart Builder |
| Map | (Not yet) | Coming soon |
| Q&A (NLQ) | Ask Your Data | Navigation → Ask Your Data |
| Drill-through | NLQ follow-up queries | Type follow-up questions |
| AI Narratives | Analytics Tab → AI Narrative | Dashboard → Analytics tab |
| KPIs + Trends | KPI Cards + Sparklines | Dashboard Overview |
| Scheduled Refresh | Sync Now / ETL Pipeline | Dashboard or Settings |
| Export to PDF | Download Report | Reports History → Download |