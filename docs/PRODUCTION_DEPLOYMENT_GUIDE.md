# Production Deployment Guide
## Enterprise Analytics Platform

This guide covers complete production deployment including email configuration, database setup, and verification.

---

## 1. Pre-Deployment Checklist

### Environment Variables Required

Create `backend/.env` with these variables:

```env
# ─── Supabase (Required) ───────────────────────────────────────────────────────
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_KEY=<your-service-role-key>
VITE_SUPABASE_ANON_KEY=<your-anon-key>

# ─── AI / Narrative (Required) ─────────────────────────────────────────────────
GROQ_API_KEY=gsk_<your-groq-key>

# ─── Email - Brevo (Required for emails) ───────────────────────────────────────
BREVO_API_KEY=xkeysib-<your-brevo-key>
EMAIL_SENDER_NAME=Your Organization Name
EMAIL_SENDER_ADDRESS=noreply@yourdomain.com

# ─── App Configuration ─────────────────────────────────────────────────────────
FRONTEND_URL=https://yourdomain.com
UNSUBSCRIBE_SECRET=<random-secret-key-min-32-chars>
INSTITUTION_NAME=Your Organization

# ─── Feature Flags ─────────────────────────────────────────────────────────────
MOCK_DATA=False
```

---

## 2. Email Configuration (Brevo)

### Step 1: Create Brevo Account
1. Go to [brevo.com](https://www.brevo.com/)
2. Sign up for a free account (300 emails/day free tier)
3. Verify your sender email address in Brevo dashboard

### Step 2: Get API Key
1. In Brevo dashboard, go to **Settings → API Keys**
2. Click **Create a new API key**
3. Copy the key (starts with `xkeysib-`)
4. Add to `backend/.env` as `BREVO_API_KEY`

### Step 3: Configure Sender
```env
EMAIL_SENDER_NAME=Your Organization Name
EMAIL_SENDER_ADDRESS=noreply@yourdomain.com
```

**Important:** The sender email must be verified in Brevo.

### Step 4: Test Email Configuration

#### Option A: Using the API Endpoint
```bash
curl -X POST https://your-api-domain.com/api/email/test \
  -H "Content-Type: application/json" \
  -d '{"recipient_email": "your-email@example.com", "test_type": "digest"}'
```

#### Option B: Using the Frontend
1. Log in as admin/manager
2. Go to **Settings → Email Configuration**
3. Click **Send Test Email**
4. Check your inbox

#### Option C: Check Configuration Status
```bash
curl https://your-api-domain.com/api/email/config \
  -H "Authorization: Bearer <your-token>"
```

Expected response:
```json
{
  "brevo_configured": true,
  "brevo_client_ready": true,
  "sender_email": "noreply@yourdomain.com",
  "sender_name": "Your Organization",
  "recipients": ["user@example.com"],
  "recipient_count": 1,
  "status": "ready",
  "missing": []
}
```

### Step 5: Add Email Recipients
Recipients receive automated reports. Add them via:

**API:**
```bash
curl -X POST https://your-api-domain.com/api/email/add-recipient \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "recipient@example.com"}'
```

**Frontend:**
1. Go to **Settings → Notification Recipients**
2. Click **Add Recipient**
3. Enter email address
4. Click **Save**

---

## 3. Database Configuration

### Supabase Setup
1. Create project at [supabase.com](https://supabase.com/)
2. Run migrations in SQL Editor:
   ```sql
   -- Run these files in order:
   backend/migrations/001_initial_schema.sql
   backend/migrations/002_add_user_preferences.sql
   backend/migrations/003_add_database_connections.sql
   backend/migrations/004_add_notification_recipients.sql
   backend/migrations/005_add_report_versions.sql
   backend/migrations/006_fix_database_connections.sql
   ```
3. Get credentials from **Settings → API**

### Oracle Database (Optional)
1. Install Oracle 19C client on server
2. Configure `tnsnames.ora` or use EZCONNECT
3. Test connection in **Settings → Database Connection**

---

## 4. Deployment Steps

### Backend Deployment

#### Option A: Docker (Recommended)
```bash
# Build image
docker build -t saas-backend ./backend

# Run container
docker run -d \
  --name saas-backend \
  -p 8000:8000 \
  --env-file backend/.env \
  saas-backend
```

#### Option B: Direct Python
```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Deployment

#### Build
```bash
cd frontend
npm install
npm run build
```

#### Deploy to Vercel/Netlify
```bash
# Vercel
vercel --prod

# Netlify
netlify deploy --prod --dir=dist
```

---

## 5. Production Verification

### Health Check
```bash
curl https://your-api-domain.com/api/ping
```

Expected:
```json
{"ok": true, "timestamp": "2025-01-15T10:30:00+00:00"}
```

### Email Test
```bash
curl -X POST https://your-api-domain.com/api/email/test \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "recipient_email": "test@example.com",
    "test_type": "digest"
  }'
```

### Database Connection Test
```bash
curl -X POST https://your-api-domain.com/api/test-connection \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "db_type": "oracle",
    "credentials": "oracle://user:pass@host:1521/service"
  }'
