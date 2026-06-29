# Test Cases for `seed_oracle_cnps_large.py` (Large DB)

**Schema:** Auto-generated | **9 tables** | **~885,000 rows**

Tables: `regional_offices`, `employers`, `insured_workers`, `beneficiaries`, `contributions`, `pension_payments`, `at_mp_claims`, `social_benefit_payments`, `employer_expected_contributions`

---

## TC-001 — Contribution Collection by Region

```sql
SELECT r.name AS region_name,
       COUNT(DISTINCT e.id) AS total_employers,
       SUM(c.contribution_amount) AS total_collected,
       ROUND(AVG(c.contribution_amount), 2) AS avg_contribution,
       COUNT(c.id) AS transaction_count
FROM contributions c
JOIN employers e ON c.employer_id = e.id
JOIN regional_offices r ON c.regional_code = r.code
WHERE c.contribution_date >= DATE('now', '-6 months')
GROUP BY r.name
ORDER BY total_collected DESC;
```

**Chart:** Grouped Bar | **Verifies:** 3-table JOIN, 500K+ row aggregation, date filter

---

## TC-002 — Payment Status Distribution

```sql
SELECT payment_status,
       COUNT(*) AS count,
       SUM(contribution_amount) AS total_amount
FROM contributions
GROUP BY payment_status
ORDER BY count DESC;
```

**Chart:** Pie | **Verifies:** 500K+ row GROUP BY, status breakdown (paid/overdue/pending)

---

## TC-003 — Monthly Contribution Trend (8 Years)

```sql
SELECT period_month,
       COUNT(*) AS transaction_count,
       SUM(contribution_amount) AS total_collected,
       ROUND(AVG(contribution_amount), 2) AS avg_contribution
FROM contributions
GROUP BY period_month
ORDER BY period_month;
```

**Chart:** Area | **Verifies:** 96-month time series, seasonal patterns visible (Jan-Feb dips, Jun-Aug peaks)

---

## TC-004 — Employer Sector Comparison

```sql
SELECT e.sector,
       COUNT(DISTINCT e.id) AS employer_count,
       SUM(c.contribution_amount) AS total_contributions,
       ROUND(AVG(c.contribution_amount), 2) AS avg_contribution,
       COUNT(DISTINCT w.employee_id) AS worker_count
FROM employers e
JOIN contributions c ON c.employer_id = e.id
JOIN insured_workers w ON w.employer_id = e.id
GROUP BY e.sector
ORDER BY total_contributions DESC;
```

**Chart:** Grouped Bar | **Verifies:** 15 sectors across 570 employers, worker cross-reference

---

## TC-005 — Pension Disbursement Trend

```sql
SELECT STRFTIME('%Y-%m', payment_date) AS month,
       COUNT(DISTINCT beneficiary_id) AS total_beneficiaries,
       SUM(pension_amount) AS total_disbursed,
       ROUND(AVG(pension_amount), 2) AS avg_pension
FROM pension_payments
WHERE payment_date >= DATE('now', '-5 years')
GROUP BY STRFTIME('%Y-%m', payment_date)
ORDER BY month;
```

**Chart:** Area | **Verifies:** 60-month pension trend, 3% annual increase visible

---

## TC-006 — AT/MP Claims by Severity and Region

```sql
SELECT r.name AS region_name,
       a.severity,
       COUNT(*) AS claim_count,
       ROUND(AVG(a.claim_amount), 2) AS avg_claim_amount,
       ROUND(AVG(a.days_lost), 1) AS avg_days_lost,
       SUM(a.compensation_paid) AS total_compensation
FROM at_mp_claims a
JOIN employers e ON a.employer_id = e.id
JOIN regional_offices r ON a.regional_code = r.code
GROUP BY r.name, a.severity
ORDER BY claim_count DESC;
```

**Chart:** Stacked Bar or Radar | **Verifies:** 5,000 claim records, severity distribution (minor 60%, moderate 30%, severe 10%)

---

## TC-007 — Employer Retention Cohort Analysis

