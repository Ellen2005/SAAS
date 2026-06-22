# Comprehensive Testing Guide
## Enterprise Analytics Platform - Data Analyst Testing Guide

This guide provides step-by-step testing scenarios for validating the system with the large CNPS dataset.

---

## Table of Contents
1. [Dataset Overview](#dataset-overview)
2. [Prerequisites](#prerequisites)
3. [Testing Scenarios](#testing-scenarios)
4. [Performance Testing](#performance-testing)
5. [Edge Cases & Validation](#edge-cases--validation)
6. [Troubleshooting](#troubleshooting)

---

## Dataset Overview

### Generated Data Summary
- **Time Period:** January 2018 - Present (8+ years)
- **Regions:** 10 regions across Cameroon
- **Employers:** 500+ companies across 15 sectors
- **Insured Workers:** 10,000+ employees
- **Beneficiaries:** 5,000+ pensioners/beneficiaries
- **Contributions:** 500,000+ payment records
- **Pension Payments:** 300,000+ records
- **AT/MP Claims:** 5,000+ workplace accidents
- **Social Benefits:** 10,000+ payments

### Data Characteristics
- **Seasonal Patterns:** Lower contributions in Jan-Feb, higher in Jun-Aug
- **Economic Growth:** 5% annual increase in contributions
- **Realistic Distribution:** 85% paid, 10% pending, 5% overdue
- **Anomalies Included:** Duplicate records, sparse regions, late payers

---

## Prerequisites

### 1. Generate the Dataset
```bash
# Generate SQLite database (8 years of data)
python scripts/seed_oracle_cnps_large.py --output ./data/cnps_oracle_large.db --years 8

# Expected output:
# ============================================================
# Database created: /path/to/cnps_oracle_large.db
# ============================================================
#   regional_offices                    :        10 rows
#   employers                           :       500 rows
#   insured_workers                     :    12,500 rows
#   beneficiaries                       :     5,000 rows
#   contributions                       :   500,000 rows
#   pension_payments                    :   300,000 rows
#   at_mp_claims                        :     5,000 rows
#   social_benefit_payments             :    10,000 rows
#   employer_expected_contributions     :    48,000 rows
# ============================================================
#   TOTAL                               :   880,510 rows
# ============================================================
```

### 2. Configure Database Connection
1. Start the application
2. Go to **Settings → Database Connection**
3. Select database type: **SQLite** (for testing) or **Oracle** (for production)
4. For SQLite: Enter path to `cnps_oracle_large.db`
5. Click **Test Connection** - should show "Connection verified!"
6. Click **Save Connection**

### 3. Initial Data Sync
1. Go to **Dashboard**
2. Click **Sync Now** button
3. Wait for ETL to complete (may take 2-5 minutes for large dataset)
4. Monitor status: "Fetching data..." → "Mapping fields..." → "Validating..." → "Done"

---

## Testing Scenarios

### Scenario 1: Dashboard Overview (5 minutes)

**Objective:** Verify dashboard loads correctly with large dataset

**Steps:**
1. Navigate to **Dashboard**
2. Observe loading time (should be < 3 seconds with caching)
3. Check KPI cards display:
   - Total Contributions
   - Pension Disbursement
   - AT/MP Frequency
   - Contributions by Region

**Expected Results:**
- ✅ Dashboard loads without errors
- ✅ 4 KPI cards visible with values
- ✅ Sparkline charts show trends
- ✅ Last updated timestamp is recent
- ✅ No console errors

**Actual Data to Verify:**
```sql
-- Total contributions should be ~500,000 records
SELECT COUNT(*) FROM contributions;
-- Expected: 500,000

-- Total contribution amount (sum of all payments)
SELECT SUM(contribution_amount) FROM contributions;
-- Expected: ~15-25 billion XAF

-- Active employers
SELECT COUNT(*) FROM employers WHERE active = 1;
-- Expected: 500
```

---

### Scenario 2: KPI Drill-Down Analysis (10 minutes)

**Objective:** Test detailed KPI analytics

**Steps:**
1. Click on **Total Contributions** KPI card
2. Verify navigation to Analytics tab
3. Check detailed view shows:
   - Current value
   - Day-over-Day % change
   - Status (NORMAL/WARNING/CRITICAL)
   - Historical trend chart
4. Change date range: 7D → 30D → 90D → 1Y
5. Observe chart updates

**Expected Results:**
- ✅ KPI detail view loads
- ✅ Historical chart shows 8 years of data
- ✅ Date range selector works
- ✅ Values update correctly
- ✅ Status color-coded (green/yellow/red)

**Analysis Queries:**
```sql
-- Contributions by month (last 12 months)
SELECT 
    period_month,
    SUM(contribution_amount) as total,
    COUNT(*) as count
FROM contributions
WHERE contribution_date >= DATE('now', '-12 months')
GROUP BY period_month
ORDER BY period_month DESC;

-- Top 10 employers by contribution volume
SELECT 
    e.name,
    SUM(c.contribution_amount) as total_contributions,
    COUNT(*) as payment_count
FROM contributions c
JOIN employers e ON c.employer_id = e.id
GROUP BY e.id, e.name
ORDER BY total_contributions DESC
LIMIT 10;

-- Regional distribution
SELECT 
    regional_code,
    SUM(contribution_amount) as total,
    COUNT(DISTINCT employer_id) as employers
FROM contributions
GROUP BY regional_code
ORDER BY total DESC;
```

---

### Scenario 3: Anomaly Detection (10 minutes)

**Objective:** Verify anomaly detection works with large dataset

**Steps:**
1. Navigate to **Dashboard → Analytics** tab
2. Scroll to **Anomalies Detected** section
3. Review flagged records:
   - Should show outliers in contributions
   - Should highlight overdue payments
   - Should show regional gaps
4. Click on anomaly to see details

**Expected Results:**
- ✅ At least 5-10 anomalies detected
- ✅ Anomalies include:
  - Late payers (EMP-1016 and similar)
  - Regional data gaps (Maroua sparse data)
  - Duplicate records
  - Unusual payment amounts
- ✅ Each anomaly shows:
  - KPI name
  - Deviation percentage
  - Context/reason
  - Severity level

**Manual Anomaly Check:**
```sql
-- Find employers with overdue contributions (>30 days)
SELECT 
    e.employer_code,
    e.name,
    COUNT(*) as overdue_count,
    SUM(c.contribution_amount) as overdue_amount
FROM contributions c
JOIN employers e ON c.employer_id = e.id
WHERE c.payment_status = 'overdue'
  AND c.contribution_date < DATE('now', '-30 days')
GROUP BY e.id, e.employer_code, e.name
ORDER BY overdue_amount DESC
LIMIT 20;

-- Find duplicate contributions (same employer, period, amount)
SELECT 
    employer_id,
    period_month,
    contribution_amount,
    COUNT(*) as duplicate_count
FROM contributions
GROUP BY employer_id, period_month, contribution_amount
HAVING COUNT(*) > 1;

-- Regional gaps (months with no data)
SELECT 
    r.code,
    r.name,
    COUNT(DISTINCT strftime('%Y-%m', c.contribution_date)) as months_with_data
FROM regional_offices r
LEFT JOIN contributions c ON r.code = c.regional_code
GROUP BY r.code, r.name
ORDER BY months_with_data ASC;
```

---

### Scenario 4: AI Narrative Generation (5 minutes)

**Objective:** Test AI-powered report generation

**Steps:**
1. Click **Generate Report** button
2. Wait for AI to process (10-30 seconds)
3. Review generated narrative:
   - Should be clean text (no asterisks)
   - Professional formatting
   - Structured sections
   - Data-driven insights
4. Check for:
   - Executive summary
   - Key findings
   - Anomalies highlighted
   - Recommendations

**Expected Results:**
- ✅ Report generates without errors
- ✅ Narrative is well-structured
- ✅ No markdown artifacts (**, *, __)
- ✅ Insights are data-driven
- ✅ Professional tone

**Sample Analysis to Verify:**
```sql
-- Collection rate by region
SELECT 
    regional_code,
    SUM(contribution_amount) as collected,
    SUM(expected_amount) as expected,
    ROUND(SUM(contribution_amount) / SUM(expected_amount) * 100, 2) as collection_rate
FROM contributions c
JOIN employer_expected_contributions e 
  ON c.employer_id = e.employer_id 
  AND strftime('%Y-%m', c.contribution_date) = e.period_month
GROUP BY regional_code
ORDER BY collection_rate DESC;

-- AT/MP severity trends
SELECT 
    strftime('%Y', claim_date) as year,
    severity,
    COUNT(*) as claim_count,
    AVG(days_lost) as avg_days_lost,
    SUM(claim_amount) as total_cost
FROM at_mp_claims
GROUP BY year, severity
ORDER BY year, severity;
```

---

### Scenario 5: Report History & Export (5 minutes)

**Objective:** Test report management and export

**Steps:**
1. Navigate to **Reports** page
2. Verify report list loads
3. Click on a report to expand
4. Test **PDF** download
5. Test **Excel** export
6. Verify file downloads correctly

**Expected Results:**
- ✅ Reports list loads
- ✅ PDF download works
- ✅ Excel export works
- ✅ Files open correctly
- ✅ Data matches dashboard

---

### Scenario 6: Schema Explorer (10 minutes)

**Objective:** Test database schema visualization

**Steps:**
1. Navigate to **Schema** (or /explorer)
2. Verify tables are displayed:
   - contributions
   - employers
   - insured_workers
   - beneficiaries
   - pension_payments
   - at_mp_claims
   - social_benefit_payments
3. Click on table to see columns
4. Check domain tags are correct

**Expected Results:**
- ✅ All 9 tables visible
- ✅ Columns displayed with types
- ✅ Domain tags shown (contribution, payment, etc.)
- ✅ Relationships visible
- ✅ No errors in console

---

### Scenario 7: Natural Language Query (10 minutes)

**Objective:** Test NLQ functionality

**Steps:**
1. Navigate to **Query** (or /query)
2. Try these queries:
   - "Show me total contributions by region for 2024"
   - "Which employers have the most overdue payments?"
   - "What is the average pension amount by region?"
   - "Show AT/MP claims by severity for the last 2 years"
   - "Which sector has the highest collection rate?"
3. Verify results display as charts/tables

**Expected Results:**
- ✅ Queries execute successfully
- ✅ Results are accurate
- ✅ Charts render correctly
- ✅ SQL is generated (visible in debug mode)
- ✅ No SQL injection errors

---

### Scenario 8: Validation & Data Quality (10 minutes)

**Objective:** Test data validation features

**Steps:**
1. Navigate to **Validation** page
2. Review validation checks:
   - Staleness checks
   - Duplicate detection
   - Regional gaps
   - Completeness checks
3. Click on validation item for details
4. Verify issues are correctly identified

**Expected Results:**
- ✅ Validation runs automatically
- ✅ Issues are detected:
  - Duplicate contributions (intentional test data)
  - Sparse data in Maroua (MAR)
  - Late payer employer (EMP-1016)
- ✅ Severity levels correct
- ✅ Recommendations provided

**Validation Queries:**
```sql
-- Check for null values
SELECT 
    'contributions' as table_name,
    COUNT(*) as total_rows,
    SUM(CASE WHEN contribution_amount IS NULL THEN 1 ELSE 0 END) as null_amounts,
    SUM(CASE WHEN employee_id IS NULL THEN 1 ELSE 0 END) as null_employees
FROM contributions
UNION ALL
SELECT 
    'employers',
    COUNT(*),
    SUM(CASE WHEN name IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN sector IS NULL THEN 1 ELSE 0 END)
FROM employers;

-- Data freshness check
SELECT 
    MAX(contribution_date) as latest_contribution,
    MIN(contribution_date) as earliest_contribution,
    COUNT(DISTINCT strftime('%Y-%m', contribution_date)) as months_covered
FROM contributions;
```

---

### Scenario 9: Admin Dashboard Performance (15 minutes)

**Objective:** Test admin dashboard with large dataset

**Steps:**
1. Login as **admin** user
2. Navigate to **Admin** dashboard
3. Monitor load time (should be < 5 seconds)
4. Check all sections load:
   - User statistics
   - Department overview
   - System health
   - Recent activity
5. Navigate to **Admin → Users**
6. Verify user list loads with pagination
7. Test user editing

**Expected Results:**
- ✅ Admin dashboard loads in < 5 seconds
- ✅ No timeout errors
- ✅ Pagination works for large lists
- ✅ Charts render correctly
- ✅ All admin functions accessible

**Performance Optimization Applied:**
- Pagination (50 items per page)
- Lazy loading for charts
- Cached aggregations
- Indexed database queries

---

### Scenario 10: Scheduled Reports (10 minutes)

**Objective:** Test automated report generation

**Steps:**
1. Navigate to **Settings → Scheduled Reports**
2. Configure report:
   - Frequency: Daily
   - Time: 02:00
   - Recipients: your-email@example.com
3. Save configuration
4. Trigger manual run: **Run Now**
5. Check email inbox for report
6. Verify report content

**Expected Results:**
- ✅ Configuration saves
- ✅ Manual trigger works
- ✅ Email received within 2 minutes
- ✅ Report contains:
  - KPIs table
  - Anomalies section
  - AI narrative
  - Professional formatting

---

## Performance Testing

### Load Testing Checklist

**Small Dataset (< 10,000 rows):**
- [ ] Dashboard loads in < 1 second
- [ ] Reports generate in < 5 seconds
- [ ] Queries execute in < 2 seconds

**Medium Dataset (10,000 - 100,000 rows):**
- [ ] Dashboard loads in < 2 seconds
- [ ] Reports generate in < 10 seconds
- [ ] Queries execute in < 5 seconds

**Large Dataset (500,000+ rows):**
- [ ] Dashboard loads in < 3 seconds (with caching)
- [ ] Reports generate in < 30 seconds
- [ ] Queries execute in < 10 seconds
- [ ] No memory leaks
- [ ] No timeout errors

### Database Performance

**Indexes to Verify:**
```sql
-- Check indexes exist
SELECT name FROM sqlite_master WHERE type = 'index';

-- Should see:
-- idx_contrib_date
-- idx_contrib_region
-- idx_contrib_employer
-- idx_contrib_period
-- idx_pension_date
-- idx_claim_date
-- idx_claim_employer
-- idx_worker_employer
-- idx_worker_status
-- idx_employer_region
-- idx_employer_sector
```

**Query Performance:**
```sql
-- Should use index and complete in < 100ms
EXPLAIN QUERY PLAN
SELECT * FROM contributions 
WHERE contribution_date >= '2024-01-01'
  AND regional_code = 'DOU'
ORDER BY contribution_date DESC
LIMIT 100;

-- Expected: SEARCH TABLE contributions USING INDEX idx_contrib_date
```

---

## Edge Cases & Validation

### Edge Case 1: Empty Database
**Test:** Connect to empty database
**Expected:** Graceful handling, "No data yet" message

### Edge Case 2: Missing Data
**Test:** Delete some contributions manually
**Expected:** Validation detects gaps, shows warnings

### Edge Case 3: Duplicate Records
**Test:** System includes intentional duplicates
**Expected:** Validation flags duplicates, suggests cleanup

### Edge Case 4: Late Payments
**Test:** EMP-1016 has 50% overdue rate
**Expected:** Anomaly detection flags employer

### Edge Case 5: Regional Gaps
**Test:** Maroua (MAR) has sparse recent data
**Expected:** Validation shows data staleness warning

### Edge Case 6: Large Date Ranges
**Test:** Query 8 years of data
**Expected:** Pagination works, no timeout

---

## Troubleshooting

### Issue: Dashboard loads slowly
**Solution:**
1. Check database indexes exist
2. Enable caching (Redis recommended)
3. Reduce date range
4. Check server resources (CPU/RAM)

### Issue: "No data available"
**Solution:**
1. Verify database connection
2. Run ETL sync
3. Check table names match schema
4. Review ETL logs

### Issue: Anomalies not detected
**Solution:**
1. Ensure data has variations
2. Check anomaly detection is enabled
3. Review threshold settings
4. Verify KPI calculations

### Issue: Reports fail to generate
**Solution:**
1. Check AI API key (Groq)
2. Verify sufficient data exists
3. Review backend logs
4. Test with smaller dataset

### Issue: Emails not sending
**Solution:**
1. Check Brevo API key
2. Verify sender email
3. Add email recipients
4. Test with `/api/email/test`

---

## Success Criteria

### Functional Testing
- [ ] All 10 scenarios pass
- [ ] No console errors
- [ ] All features work as expected
- [ ] Data accuracy verified

### Performance Testing
- [ ] Dashboard loads < 3s with 500K records
- [ ] Reports generate < 30s
- [ ] Queries execute < 10s
- [ ] No memory leaks after 1 hour

### Data Quality
- [ ] 500,000+ contributions generated
- [ ] Realistic patterns present
- [ ] Anomalies detectable
- [ ] No orphaned records

### Production Readiness
- [ ] All tests pass
- [ ] Documentation complete
- [ ] Error handling robust
- [ ] Monitoring in place

---

## Next Steps

1. **Run the dataset generator:**
   ```bash
   python scripts/seed_oracle_cnps_large.py --output ./data/cnps_oracle_large.db --years 8
   ```

2. **Connect and sync:**
   - Configure database connection
   - Run initial ETL sync
   - Verify data loaded

3. **Execute test scenarios:**
   - Follow scenarios 1-10
   - Document results
   - Report any issues

4. **Performance baseline:**
   - Record load times
   - Monitor resource usage
   - Identify bottlenecks

5. **Production deployment:**
   - Follow `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`
   - Use Oracle database
   - Enable monitoring

---

**Last Updated:** 2025-01-15  
**Tested With:** cnps_oracle_large.db (880K+ rows, 8 years)  
**Status:** Ready for Testing ✅