# SAAS Production Deployment Checklist

## Pre-Deployment Verification ✅

### 1. System Testing
- [ ] Run `python test_system.py` - all tests pass
- [ ] Backend starts without errors
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Database connections work
- [ ] Analysis engine handles errors gracefully
- [ ] NLQ service rejects malicious SQL

### 2. Security Checklist
- [ ] All credentials use environment variables
- [ ] No hardcoded passwords or API keys
- [ ] CORS configured for production domains only
- [ ] SQL injection protection verified
- [ ] Row-level security (RLS) enabled in Supabase
- [ ] HTTPS enforced for all endpoints

### 3. Performance Optimization
- [ ] Database indexes created for key queries
- [ ] Frontend assets optimized and minified
- [ ] CDN configured for static assets
- [ ] Caching headers set appropriately
- [ ] Connection pooling configured

## Production Environment Setup

### 1. Supabase Configuration
```sql
-- Enable RLS on all tables
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE database_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can only see their own data" ON user_roles
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Department isolation" ON kpi_results
  FOR ALL USING (
    user_id IN (
      SELECT user_id FROM user_roles 
      WHERE department_id = (
        SELECT department_id FROM user_roles WHERE user_id = auth.uid()
      )
    )
  );
```

### 2. Environment Variables

**Backend (.env)**
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_ANON_KEY=your-anon-key

# AI Services
GROQ_API_KEY=your-groq-key
GROQ_MODEL=llama-3-70b-8192

# Email
BREVO_API_KEY=your-brevo-key
BREVO_SENDER_EMAIL=noreply@cnps.cm
BREVO_SENDER_NAME=CNPS Analytics

# Security
JWT_SECRET=your-secure-jwt-secret-256-bits
ENCRYPTION_KEY=your-fernet-encryption-key

# Production
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://your-frontend-domain.com
```

**Frontend (.env)**
```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=https://your-backend-domain.com
VITE_APP_NAME=SAAS
VITE_ENVIRONMENT=production
```

### 3. Backend Deployment (Render)

1. **Create Web Service**
   - Repository: Connect your GitHub repo
   - Branch: `main`
   - Root Directory: `backend`
   - Runtime: `Python 3.11`

2. **Build Command**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Command**
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2
   ```

4. **Environment Variables**
   - Add all variables from backend `.env`
   - Set `PORT` to `$PORT` (Render provides this)

### 4. Frontend Deployment (Vercel)

1. **Import Project**
   - Repository: Your GitHub repo
   - Framework: React
   - Root Directory: `frontend`

2. **Build Settings**
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

3. **Environment Variables**
   - Add all variables from frontend `.env`

### 5. Domain Configuration

**Backend Domain (Render)**
- Custom domain: `api.cnps-analytics.cm`
- SSL certificate: Auto-generated

**Frontend Domain (Vercel)**
- Custom domain: `cnps-analytics.cm`
- SSL certificate: Auto-generated

**CORS Update**
```python
# backend/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cnps-analytics.cm",
        "https://www.cnps-analytics.cm"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Post-Deployment Verification

### 1. Smoke Tests
- [ ] Frontend loads without errors
- [ ] User can register/login
- [ ] Dashboard displays data
- [ ] Analysis engine works
- [ ] Email notifications send
- [ ] All API endpoints respond

### 2. Performance Tests
- [ ] Page load time < 3 seconds
- [ ] API response time < 1 second
- [ ] Database queries optimized
- [ ] No memory leaks detected

### 3. Security Tests
- [ ] HTTPS enforced everywhere
- [ ] Authentication required for protected routes
- [ ] SQL injection attempts blocked
- [ ] XSS protection active
- [ ] CSRF protection enabled

## Monitoring & Maintenance

### 1. Application Monitoring
```python
# Add to backend/api/main.py
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0"
    }
```

### 2. Database Monitoring
- Monitor connection pool usage
- Track slow queries (> 1 second)
- Set up automated backups
- Monitor storage usage

### 3. Error Tracking
- Set up Sentry for error tracking
- Monitor API error rates
- Track user session errors
- Set up alerts for critical failures

### 4. Performance Monitoring
- Monitor response times
- Track memory usage
- Monitor CPU utilization
- Set up uptime monitoring

## Backup & Recovery

### 1. Database Backups
- Supabase automatic backups enabled
- Manual backup before major updates
- Test restore procedures monthly

### 2. Code Backups
- GitHub repository with all code
- Tagged releases for each deployment
- Environment configuration documented

### 3. Recovery Procedures
1. **Database Recovery**
   - Restore from Supabase backup
   - Verify data integrity
   - Test application functionality

2. **Application Recovery**
   - Redeploy from GitHub
   - Restore environment variables
   - Verify all services running

## Scaling Considerations

### 1. Horizontal Scaling
- Backend: Increase Render service instances
- Database: Supabase handles scaling automatically
- Frontend: Vercel CDN scales globally

### 2. Performance Optimization
- Implement Redis caching for frequent queries
- Add database read replicas for analytics
- Optimize SQL queries with proper indexes
- Implement API rate limiting

### 3. Cost Optimization
- Monitor usage and optimize resource allocation
- Implement data archiving for old records
- Use CDN for static assets
- Optimize database queries to reduce compute

## Support & Documentation

### 1. User Documentation
- [ ] User manual created
- [ ] Video tutorials recorded
- [ ] FAQ document prepared
- [ ] Support contact information provided

### 2. Technical Documentation
- [ ] API documentation updated
- [ ] Database schema documented
- [ ] Deployment procedures documented
- [ ] Troubleshooting guide created

### 3. Training Materials
- [ ] Admin training guide
- [ ] Manager training guide
- [ ] End-user training materials
- [ ] Technical support procedures

## Go-Live Checklist

### Final Verification (Day of Deployment)
- [ ] All tests pass in production environment
- [ ] DNS records updated and propagated
- [ ] SSL certificates active and valid
- [ ] Monitoring systems active
- [ ] Backup systems verified
- [ ] Support team notified and ready
- [ ] Rollback plan prepared and tested

### Communication
- [ ] Stakeholders notified of go-live
- [ ] User training sessions scheduled
- [ ] Support channels established
- [ ] Success metrics defined and tracking enabled

---

## Emergency Contacts

**Technical Issues:**
- Backend: Render Support (render.com/support)
- Frontend: Vercel Support (vercel.com/support)
- Database: Supabase Support (supabase.com/support)

**System Administrator:** [Your contact info]
**Project Manager:** [Your contact info]

---

**🎉 System is ready for production deployment!**

*Last updated: [Current Date]*
*Version: 2.0*