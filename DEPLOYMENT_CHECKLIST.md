# SAAS Deployment Checklist

## Pre-Deployment Verification

### ✅ Code Quality
- [x] All Python files pass linting (ruff)
- [x] All JavaScript files pass linting (ESLint)
- [x] No hardcoded credentials in codebase
- [x] All environment variables in .env.example files
- [x] .gitignore properly configured

### ✅ Database Setup
- [ ] Supabase project created
- [ ] All 8 migrations executed in order
- [ ] Admin user bootstrapped via SQL function
- [ ] RLS policies verified and tested
- [ ] Database indexes created for performance

### ✅ Backend Configuration
- [ ] `backend/.env` configured with all required variables:
  - [ ] SUPABASE_URL
  - [ ] SUPABASE_SERVICE_KEY
  - [ ] GROQ_API_KEY (starts with `gsk_`)
  - [ ] BREVO_API_KEY (starts with `xkeysib-`)
  - [ ] EMAIL_SENDER_ADDRESS (verified in Brevo)
  - [ ] MOCK_DATA=False (for production)

### ✅ Frontend Configuration
- [ ] `frontend/.env` configured with:
  - [ ] VITE_SUPABASE_URL
  - [ ] VITE_SUPABASE_ANON_KEY
  - [ ] VITE_API_URL (set to production backend URL)

### ✅ Security Checks
- [ ] CORS origins updated in `backend/api/main.py`
- [ ] JWT authentication working on all protected endpoints
- [ ] RLS policies preventing cross-tenant access
- [ ] Credentials encrypted with Fernet
- [ ] No sensitive data in logs

### ✅ PWA Configuration
- [ ] `manifest.webmanifest` present and valid
- [ ] PWA icons (192x192, 512x512) present
- [ ] Service worker configured with Workbox
- [ ] Offline functionality tested
- [ ] Install prompt working

### ✅ Testing
- [ ] Backend tests passing (`pytest tests/`)
- [ ] Manual testing guide followed
- [ ] ETL pipeline tested end-to-end
- [ ] Email delivery tested (Brevo simulation or real)
- [ ] Multi-tenant isolation verified

---

## Deployment Steps

### Step 1: Database Setup (Supabase)

1. **Create Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create new project
   - Note project URL and keys

2. **Run Migrations**
   ```sql
   -- Execute in Supabase SQL Editor in order:
   -- 1. backend/migrations/001_governed_mesh.sql
   -- 2. backend/migrations/002_seed_test_data.sql (optional)
   -- 3. backend/migrations/003_forecasts_audit.sql
   -- 4. backend/migrations/004_insight_snapshots.sql
   -- 5. backend/migrations/005_remove_legacy_demo_data.sql
   -- 6. backend/migrations/006_fix_database_connections.sql
   -- 7. backend/migrations/007_empty_kpi_template.sql
   -- 8. backend/migrations/008_remove_legacy_seed_kpis.sql
   ```

3. **Bootstrap Admin**
   ```sql
   SELECT bootstrap_admin('your-email@company.com');
   ```

4. **Verify Tables**
   - Check all tables exist in Table Editor
   - Verify RLS is enabled on all tables
   - Test that policies work correctly

---

### Step 2: Backend Deployment (Render)

1. **Create Web Service**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect GitHub repository

2. **Configure Build**
   - **Name**: `saas-backend`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: (leave blank)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

3. **Add Environment Variables**
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   GROQ_API_KEY=gsk_your-groq-key
   BREVO_API_KEY=xkeysib_your-brevo-key
   EMAIL_SENDER_ADDRESS=verified@your-domain.com
   EMAIL_SENDER_NAME=SAAS Analytics
   MOCK_DATA=False
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Note the generated URL (e.g., `https://saas-backend.onrender.com`)

5. **Verify Backend**
   ```bash
   curl https://your-backend.onrender.com/api/ping
   # Should return: {"ok": true}
   ```

---

### Step 3: Frontend Deployment (Vercel)

1. **Import to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New..." → "Project"
   - Import GitHub repository

2. **Configure Project**
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

3. **Add Environment Variables**
   ```
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key
   VITE_API_URL=https://your-backend.onrender.com
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for build to complete
   - Note the generated URL (e.g., `https://saas-frontend.vercel.app`)

5. **Verify Frontend**
   - Open the Vercel URL in browser
   - Should see login page
   - PWA install prompt should appear

---

### Step 4: Update CORS

1. **Edit `backend/api/main.py`**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://saas-frontend.vercel.app",  # Your Vercel URL
           "http://localhost:5173",
           "http://localhost:5174",
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Commit and Push**
   ```bash
   git add backend/api/main.py
   git commit -m "chore: update CORS for production deployment"
   git push origin main
   ```

3. **Verify Render Redeploys**
   - Check Render dashboard for automatic redeploy
   - Wait for deployment to complete

---

### Step 5: Keep-Alive for Supabase

1. **Set Up Cron Job**
   ```bash
   # Add to your server's crontab (runs every 5 minutes)
   */5 * * * * curl -s https://your-backend.onrender.com/api/ping > /dev/null
   ```