```sql
WITH cohorts AS (
    SELECT e.id,
           STRFTIME('%Y-%m', e.registered_at) AS cohort_month,
           CAST((STRFTIME('%Y', 'now') - STRFTIME('%Y', e.registered_at)) * 12
               + (STRFTIME('%m', 'now') - STRFTIME('%m', e.registered_at)) AS INTEGER) AS months_active
    FROM employers e
)
SELECT cohort_month,
       COUNT(DISTINCT id) AS cohort_size,
       COUNT(DISTINCT CASE WHEN months_active >= 1 THEN id END) AS retained_1m,
       COUNT(DISTINCT CASE WHEN months_active >= 3 THEN id END) AS retained_3m,
       COUNT(DISTINCT CASE WHEN months_active >= 6 THEN id END) AS retained_6m,
       COUNT(DISTINCT CASE WHEN months_active >= 12 THEN id END) AS retained_12m,
       COUNT(DISTINCT CASE WHEN months_active >= 24 THEN id END) AS retained_24m
FROM cohorts
GROUP BY cohort_month
ORDER BY cohort_month;
```

**Chart:** Heatmap or Table | **Verifies:** CTE (WITH clause), conditional COUNT DISTINCT, retention decay

---

## TC-008 — Beneficiary Demographics

```sql
SELECT b.relationship,
       COUNT(*) AS count,
       ROUND(AVG(b.monthly_pension), 2) AS avg_pension,
       SUM(b.monthly_pension) AS total_monthly_liability
FROM beneficiaries b
WHERE b.status = 'active'
GROUP BY b.relationship
ORDER BY count DESC;
```

**Chart:** Pie | **Verifies:** ~5,000 beneficiaries, relationship types (spouse/survivor/retiree/orphan)

---

## TC-009 — Contribution Compliance Gap

```sql
SELECT e.regional_code,
       COUNT(DISTINCT e.id) AS employer_count,
       SUM(eec.expected_amount) AS total_expected,
       COALESCE(SUM(c.actual_paid), 0) AS total_actual,
       ROUND(COALESCE(SUM(c.actual_paid), 0)
             / NULLIF(SUM(eec.expected_amount), 0) * 100, 2) AS compliance_pct
FROM employer_expected_contributions eec
JOIN employers e ON eec.employer_id = e.id
LEFT JOIN (
    SELECT employer_id, period_month, SUM(contribution_amount) AS actual_paid
    FROM contributions WHERE payment_status = 'paid'
    GROUP BY employer_id, period_month
) c ON c.employer_id = eec.employer_id AND c.period_month = eec.period_month
GROUP BY e.regional_code
ORDER BY compliance_pct;
```

**Chart:** Grouped Bar | **Verifies:** Subquery, LEFT JOIN on composite key, compliance calculation, ~54K expected records

---

## TC-010 — Executive KPI Summary

```sql
SELECT 'Total Contributions' AS kpi_name,
       TO_CHAR(SUM(contribution_amount), 'FML999G999G999') AS kpi_value
FROM contributions
UNION ALL
SELECT 'Active Employers', TO_CHAR(COUNT(*), 'FM999G999')
FROM employers WHERE active = 1
UNION ALL
SELECT 'Insured Workers', TO_CHAR(COUNT(*), 'FM999G999')
FROM insured_workers WHERE status = 'active'
UNION ALL
SELECT 'Total Pension Paid', TO_CHAR(SUM(pension_amount), 'FML999G999G999')
FROM pension_payments
UNION ALL
SELECT 'Pending AT/MP Claims', TO_CHAR(COUNT(*), 'FM999G999')
FROM at_mp_claims WHERE claim_status IN ('open', 'under_review')
UNION ALL
SELECT 'Active Beneficiaries', TO_CHAR(COUNT(*), 'FM999G999')
FROM beneficiaries WHERE status = 'active';
```

**Chart:** KPI Cards | **Verifies:** UNION ALL across 6 tables, cross-table aggregation

---

## TC-011 — Social Benefits by Type

```sql
SELECT benefit_type,
       COUNT(*) AS payment_count,
       SUM(benefit_amount) AS total_paid,
       ROUND(AVG(benefit_amount), 2) AS avg_payment,
       COUNT(DISTINCT regional_code) AS regions_served
FROM social_benefit_payments
WHERE payment_date >= DATE('now', '-2 years')
GROUP BY benefit_type
ORDER BY total_paid DESC;
```

**Chart:** Bar | **Verifies:** 10,000 social benefit records, 5 benefit types (maternity, family, disability, survivor, old_age)
