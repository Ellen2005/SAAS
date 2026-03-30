# SAAS: Master Setup & Integration Guide

Welcome to the **Smart Automated Analytics System (SAAS)**. This guide explains how to transition from the current "Mock Mode" to a production-ready environment by connecting your live databases, AI models, and communication services.

---

## 1. Backend Service Configuration (.env)

The Python backend (FastAPI) requires several environment variables to communicate with external services. Create a `.env` file in the `backend/` directory:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# AI / Narrative Configuration
GROQ_API_KEY=gsk_your_groq_key_here
# OR if using local Ollama, ensure it's running on http://localhost:11434

# Email Configuration (Brevo)
BREVO_API_KEY=xkeysib-your-long-api-key
```

### Replacing Mock Logic
Once your keys are added, navigate to `backend/api/core/supabase_client.py` and `backend/api/services/email_service.py` to toggle the `Mock` flags to `False`.

---

## 2. Connecting to Your Department Databases

The ETL pipeline is designed to fetch data from your existing SQL databases. 

### Connecting a Supabase Database (e.g. Analytix360)
If you want to use another Supabase project as your data source:
1.  Log in to your **Supabase Dashboard** for the project you want to connect (e.g., *Analytix360*).
2.  Go to **Project Settings** > **Database**.
3.  Scroll down to **Connection String** and select the **URI** tab.
4.  Copy the URI (e.g. `postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres`).
5.  In the **SAAS App**, go to **Settings** > **Database Connection**.
6.  Enter the **Host** (e.g., `db.xxxx.supabase.co`), **User** (`postgres`), and your **Password**.
7.  Click **Save credentials**.
8.  Scroll down to **System Controls** and click **Trigger Manual Refresh Batch**. 
9.  Wait a few seconds, then check your **Dashboard** to see results from *Analytix360*.

### Local Database Testing
If your database is running on your own computer (e.g., SQL Server, MySQL, Postgres):
1.  Open the **SAAS Settings** page.
2.  Set the **Host URL** to `localhost` or `127.0.0.1`.
3.  Ensure your firewall allows connections on the specific port (e.g., `1433` for SQL Server, `5432` for Postgres).
4.  The backend Python service will act as a bridge, fetching data from your local PC and pushing results to the Supabase cloud.

### Adding New Extractors
To add a new data source, modify `backend/api/services/etl_service.py`. Replace the `extract_from_source` mock logic with a real SQLAlchemy engine:
```python
from sqlalchemy import create_client
engine = create_engine(f"postgresql://{user}:{pw}@{host}:{port}/{db}")
df = pd.read_sql("SELECT * FROM your_table", engine)
```

---

## 3. Customizing the AI Narrative

The system uses LLMs to "read" your data. 
- **Groq (Cloud):** High speed, requires API key.
- **Ollama (Local):** Private and free. Run `ollama run llama3` on your machine, and the `narrative_service.py` will automatically attempt to connect to it if no Groq key is found.

---

## 4. Frontend PWA Installation

SAAS is a Progressive Web App. To install it:
1.  Run the app (`npm run dev`).
2.  Open the URL in Chrome or Edge.
3.  Look for the **"Install App"** icon in the address bar (next to the star/bookmark icon).
4.  Once installed, SAAS will appear as a standalone desktop/mobile app with the custom 3D Crystal logo.

---

## 5. Troubleshooting Sync Issues

- **Sync Time:** You can change the nightly run time in the **Settings > System Controls**. This updates the `APScheduler` on the backend.
- **Manual Trigger:** Use the "Trigger Manual Refresh Batch" button in Settings to force an ETL run instantly for testing.
- **Check Logs:** The FastAPI terminal will output "Extraction complete", "Anomaly detected", and "Email dispatched" in real-time.

---

> [!IMPORTANT]
> **Security Reminder:** Never commit your `.env` file to version control (GitHub/GitLab). Always use secrets management in production environments.
