# 🚀 Quick Start Guide - SAAS Application

## Prerequisites

- Python 3.11+ 
- Node.js 18+
- Docker (optional, for containerized deployment)
- PostgreSQL or compatible database

## Setup in 5 Minutes

### 1. Clone & Navigate
```bash
git clone https://github.com/yourusername/saas.git
cd saas
```

### 2. Configure Environment
```bash
# Copy template and edit with your values
cp backend/.env.example backend/.env
nano backend/.env  # or edit in your editor
```

**Required values:**
- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service key
- `GROQ_API_KEY` - Groq API key

### 3. Validate Before Deployment
```bash
# Run pre-deployment checks (ALL MUST PASS)
python deployment_checklist.py
```

Expected output: `✅ ALL CHECKS PASSED - Ready for deployment!`

### 4. Option A: Docker Deployment (Recommended)
```bash
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:5000
# Health: curl http://localhost:8000/api/ping
```

### 4. Option B: Local Development
```bash
# Terminal 1 - Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn api.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev

# Terminal 3 - Run tests
pytest tests/ -v
```

## Verify Installation

```bash
# All tests should pass (28/28)
python -m pytest tests/ -v

# Backend should respond
curl http://localhost:8000/api/ping
# Response: {"ok": true}

# Frontend should load
open http://localhost:5000
```

## Common Issues

### "ImportError: No module named 'backend'"
```bash
# Run from project root, not from backend directory
cd .. && python -m pytest tests/
```

### "NameError: 'UTC' is not defined"
- Ensure you have Python 3.11+ (UTC was added in Python 3.11)
- Check: `python --version`

### "401 Unauthorized"
- This is expected! The API requires authentication
- Only `/api/ping` and `/favicon.ico` are public
- Tests handle auth internally

### Database Connection Error
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

## Production Deployment

### Pre-deployment Checklist
- [ ] All 28 tests pass: `pytest tests/ -v`
- [ ] Deployment checklist passes: `python deployment_checklist.py`
- [ ] Environment variables validated
- [ ] Database migrations applied
- [ ] `.env` file is NOT committed to git

### Deploy to Heroku
```bash
# Install Heroku CLI and login
heroku create your-app-name
heroku buildpacks:set heroku/python
heroku config:set DATABASE_URL="..."
heroku config:set SUPABASE_URL="..."
heroku config:set SUPABASE_SERVICE_KEY="..."
heroku config:set GROQ_API_KEY="..."
git push heroku main
```

### Deploy to AWS
```bash
# Using Elastic Beanstalk
eb init -p python-3.11 saas-app
eb create production
eb setenv DATABASE_URL="..." SUPABASE_URL="..." ...
eb deploy
```

### Deploy to Railway
```bash
# Via GitHub integration (easiest)
# 1. Push to GitHub
# 2. Connect GitHub repo in Railway dashboard
# 3. Add environment variables
# 4. Deploy
```

## Security Checklist

- [ ] Never commit `.env` file (it's in `.gitignore`)
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS in production (set `FRONTEND_URL` to https://...)
- [ ] Verify CORS_ORIGINS in production mode
- [ ] Check security headers are present: `curl -I http://localhost:8000/`

## Documentation

- 📖 [Full Deployment Guide](docs/DEPLOYMENT_READY_REPORT.md)
- 🏗️ [Architecture Overview](docs/ARCHITECTURE_UML.md)
- 🔧 [Setup Guide](docs/SETUP_GUIDE.md)
- 🧪 [Testing Guide](docs/TESTING_GUIDE.md)

## Support

- GitHub Issues: [Report a bug](https://github.com/yourusername/saas/issues)
- Documentation: See `docs/` folder
- Deployment: See [DEPLOYMENT_READY_REPORT.md](docs/DEPLOYMENT_READY_REPORT.md)

---

**Status:** ✅ Production Ready | **Tests:** 28/28 Passing | **Version:** 1.0.0
