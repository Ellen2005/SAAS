import sqlite3
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cnps_sample.db")

# Sample pools for generating realistic customer data
FIRST_NAMES = ["John", "Sarah", "David", "Emma", "Michael", "Olivia", "James", "Sophia", "Robert", "Isabella", "William", "Mia", "Joseph", "Charlotte", "Daniel", "Amelia", "Matthew", "Harper", "Andrew", "Evelyn"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
SEGMENTS = ["Enterprise", "Mid-Market", "SMB"]
CHANNELS = ["Email", "Web", "In-App"]

# Feedback templates categorized by score sentiment
PROMOTER_FEEDBACK = [
    "Absolutely stellar customer service! The dashboard is incredibly fast and intuitive. We've scaled our usage by 50% without a single hitch.",
    "The new integration features are exactly what our enterprise team needed. Highly recommend for any corporate client.",
    "Very satisfied with the speed and reliability. Customer support responded in less than 5 minutes when I had a question about billing.",
    "Perfect product for our workflow. Clean interface, no clutter, and extremely stable.",
    "Amazing performance! We've migrated all our operations to this platform and the team is loving the productivity boost.",
    "The reporting module is exceptionally detailed. Love the automatic export and automated scheduling features.",
    "Excellent onboarding experience. The account manager was highly knowledgeable and helped us configure everything perfectly.",
    "Best software in this category. Regular updates, premium feel, and outstanding responsiveness.",
    "So easy to use! My team adopted it within one day. No training was necessary.",
    "Great product value. The pricing structure is extremely fair for the depth of features offered."
]

PASSIVE_FEEDBACK = [
    "The software is decent and does the job, but the loading speeds could be improved during peak European hours.",
    "Good tool with solid features, though I wish there was a more direct integration with our Slack workspace.",
    "It works fine for the most part, but the reporting charts are occasionally sluggish when rendering large datasets.",
    "Satisfied overall, but the interface feels a bit dense. A simplified view option would be great.",
    "Good value for money. It lacks some of the advanced enterprise features of competitors, but it is highly stable.",
    "The core features are good, but I encountered a minor bug when updating our user permission rules.",
    "It's a useful system, but the documentation is a bit outdated regarding the latest API release.",
    "Fairly good experience. Customer support took about two hours to respond, which is okay but could be faster.",
    "Nice app, but the mobile version needs some UI enhancements to match the web experience.",
    "Solid platform, though the billing invoice layout is slightly confusing for our accounting department."
]

DETRACTOR_FEEDBACK = [
    "Extremely frustrated with the constant slow-downs. The system occasionally freezes when saving heavy reports.",
    "The UI is overly complicated and hard for new hires to navigate. We need more intuitive workflows.",
    "Very slow support response times. It took over 24 hours to get an answer to a critical configuration question.",
    "Too expensive for what it offers. Several advertised features are still marked as 'coming soon' or feel incomplete.",
    "The system is buggy and we've experienced two minor service disruptions during our weekly sync sessions this month.",
    "Disappointed with the lack of direct data exports. Doing it manually via the CSV interface is extremely tedious.",
    "We need better permission controls. Currently, it is too easy for managers to accidentally modify admin templates.",
    "The recent software update broke our custom webhook mapping. We had to spend hours restoring it.",
    "The search interface is terrible. It rarely finds matching client IDs unless typed exactly with hyphens.",
    "We are considering switching to a competitor. The system lacks the robustness we require for high-volume tasks."
]

def main():
    print(f"Generating SQLite CNPS sample database at: {DB_PATH}")
    
    # Remove existing database if it exists to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database file.")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create tables
    cursor.execute("""
    CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        segment TEXT NOT NULL,
        signup_date TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE nps_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        score INTEGER NOT NULL,
        feedback_text TEXT,
        submitted_at TEXT NOT NULL,
        channel TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """)
    
    # 2. Generate and insert 120 customers
    customers = []
    start_date = datetime.now() - timedelta(days=120)
    for i in range(1, 121):
        cust_id = f"CUST-{i:04d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}{random.randint(10,99)}@example.com"
        segment = random.choice(SEGMENTS)
        signup_dt = (start_date + timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        customers.append((cust_id, name, email, segment, signup_dt))
        
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?);", customers)
    print(f"Inserted {len(customers)} customers.")
    
    # 3. Generate and insert bulky NPS responses over the last 90 days
    nps_records = []
    base_date = datetime.now() - timedelta(days=90)
    
    # Let's write ~1,500 NPS records
    # To simulate a realistic trend, we can increase the customer score slightly over time (representing a successful product iteration)
    # We also give different distributions per customer segment:
    # - Enterprise: High satisfaction (70% promoters, 20% passives, 10% detractors)
    # - Mid-Market: Medium satisfaction (50% promoters, 35% passives, 15% detractors)
    # - SMB: Mixed satisfaction (40% promoters, 30% passives, 30% detractors)
    
    feedback_id = 1
    for day in range(91):
        current_date = (base_date + timedelta(days=day)).strftime("%Y-%m-%d")
        # Generate 12 to 22 submissions per day to make it bulky
        daily_count = random.randint(12, 22)
        
        for _ in range(daily_count):
            customer = random.choice(customers)
            cust_id, _, _, segment, _ = customer
            channel = random.choice(CHANNELS)
            
            # Determine score distribution based on segment
            rand_val = random.random()
            if segment == "Enterprise":
                if rand_val < 0.70:
                    score = random.randint(9, 10)
                    feedback = random.choice(PROMOTER_FEEDBACK)
                elif rand_val < 0.90:
                    score = random.randint(7, 8)
                    feedback = random.choice(PASSIVE_FEEDBACK)
                else:
                    score = random.randint(2, 6) # Detractor (0-6)
                    feedback = random.choice(DETRACTOR_FEEDBACK)
            elif segment == "Mid-Market":
                if rand_val < 0.50:
                    score = random.randint(9, 10)
                    feedback = random.choice(PROMOTER_FEEDBACK)
                elif rand_val < 0.85:
                    score = random.randint(7, 8)
                    feedback = random.choice(PASSIVE_FEEDBACK)
                else:
                    score = random.randint(1, 6)
                    feedback = random.choice(DETRACTOR_FEEDBACK)
            else: # SMB
                if rand_val < 0.40:
                    score = random.randint(9, 10)
                    feedback = random.choice(PROMOTER_FEEDBACK)
                elif rand_val < 0.70:
                    score = random.randint(7, 8)
                    feedback = random.choice(PASSIVE_FEEDBACK)
                else:
                    score = random.randint(0, 6)
                    feedback = random.choice(DETRACTOR_FEEDBACK)
            
            # Add some variations to the feedback to make them feel highly unique
            feedback = f"{feedback} [Ref: Tx-{feedback_id:05d}]"
            nps_records.append((cust_id, score, feedback, current_date, channel))
            feedback_id += 1
            
    cursor.executemany("INSERT INTO nps_feedback (customer_id, score, feedback_text, submitted_at, channel) VALUES (?, ?, ?, ?, ?);", nps_records)
    conn.commit()
    print(f"Inserted {len(nps_records)} NPS feedback records successfully.")
    
    # 4. Verify count
    cursor.execute("SELECT COUNT(*) FROM nps_feedback;")
    total_feedback = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(score) FROM nps_feedback;")
    avg_score = cursor.fetchone()[0]
    
    # 5. Let's create a dynamic view for dynamic NPS calculation just in case the user wants it!
    cursor.execute("""
    CREATE VIEW v_nps_summary AS
    SELECT 
        submitted_at,
        COUNT(*) AS total_responses,
        SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END) AS promoters,
        SUM(CASE WHEN score >= 7 AND score <= 8 THEN 1 ELSE 0 END) AS passives,
        SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END) AS detractors,
        ROUND(
            (CAST(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100) - 
            (CAST(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100), 
            1
        ) AS nps_score
    FROM nps_feedback
    GROUP BY submitted_at;
    """)
    conn.commit()
    conn.close()
    
    print("\nDatabase Generation Complete!")
    print(f"Total Feedback Generated: {total_feedback}")
    print(f"Average Score: {avg_score:.2f}")
    print("Created SQLite View `v_nps_summary` for dynamically calculating NPS over time.")

if __name__ == "__main__":
    main()
