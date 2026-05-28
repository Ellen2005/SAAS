# Push to GitHub & Deploy (Free) Guide

A step-by-step recipe to push this repo to GitHub and deploy the backend +
frontend on free tiers.

---

## 1. One-time GitHub setup

### 1.1 Create the repo

1. Go to https://github.com/new and create an empty repo (e.g.
   `saas-analytics-pwa`). **Do not** add a README / .gitignore / license
   from the wizard — we already have files.
2. Copy the SSH or HTTPS URL it gives you, e.g.
   `git@github.com:youruser/saas-analytics-pwa.git`.

### 1.2 Make sure secrets are NOT committed

The repo already has a sensible `.gitignore`. Double-check:

```bash
grep -E "^(\.env|node_modules|__pycache__|\.venv|dist|build)$" .gitignore
```

If `.env` is missing, add it:

```bash
echo ".env" >> .gitignore
echo "backend/.env" >> .gitignore
echo "frontend/.env*" >> .gitignore
```

### 1.3 First push

From a terminal in the project root:

```bash
git init                                # if not already a git repo
git add .
git commit -m "Initial import"
git branch -M main
git remote add origin git@github.com:youruser/saas-analytics-pwa.git
git push -u origin main
```

> 💡 On Replit you can also use the built-in **Version Control** panel:
> click *Connect to GitHub*, pick your account, name the repo, and click
> *Push*. Replit handles the SSH key for you.

### 1.4 Add the GitHub Actions CI (optional but recommended)

Create `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt
      - run: python -m compileall backend
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm --prefix frontend ci
      - run: npm --prefix frontend run build
```

---

## 2. Deploy the **backend** (Render — free)

Render's free Web Service tier sleeps after 15 min idle but wakes on
request. Perfect for this app.

1. Sign up at https://render.com (link your GitHub).
2. Click **New → Web Service** and pick the repo.
3. Fill in:

   | Field | Value |
   |---|---|
   | Name | `saas-analytics-api` |
   | Region | nearest you |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |

> Note: `backend/requirements.txt` now includes `oracledb` for Oracle source database support. Ensure the target runtime can install Oracle dependencies if you plan to connect Oracle sources.
   | Plan | **Free** |

4. Click **Advanced → Add Environment Variable** for every key in your
   `backend/.env` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_KEY`, `DATABASE_URL`, `GROQ_API_KEY`,
   `BREVO_API_KEY`, `FERNET_KEY`).
5. Click **Create Web Service**. First build takes ~3 minutes.
6. Copy the public URL Render gives you (e.g.
   `https://saas-analytics-api.onrender.com`).

### Free-tier ping (avoid cold starts)

Add a free **cron-job.org** (or UptimeRobot) job that hits
`https://saas-analytics-api.onrender.com/api/ping` every 10 minutes. The
endpoint is already implemented in `backend/api/main.py`.

### Alternatives

* **Fly.io** — `fly launch --no-deploy` then `fly deploy`. Free allowance
  covers this app comfortably (256 MB shared-CPU VM).
* **Railway** — free trial credits per month; same workflow.
* **Replit Reserved-VM Deployment** — click **Deploy** in the Replit
  workspace; choose **Reserved VM** ($7/mo) or **Autoscale** (free for low
  traffic) and the build/start commands above.

---

## 3. Deploy the **frontend** (Vercel — free)

1. Sign up at https://vercel.com (link your GitHub).
2. **Add New → Project** → pick the repo.
3. Framework preset: **Vite**. Root Directory: `frontend`.
4. Build Command: `npm run build`. Output Directory: `dist`.
5. Environment Variables:

   | Name | Value |
   |---|---|
   | `VITE_SUPABASE_URL` | `https://<project>.supabase.co` |
   | `VITE_SUPABASE_ANON_KEY` | (from Supabase) |
   | `VITE_API_BASE_URL` | `https://saas-analytics-api.onrender.com` |

6. **Deploy**. After ~2 min you get `https://your-app.vercel.app`.

### Make `/api` calls hit your backend

The frontend uses `VITE_API_BASE_URL` for API calls; if it is unset, it
defaults to relative `/api` paths and depends on a proxy. On Vercel, set the
env var (step 5) **and/or** add a `vercel.json` rewrite:

```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://saas-analytics-api.onrender.com/api/$1" }
  ]
}
```

### Alternative: Netlify

* Same steps; set Base directory to `frontend`, Publish directory to `dist`.
* Use `netlify.toml`:

  ```toml
  [build]
    base = "frontend"
    command = "npm run build"
    publish = "dist"
  [[redirects]]
    from = "/api/*"
    to = "https://saas-analytics-api.onrender.com/api/:splat"
    status = 200
  ```

---

## 4. Configure the app database (Supabase — free)

1. https://supabase.com → **New project** (free plan, ~500 MB).
2. **SQL Editor** → paste `backend/supabase_schema.sql` → Run.
3. Then run each file in `backend/migrations/` in numeric order.
4. **Auth → Providers** → enable Email + any social you want.
5. **Project Settings → API**:
   * Copy `URL` → `SUPABASE_URL`
   * Copy `anon` key → `SUPABASE_ANON_KEY` (frontend) and the same anon key
     to backend `SUPABASE_ANON_KEY`
   * Copy `service_role` key → `SUPABASE_SERVICE_KEY` (backend only — never
     ship to frontend!)
6. **Project Settings → Database** → copy the connection string into
   `DATABASE_URL` (use the **pooled** URI on free tier).

---

## 5. Optional — Email & AI

| Service | Free tier | Where to put the key |
|---|---|---|
| **Brevo** (email) | 300 emails/day | `BREVO_API_KEY` |
| **Groq** (LLM) | Generous monthly free quota | `GROQ_API_KEY` |

Both are optional — the app degrades gracefully if missing (NLQ returns a
"key not configured" error; the briefing email is skipped).

---

## 6. Custom domain (free with Vercel)

1. Vercel → your project → **Domains** → **Add** → type your domain.
2. At your DNS provider, add the CNAME / A records Vercel shows.
3. SSL is provisioned automatically.

For the backend you can either:

* Use Render's `*.onrender.com` URL (free), or
* Add a custom domain on Render (free with their free plan, certificate
  auto-issued).

---

## 7. Post-deploy smoke test

1. Visit your Vercel URL → log in.
2. **Settings** → save a connection string (use one from
   `docs/TESTING_GUIDE.md` §2).
3. **Schema Explorer** → Re-discover, then **Sync to dashboard**.
4. **Dashboard** shows fresh KPI tiles.
5. Wait for your scheduled `sync_time` (or change it to one minute from
   now in Settings) and confirm the nightly job ran by checking
   **Reports History**.

---

## 8. Updating after first deploy

```bash
git add . && git commit -m "Feature: X"
git push
```

* Render auto-deploys on push to `main`.
* Vercel auto-deploys on push to `main`.
* Supabase migrations are **not** auto-applied — paste new SQL files
  manually in the SQL Editor (or wire up `supabase db push` later).

---

## 9. Cost summary at the free tier

| Component | Monthly cost |
|---|---|
| GitHub (public or 3 private collaborators) | $0 |
| Render Web Service (free) | $0 (sleeps after 15 min idle) |
| Vercel Hobby | $0 |
| Supabase Free | $0 (≤ 500 MB DB, ≤ 50k MAU) |
| Brevo Free | $0 (≤ 300 emails/day) |
| Groq Free | $0 (current quotas) |
| **Total** | **$0/mo** |

For production you'll likely want to upgrade Render ($7/mo) so the API
doesn't cold-start, and Supabase Pro ($25/mo) once data grows.
