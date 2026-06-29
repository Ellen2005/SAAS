# Test Cases for `oracle_cnps_demo.sql` (Medium DB)

**Schema:** `cnps_demo` | **5 tables** | **~18,000 rows**

Tables: `regional_offices`, `employers`, `contributions`, `pension_payments`, `workplace_accidents`

---

## TC-001 — Contribution Collection by Region

```sql
SELECT r.name AS region_name,
       COUNT(DISTINCT e.employer_id) AS total_employers,
       SUM(c.contribution_amount) AS total_collected,
       ROUND(AVG(c.contribution_amount), 2) AS avg_contribution,
       COUNT(c.contribution_id) AS transaction_count
FROM contributions c
JOIN employers e ON c.employer_id = e.employer_id
JOIN regional_offices r ON c.regional_code = r.code
WHERE c.contribution_date >= ADD_MONTHS(SYSDATE, -6)
GROUP BY r.name
ORDER BY total_collected DESC;
```

**Chart:** Grouped Bar | **Verifies:** JOIN across 3 tables, aggregation, date filter

---

## TC-002 — Payment Status Breakdown

```sql
SELECT payment_status,
       COUNT(*) AS count,
       SUM(contribution_amount) AS total_amount,
       ROUND(AVG(contribution_amount), 2) AS avg_amount
FROM contributions
GROUP BY payment_status
ORDER BY count DESC;
```

**Chart:** Pie or Donut | **Verifies:** Status distribution (paid/overdue/rejected/partial)

---

## TC-003 — Monthly Contribution Trend

```sql
SELECT TO_CHAR(contribution_date, 'YYYY-MM') AS month,
       COUNT(*) AS transaction_count,
       SUM(contribution_amount) AS total_collected,
       ROUND(AVG(contribution_amount), 2) AS avg_contribution
FROM contributions
WHERE contribution_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY TO_CHAR(contribution_date, 'YYYY-MM')
ORDER BY month;
```

**Chart:** Area or Line | **Verifies:** Time-series aggregation, TO_CHAR formatting

---

## TC-004 — Employer Delinquency Analysis

```sql
SELECT e.employer_code,
       e.company_name,
       e.sector,
       r.name AS region,
       e.last_payment_date,
       ROUND(SYSDATE - e.last_payment_date) AS days_since_last_payment,
       COUNT(c.contribution_id) AS unpaid_count,
       SUM(c.contribution_amount) AS total_owed
FROM employers e
JOIN regional_offices r ON e.regional_code = r.code
LEFT JOIN contributions c ON c.employer_id = e.employer_id
    AND c.payment_status IN ('overdue', 'rejected')
WHERE e.status = 'delinquent'
GROUP BY e.employer_code, e.company_name, e.sector, r.name, e.last_payment_date
ORDER BY days_since_last_payment DESC;
```

**Chart:** Table + Bar | **Verifies:** LEFT JOIN, date arithmetic, filtered aggregation

---

## TC-005 — Pension Disbursement by Region

```sql
SELECT r.name AS region_name,
       COUNT(DISTINCT p.beneficiary_ssn) AS total_beneficiaries,
       SUM(p.pension_amount) AS total_disbursed,
       ROUND(AVG(p.pension_amount), 2) AS avg_pension,
       ROUND(AVG(p.processing_days), 1) AS avg_processing_days
FROM pension_payments p
JOIN regional_offices r ON p.regional_code = r.code
WHERE p.payment_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY r.name
ORDER BY total_disbursed DESC;
```

**Chart:** Grouped Bar | **Verifies:** Pension table, JOIN, AVG processing time

---

## TC-006 — Workplace Accidents by Severity

```sql
SELECT r.name AS region_name,
       a.severity,
       COUNT(*) AS claim_count,
       ROUND(AVG(a.claim_amount), 2) AS avg_claim_amount,
       ROUND(AVG(a.processing_days), 1) AS avg_processing_days,
       SUM(a.claim_amount) AS total_claimed
FROM workplace_accidents a
JOIN employers e ON a.employer_id = e.employer_id
JOIN regional_offices r ON a.regional_code = r.code
WHERE a.accident_date >= ADD_MONTHS(SYSDATE, -12)
GROUP BY r.name, a.severity
ORDER BY claim_count DESC;
```

