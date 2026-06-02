# CNPS Adoption Guide (Future Production)

This document explains what CNPS would change/improve to adopt this system long-term, and how to deploy it in **cloud**, **on‑prem**, or **hybrid** modes.

---

## 1) Value proposition for CNPS

### Why CNPS needs this system (beyond dashboards)

- **Workflow-aware analytics**: CNPS processes (cotisations, pensions, AT/MP, conformité employeurs) require validation, governance, and auditability—not just charts.
- **Goal-driven analysis**: managers specify an *analysis goal* each time (like a BI “study”), while institutional monitoring runs continuously in the background.
- **Institutional governance**: departments/regions, roles, validation logs, lineage, and analysis history are built into the platform.
- **Lower manual load**: reduces IT-driven Excel extraction loops and repetitive reporting.
- **Traceability**: validation logs + audit logs + lineage + stored analysis runs support internal monitoring and future compliance needs.

### How to position it vs Power BI

This system is not a 1:1 replacement for Microsoft Power BI’s ecosystem and advanced modeling. Instead, it is a **purpose-built institutional analytics platform** that can:

- reduce dependence on ad-hoc Excel/BI work for recurring institutional reports
- provide CNPS-specific semantics, workflows, and audit trails
- integrate AI explanations and goal-based “studies” that are not native to classical BI dashboards

---

## 2) What CNPS would improve for production adoption

### A. Performance and scalability

- **Indexing**: add indexes/partitioning for high-volume time series (`kpi_results`, `validation_logs`, `analysis_runs`).
- **Caching**: cache schema introspection and dashboard summaries (Redis/Valkey).
- **Async jobs**: move ETL and analysis runs to a queue worker (Celery/RQ) for parallelism and reliability.

### B. Security hardening

- Move JWT from local storage to **HttpOnly cookies** + CSRF protection (if required).
- Add **rate limiting** and audit logging for auth/privileged actions.
- Use **secrets manager** (Render/Vercel/Kubernetes secrets) and key rotation.

### C. Governance features

- Fine-grained permissions (beyond admin/manager/viewer).
- Approval workflows for template and KPI definition changes.
- Data dictionary / catalog for institutional datasets.

### D. Reporting

- PDF generator service (server-side) for official reports.
- Scheduled distribution lists and approval/attestation steps.

---

## 3) Deployment modes

### Option 1 — Cloud-first (simplest)

**Recommended for pilot**:

- Supabase (Postgres + Auth)
- Backend (FastAPI) on Render/Fly/Railway
- Frontend (Vite/React PWA) on Vercel/Netlify
- LLM via hosted API (Groq or alternative)

**Pros**: fastest to deploy, easiest maintenance  
**Cons**: depends on external LLM/network policy

### Option 2 — On‑prem deployment (CNPS datacenter)

CNPS can host the full stack internally. You do **not** need to “create a CNPS LLM” — you either:

1) call a hosted LLM API, or  
2) deploy an open-source model inside CNPS infra.

**Typical on‑prem components**:

- 1+ Linux VM (or Kubernetes)
- Postgres (or Supabase self-host, or plain Postgres + auth alternative)
- Backend container(s): FastAPI
- Frontend served by Nginx
- Optional: Redis, queue worker, monitoring

**Do you need a virtual machine?**  
Yes, typically you would deploy on **VMs** (or Kubernetes nodes). A VM is the common baseline for on-prem.

**LLM on‑prem**:

- If CNPS policy requires no external AI calls, deploy a model (e.g., Llama-family) behind an internal API.
- The system only needs an API endpoint compatible with your LLM client layer; it does not require training.

### Option 3 — Hybrid (common for institutions)

Keep sensitive data and core services **on‑prem**, while allowing controlled AI calls:

**Hybrid patterns**:

- **On‑prem DB + backend**; frontend optional cloud CDN
- AI calls restricted to:
  - metadata only (schema hints, aggregates), not raw personal data
  - approved prompts and sanitized outputs
- or: on‑prem model for sensitive prompts; hosted model for low-risk summarization

**Why hybrid works well**:

- CNPS keeps data residency and control
- reduces GPU/ML ops burden if hosted AI is allowed for limited tasks

---

## 4) “Ready for GitHub + deploy” checklist

- **Environment files**:
  - `backend/.env.example` and `backend/.env.cnps.example`
  - `frontend/.env.example` and `frontend/.env.cnps.example`
- **Migrations**: apply `001`–`012` in Supabase SQL Editor
- **Demo DBs**:
  - `python scripts/seed_cnps_sample.py`
  - `python scripts/seed_cnps_full_demo.py`
- **Docs**:
  - `docs/CNPS_USER_GUIDE.md`
  - `docs/CNPS_FULL_DEMO_WALKTHROUGH.md`
  - this document: `docs/CNPS_ADOPTION_GUIDE.md`

---

## 5) Roadmap for CNPS institutional rollout

1. Pilot with 1–2 directions/regional offices
2. Validate KPI definitions and data mappings per source system
3. Add governance approvals + performance hardening
4. Expand to all regions + automate monthly/quarterly official reports

