# CNPS SAAS Analytics - Production Deployment Checklist

## Pre-Deployment (Complete before GitHub push)

### 1. Environment Configuration
- [ ] Create production `.env` from `.env.example`
- [ ] Generate new FERNET_KEY: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- [ ] Generate new UNSUBSCRIBE_SECRET: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Update FRONTEND_URL to production domain
- [ ] Verify Brevo sender email is verified
- [ ] Verify Groq API key has sufficient quota

### 2. Database Setup
- [ ] Run migration `018_reports_add_columns.sql` in Supabase SQL Editor
- [ ] Verify Oracle connection works from production server
- [ ] Test ETL pipeline triggers successfully
- [ ] Verify field mappings are configured in `admin_field_mappings` table

### 3. Code Cleanup
- [ ] Remove temporary test files (already done)
- [ ] Verify `.env` is in `.gitignore` (confirmed)
- [ ] Verify `backend/.env` is not tracked (confirmed)
- [ ] Run frontend build: `cd frontend && npm run build`
- [ ] Run backend syntax check on all routers

### 4. Git Setup
```bash
cd C:\Users\nguki\OneDrive\Desktop\SAAS

# Stage all changes
git add .

# Verify no secrets are staged
git diff --cached --name-only | findstr ".env"

# Commit
git commit -m "feat: production-ready CNPS analytics system

- Fix 22+ backend bugs (missing imports, route decorators, undefined variables)
- Optimize dashboard performance (KPI filtering, cache TTL reduction)
- Add dashboard sync from Settings/Schema/Analysis pages
- Remove duplicate buttons, fix customize button
- Add shared dashboard cache invalidation utility
- Fix ETL KPI naming with admin global_field_name
- Fix webhook stats (supabase.raw replacement)
- Add supervisor presentation and deployment docs
- All 4 test cases passing (TC-001 to TC-004)"

# Push to GitHub
git push origin main
```

## Deployment Steps

### Option A: Docker Compose (Recommended)
```bash
# 1. Clone on production server
git clone https://github.com/Ellen2005/SAAS.git
cd SAAS

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with production credentials

# 3. Start services
docker compose up -d

# 4. Verify
curl http://localhost:8000/api/ping
# Should return: {"ok": true}

# 5. Check logs
docker compose logs -f backend
```

### Option B: Manual Setup
```bash
# 1. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env

# 3. Run
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# 4. Frontend
cd ../frontend
npm install
npm run build  # Production build
# Serve dist/ with nginx or similar
```

### Option C: Cloud Deploy (Railway/Render)
```bash
# 1. Push to GitHub (done above)
# 2. Connect repo to Railway/Render
# 3. Set environment variables in dashboard
# 4. Deploy automatically
```

## Post-Deployment Verification

### Health Checks
```bash
# Backend health
curl http://YOUR_DOMAIN/api/ping

# Frontend
curl http://YOUR_DOMAIN/

# Test login
curl -X POST http://YOUR_DOMAIN/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@cnps.com","password":"tests2"}'
```

### Functional Tests
1. [ ] Login works
2. [ ] Dashboard loads with KPIs
3. [ ] AI Analyst generates reports
4. [ ] Custom Reports can be created
5. [ ] Schema Explorer shows tables
6. [ ] Settings page loads
7. [ ] ETL trigger works
8. [ ] Email notifications send
9. [ ] PWA installs on mobile
10. [ ] Offline mode works

### Performance
- [ ] Dashboard loads in < 3 seconds
- [ ] AI Analyst responds in < 30 seconds
- [ ] Custom Reports export in < 10 seconds
- [ ] No console errors in browser

## Rollback Plan
If issues arise:
```bash
# Docker
docker compose down
git checkout HEAD~1
docker compose up -d

# Manual
# Stop uvicorn process
git checkout HEAD~1
# Restart services
```

## Monitoring
- Backend logs: `docker compose logs -f backend` or check uvicorn output
- Frontend errors: Check browser console
- Database: Monitor Supabase dashboard
- AI: Check Groq usage at console.groq.com

## Support Contacts
- Supabase Dashboard: https://app.supabase.com
- Groq Console: https://console.groq.com
- Brevo Dashboard: https://app.brevo.com