**Chart:** Stacked Bar or Radar | **Verifies:** 3-table JOIN, GROUP BY severity, accident data

---

## TC-007 — Employer Sector Health Overview

```sql
SELECT e.sector,
       COUNT(DISTINCT e.employer_id) AS employer_count,
       SUM(c.contribution_amount) AS total_contributions,
       ROUND(AVG(c.contribution_amount), 2) AS avg_contribution,
       COUNT(CASE WHEN c.payment_status = 'overdue' THEN 1 END) AS overdue_count,
       ROUND(COUNT(CASE WHEN c.payment_status = 'overdue' THEN 1 END)
             / NULLIF(COUNT(*), 0) * 100, 2) AS overdue_pct
FROM employers e
JOIN contributions c ON c.employer_id = e.employer_id
GROUP BY e.sector
ORDER BY total_contributions DESC;
```

**Chart:** Grouped Bar | **Verifies:** CASE in aggregation, sector breakdown, overdue rate

---

## TC-008 — Regional Office Budget vs Staffing

```sql
SELECT code, name, region,
       staff_count,
       budget_allocated,
       ROUND(budget_allocated / NULLIF(staff_count, 0), 2) AS budget_per_staff
FROM regional_offices
ORDER BY budget_per_staff DESC NULLS LAST;
```

**Chart:** Scatter or Bar | **Verifies:** Simple computation, NULLIF guard

---

## TC-009 — Late Payment Fee Analysis

```sql
SELECT r.name AS region_name,
       COUNT(CASE WHEN c.late_fee > 0 THEN 1 END) AS late_payments,
       SUM(c.late_fee) AS total_fees_collected,
       ROUND(AVG(c.late_fee), 2) AS avg_fee,
       MAX(c.late_fee) AS max_fee
FROM contributions c
JOIN regional_offices r ON c.regional_code = r.code
WHERE c.late_fee > 0
GROUP BY r.name
ORDER BY total_fees_collected DESC;
```

**Chart:** Bar | **Verifies:** Conditional COUNT, non-zero filter

---

## TC-010 — Executive KPI Summary

```sql
SELECT 'Total Contributions (YTD)' AS kpi_name,
       TO_CHAR(SUM(contribution_amount), 'FML999G999G999') AS kpi_value
FROM contributions
WHERE contribution_date >= TRUNC(SYSDATE, 'YEAR')
UNION ALL
SELECT 'Active Employers', TO_CHAR(COUNT(*), 'FM999G999')
FROM employers WHERE status IN ('active', 'suspended')
UNION ALL
SELECT 'Pension Disbursed (YTD)', TO_CHAR(SUM(pension_amount), 'FML999G999G999')
FROM pension_payments
WHERE payment_date >= TRUNC(SYSDATE, 'YEAR')
UNION ALL
SELECT 'Pending Accident Claims', TO_CHAR(COUNT(*), 'FM999')
FROM workplace_accidents WHERE claim_status IN ('pending', 'under_investigation')
UNION ALL
SELECT 'Total Late Fees Collected', TO_CHAR(SUM(late_fee), 'FML999G999G999')
FROM contributions WHERE late_fee > 0;
```

**Chart:** KPI Cards or Gauge | **Verifies:** UNION ALL across 5 tables, YTD filtering

---

## TC-011 — Monthly New Employers Trend

```sql
SELECT TO_CHAR(registration_date, 'YYYY-MM') AS month,
       COUNT(*) AS new_employers,
       ROUND(AVG(employee_count), 1) AS avg_employees
FROM employers
WHERE registration_date >= ADD_MONTHS(SYSDATE, -24)
GROUP BY TO_CHAR(registration_date, 'YYYY-MM')
ORDER BY month;
```

**Chart:** Line | **Verifies:** Date truncation, registration trend
