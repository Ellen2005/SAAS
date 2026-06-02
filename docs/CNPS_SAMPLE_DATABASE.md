# CNPS Institutional Sample Database

This guide describes the **Cameroon CNPS (social security)** sample database used for demos, testing, and final-year project defense.

## Not Customer NPS

| File | Purpose |
|------|---------|
| [`scripts/seed_cnps_sample.py`](../scripts/seed_cnps_sample.py) | **Institutional CNPS** — contributions, pensions, employers, AT/MP |
| [`generate_cnps_db.py`](../generate_cnps_db.py) | **Customer Net Promoter Score** — unrelated demo (`customers`, `nps_feedback`) |

For project defense, use **`cnps_institutional_sample.db`** only.

## Generate the database

```bash
python scripts/seed_cnps_sample.py
```

Output: `cnps_institutional_sample.db` at the repository root (by default).

## Schema

| Table | Domain | Key columns |
|-------|--------|-------------|
| `regional_offices` | Organization | `code`, `name` |
| `employers` | Employers | `employer_code`, `name`, `regional_code` |
| `insured_workers` | Insured workers | `employee_id`, `employer_id` |
| `beneficiaries` | Pensions | `beneficiary_id`, `insured_worker_id` |
| `contributions` | Contributions | `contribution_date`, `contribution_amount`, `payment_status` |
| `pension_payments` | Pension disbursements | `payment_date`, `pension_amount` |
| `workplace_accidents` | AT/MP | `accident_date`, `claim_status`, `severity` |

## Connect in SAAS

1. Sign in as a manager.
2. Open **Settings** → database connection.
3. Use SQLite URL:

   ```
   sqlite:///C:/full/path/to/cnps_institutional_sample.db
   ```

4. Run **Data refresh** (ETL) or use **Analysis** with a CNPS preset.

## Expected KPI labels

After sync, introspection should classify tables into domains such as **Contribution**, **Payment**, **Pension**, **Claim**, and **Employer** — suitable for CNPS dashboard widgets and analysis presets.

## Legacy guides

Older files `CNPS_TESTING_GUIDE*.md` referred to Customer NPS sample data. Prefer this document for institutional CNPS testing.