2. **Alternative: Use UptimeRobot**
   - Create free account at [uptimerobot.com](https://uptimerobot.com)
   - Add new monitor: `https://your-backend.onrender.com/api/ping`
   - Set interval to 5 minutes

---

### Step 6: Final Verification

1. **Test Authentication**
   - [ ] Sign up with email
   - [ ] Verify email received
   - [ ] Log in successfully
   - [ ] Session persists on refresh

2. **Test Database Connection**
   - [ ] Go to Settings → Source Connectivity
   - [ ] Enter test database credentials
   - [ ] Click "Test Connection" → should succeed
   - [ ] Click "Save Connection"

3. **Test ETL Pipeline**
   - [ ] Click "Sync Now" on Dashboard
   - [ ] Watch progress updates (8 stages)
   - [ ] Verify KPI cards appear
   - [ ] Check AI narrative generated

4. **Test Email Delivery**
   - [ ] Add email recipients in Settings
   - [ ] Trigger ETL pipeline
   - [ ] Verify email received with:
     - [ ] AI narrative
     - [ ] KPI status table
     - [ ] Anomaly alerts
     - [ ] Trend chart

5. **Test Admin Features**
   - [ ] Bootstrap admin user
   - [ ] Log in as admin
   - [ ] Access Admin Dashboard
   - [ ] Create department
   - [ ] Assign user to department
   - [ ] Create semantic template

6. **Test PWA**
   - [ ] Install prompt appears
   - [ ] App installs to home screen
   - [ ] App opens in standalone mode
   - [ ] Offline mode works (disable network)
   - [ ] Cache updates on reconnect

7. **Test Multi-Tenant Isolation**
   - [ ] Create two test users
   - [ ] Log in as User A, add data
   - [ ] Log in as User B, verify cannot see User A's data
   - [ ] Log in as admin, verify can see all data

---

## Post-Deployment Monitoring

### Performance Monitoring
- [ ] Set up Render dashboard monitoring
- [ ] Set up Vercel analytics
- [ ] Monitor Supabase usage (free tier limits)
- [ ] Track Groq API usage (rate limits)
- [ ] Monitor Brevo email quota (300/day limit)

### Error Tracking
- [ ] Set up error logging service (e.g., Sentry)
- [ ] Configure alerts for critical errors
- [ ] Monitor ETL pipeline failures
- [ ] Track email delivery failures

### Security Monitoring
- [ ] Review audit logs regularly
- [ ] Monitor for unusual API access patterns
- [ ] Check for failed authentication attempts
- [ ] Verify RLS policies are working

---

## Troubleshooting Guide

### Issue: Backend returns 500 errors
**Solution**: Check Render logs, verify environment variables, ensure Supabase connection works

### Issue: Frontend shows blank page
**Solution**: Check browser console for errors, verify VITE_API_URL is correct, check CORS settings

### Issue: ETL pipeline times out
**Solution**: Increase Render instance resources, optimize database queries, reduce dataset size

### Issue: Email not delivered
**Solution**: Verify Brevo API key, check EMAIL_SENDER_ADDRESS is verified in Brevo, check spam folder

### Issue: PWA install prompt doesn't appear
**Solution**: Ensure site is served over HTTPS, verify manifest.webmanifest is valid, check browser compatibility

### Issue: Supabase pauses after inactivity
**Solution**: Ensure keep-alive cron job is running, consider upgrading to paid Supabase tier

---

## Rollback Procedure

If deployment fails, follow these steps:

1. **Identify the Issue**
   - Check Render/Vercel deployment logs
   - Review error messages
   - Determine if issue is backend or frontend

2. **Rollback Backend (Render)**
   - Go to Render dashboard
   - Find the deployment that caused issues
   - Click "Rollback" to previous version
   - Wait for rollback to complete

3. **Rollback Frontend (Vercel)**
   - Go to Vercel dashboard
   - Find the deployment that caused issues
   - Click "..." → "Rollback"
   - Wait for rollback to complete

4. **Fix and Redeploy**
   - Fix the identified issue locally
   - Test thoroughly
   - Commit and push changes
   - Monitor new deployment

---

## Support Contacts

### Documentation
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Setup Guide**: `docs/SETUP_GUIDE.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Complete Report**: `docs/PROJECT_REPORT_COMPLETE.md`

### Community
- **GitHub Issues**: [github.com/Ellen2005/SAAS/issues](https://github.com/Ellen2005/SAAS/issues)
- **Discussions**: [github.com/Ellen2005/SAAS/discussions](https://github.com/Ellen2005/SAAS/discussions)

### Emergency Contacts
- **Render Support**: [render.com/support](https://render.com/support)
- **Vercel Support**: [vercel.com/support](https://vercel.com/support)
- **Supabase Support**: [supabase.com/support](https://supabase.com/support)

---

## Checklist Completion

- [ ] All pre-deployment items verified
- [ ] Database setup complete
- [ ] Backend deployed and verified
- [ ] Frontend deployed and verified
- [ ] CORS updated and deployed
- [ ] Keep-alive configured
- [ ] All tests passing
- [ ] Monitoring set up
- [ ] Documentation reviewed
- [ ] Ready for production use

---

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Production URL**: _______________  
**Admin Email**: _______________

---

*Last updated: May 26, 2026*