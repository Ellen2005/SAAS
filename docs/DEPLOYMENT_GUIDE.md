# SAAS Deployment Guide

## Production Deployment for CNPS

---

## Option 1: Deploy to Cloud (Fastest — 2 hours)

### Prerequisites
- A **Supabase** account (free tier works for pilot)
- A **Render** or **Railway** account (for backend)
- A **Vercel** or **Netlify** account (for frontend)
- A **Groq** API key (free: https://console.groq.com)
- A **Brevo** API key (free: https://www.brevo.com)

### Step 1: Deploy Supabase Database

1. Go to https://supabase.com → Create a new project
2. Note your **Project URL** and **anon public key** from Settings → API
3. Go to **SQL Editor** → Run all migration files from `backend/migrations/` in order (001 through 013)
4. Go to **Authentication** → Settings → Enable email/password auth

### Step 2: Deploy Backend (Render)

1. Push code to GitHub
2. Go to https://render.com → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
5. Add Environment Variables:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-role-key
   GROQ_API_KEY=your-groq-key
   BREVO_API_KEY=your-brevo-key
   EMAIL_SENDER_ADDRESS=noreply@cnps.cm
   EMAIL_SENDER_NAME=CNPS Analytics
   INSTITUTION_NAME=CNPS
   CORS_ORIGINS=https://your-frontend.vercel.app
   ENVIRONMENT=production
   ```
6. Deploy — note your backend URL (e.g., `https://saas-api.onrender.com`)

### Step 3: Deploy Frontend (Vercel)

1. Go to https://vercel.com → New Project
2. Connect your GitHub repo
3. Settings:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add Environment Variables:
   ```
   VITE_API_URL=https://saas-api.onrender.com
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key
   ```
5. Deploy — your app is live at `https://saas.vercel.app`

### Step 4: Create Admin User

1. Go to your Supabase project → **Authentication** → **Users** → **Add User**
2. Create an admin account (e.g., `admin@cnps.cm`)
3. In Supabase **SQL Editor**, run:
   ```sql
   INSERT INTO user_roles (user_id, role, department_id)
   VALUES (
     (SELECT id FROM auth.users WHERE email = 'admin@cnps.cm' LIMIT 1),
     'admin',
     NULL
   );
   ```

---

## Option 2: Deploy On-Premise (CNPS Datacenter)

### Prerequisites
- 1 Linux VM (Ubuntu 22.04+, 4GB RAM, 2 CPU)
- Docker and Docker Compose installed
- PostgreSQL 15+ (or use Supabase self-hosted)
- Domain name (e.g., `analytics.cnps.cm`)
- SSL certificate (Let's Encrypt)

### Step 1: Server Setup

```bash
# SSH into your server
ssh admin@your-server

# Install Docker
sudo apt update && sudo apt install -y docker.io docker-compose
sudo systemctl enable docker && sudo systemctl start docker

# Clone the repository
git clone https://github.com/Ellen2005/SAAS.git /opt/saas
cd /opt/saas
```

### Step 2: Configure Environment

```bash
# Backend environment
cp backend/.env.example backend/.env
nano backend/.env
```

Edit `backend/.env`:
```
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=your-local-key
SUPABASE_SERVICE_KEY=your-service-key
GROQ_API_KEY=gsk_your_groq_key
BREVO_API_KEY=your_brevo_key
EMAIL_SENDER_ADDRESS=noreply@cnps.cm
EMAIL_SENDER_NAME=CNPS Analytics
INSTITUTION_NAME=CNPS
CORS_ORIGINS=https://analytics.cnps.cm
ENVIRONMENT=production
```

```bash
# Frontend environment
cp frontend/.env.example frontend/.env
nano frontend/.env
```

Edit `frontend/.env`:
```
VITE_API_URL=https://analytics.cnps.cm/api
VITE_SUPABASE_URL=http://localhost:8000
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Step 3: Deploy with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 4: Configure Nginx Reverse Proxy

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/analytics.cnps.cm
```

```
server {
    listen 80;
    server_name analytics.cnps.cm;

    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site and SSL
sudo ln -s /etc/nginx/sites-available/analytics.cnps.cm /etc/nginx/sites-enabled/
sudo certbot --nginx -d analytics.cnps.cm
sudo nginx -t && sudo systemctl reload nginx
```

---

## Option 3: Deploy for CNPS-Only Access (Private Network)

### Method A: VPN-Only Access

1. Deploy on CNPS internal network (no public internet exposure)
2. Configure firewall to allow only CNPS VPN IPs:
   ```bash
   # Allow only CNPS internal subnet
   sudo ufw allow from 10.0.0.0/8 to any port 443
   sudo ufw allow from 172.16.0.0/12 to any port 443
   sudo ufw deny 443
   ```
3. Users connect via CNPS VPN → access `https://analytics.internal.cnps.cm`

### Method B: IP Whitelist + Basic Auth

1. Deploy on a cloud VM with a public IP
2. Configure Nginx with IP whitelist:
   ```
   location / {
       allow CNPS_OFFICE_IP_1;
       allow CNPS_OFFICE_IP_2;
       deny all;
       proxy_pass http://localhost:5173;
   }
   ```
3. Add Basic Auth as a second layer:
   ```bash
   sudo apt install -y apache2-utils
   sudo htpasswd -c /etc/nginx/.htpasswd cnps_admin
   ```
4. Update Nginx config:
   ```
   location / {
       auth_basic "CNPS Analytics";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://localhost:5173;
   }
   ```

### Method C: Supabase Row-Level Security (RLS)

For maximum data isolation, enable RLS on all tables:

```sql
-- Enable RLS on all tables
ALTER TABLE kpi_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomaly_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;

-- Create policies that restrict users to their own data
CREATE POLICY user_isolation ON kpi_results
    USING (user_id = auth.uid());

CREATE POLICY user_isolation ON anomaly_records
    USING (user_id = auth.uid());

CREATE POLICY user_isolation ON daily_reports
    USING (user_id = auth.uid());

CREATE POLICY user_isolation ON validation_logs
    USING (user_id = auth.uid());

CREATE POLICY user_isolation ON analysis_runs
    USING (user_id = auth.uid());
```

---

## Post-Deployment Checklist

- [ ] Backend starts without errors
- [ ] Frontend loads without errors
- [ ] Login works (Supabase Auth)
- [ ] Dashboard loads KPIs
- [ ] Sync/ETL works
- [ ] NLQ queries work
- [ ] AI Analyst loads insights
- [ ] Executive reports generate
- [ ] Email notifications work (test with Brevo)
- [ ] Database indexes applied (migration 013)
- [ ] SSL certificate valid
- [ ] CORS configured correctly
- [ ] Environment variables set (no defaults in production)

---

## Maintenance

### Daily
- Check backend logs: `docker-compose logs --tail=50 backend`
- Check Supabase dashboard for errors

### Weekly
- Review audit logs: `GET /api/audit-log`
- Check validation scorecard in Admin panel

### Monthly
- Run database VACUUM ANALYZE
- Review and rotate API keys
- Backup database (Supabase → Database → Backups)

---

## Security Checklist for CNPS Production

- [ ] All traffic over HTTPS (SSL certificate)
- [ ] JWT tokens in HttpOnly cookies (not localStorage)
- [ ] Rate limiting on auth endpoints (via Nginx)
- [ ] Database connection strings encrypted at rest
- [ ] Row-Level Security (RLS) enabled on all tables
- [ ] Admin access restricted to specific IPs
- [ ] Audit logging enabled for all config changes
- [ ] Regular security updates for dependencies
- [ ] Backups configured (daily automated)
- [ ] Incident response plan documented