```

---

## 6. Common Email Issues & Solutions

### Issue: "BREVO_API_KEY not set"
**Solution:** Add `BREVO_API_KEY` to `backend/.env`

### Issue: "No recipients configured"
**Solution:** Add email recipients via Settings or API

### Issue: "Sender email not verified"
**Solution:** Verify sender email in Brevo dashboard

### Issue: Emails going to spam
**Solution:**
1. Set up SPF/DKIM/DMARC records for your domain
2. Use a professional sender email (not Gmail/Yahoo)
3. Avoid spam trigger words in subject lines

### Issue: "Invalid API key"
**Solution:**
1. Check API key in Brevo dashboard
2. Ensure no extra spaces in `.env` file
3. Restart backend after changing `.env`

---

## 7. Monitoring & Maintenance

### Log Monitoring
```bash
# Backend logs
docker logs -f saas-backend

# Look for email-related logs:
# [2025-01-15 10:30:00] Email sent to user@example.com: <message-id>
# [2025-01-15 10:30:00] WARNING: No recipients for user 123
```

### Email Delivery Monitoring
1. Check Brevo dashboard for delivery stats
2. Monitor bounce rates
3. Review spam complaints

### Database Maintenance
```sql
-- Weekly: Clean old logs
DELETE FROM validation_logs WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM anomaly_records WHERE detected_at < NOW() - INTERVAL '90 days';

-- Monthly: Update statistics
ANALYZE kpi_results;
ANALYZE daily_reports;
```

---

## 8. Security Checklist

- [ ] `UNSUBSCRIBE_SECRET` is a random 32+ character string
- [ ] `BREVO_API_KEY` is not exposed in frontend code
- [ ] Database credentials are encrypted (use `connection_crypto`)
- [ ] CORS origins are set to production domains only
- [ ] HTTPS is enabled (SSL certificate)
- [ ] Rate limiting is enabled
- [ ] SQL injection prevention is active
- [ ] Environment variables are not committed to git

---

## 9. Performance Optimization

### Backend
- Use Redis for caching (replace in-memory cache)
- Enable database connection pooling
- Set up CDN for static assets
- Use gzip compression

### Frontend
- Enable lazy loading for charts
- Implement service worker for offline mode
- Optimize images and assets
- Use CDN for React libraries

---

## 10. Backup & Recovery

### Database Backups
```bash
# Supabase: Enable automatic backups in dashboard
# Or export manually:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Configuration Backups
```bash
# Backup .env file (encrypted)
gpg --symmetric --cipher-algo AES256 backend/.env
```

---

## 11. Support & Troubleshooting

### Email Not Sending?
1. Check `/api/email/config` endpoint
2. Review backend logs for errors
3. Verify Brevo account status
4. Test with `/api/email/test` endpoint

### Database Connection Issues?
1. Verify `DATABASE_URL` in `.env`
2. Check Supabase project status
3. Test connection in Settings page
4. Review firewall/network settings

### Performance Issues?
1. Check database query performance
2. Review cache hit rates
3. Monitor server resources (CPU/RAM)
4. Enable query logging

---

## Quick Start Commands

```bash
# 1. Clone repository
git clone https://github.com/Ellen2005/SAAS.git
cd SAAS

# 2. Setup backend
cd backend
cp .env.example .env
# Edit .env with your values
pip install -r requirements.txt
uvicorn api.main:app --reload

# 3. Setup frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Test email
curl -X POST http://localhost:8000/api/email/test \
  -H "Content-Type: application/json" \
  -d '{"recipient_email": "test@example.com"}'
```

---

## Production URLs

After deployment, update these in `.env`:
- `FRONTEND_URL=https://yourdomain.com`
- `SUPABASE_URL=https://your-project.supabase.co`
- Update CORS origins in `backend/core/env_config.py`

---

## Contact & Support

- **GitHub Issues:** https://github.com/Ellen2005/SAAS/issues
- **Documentation:** See `/docs` folder
- **Email Support:** Configured via Brevo

---

**Last Updated:** 2025-01-15  
**Version:** 1.0.0  
**Status:** Production Ready ✅