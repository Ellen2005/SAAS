import sqlite3
conn = sqlite3.connect("cnps_realistic_demo.db")
c = conn.execute("SELECT MIN(contribution_date), MAX(contribution_date) FROM contributions")
r = c.fetchone()
print(f"Contribution date range: {r[0]} to {r[1]}")
c = conn.execute("SELECT COUNT(*) FROM contributions WHERE contribution_date >= date('now', '-12 months')")
r = c.fetchone()
print(f"Contributions in last 12 months: {r[0]}")
c = conn.execute("SELECT strftime('%Y-%m', contribution_date) AS m, COUNT(*) FROM contributions WHERE contribution_date >= date('now', '-12 months') GROUP BY m ORDER BY m")
rows = c.fetchall()
print(f"Months with data: {len(rows)}")
for row in rows[:15]:
    print(f"  {row[0]}: {row[1]}")
c = conn.execute("SELECT strftime('%Y-%m', contribution_date) AS m FROM contributions GROUP BY m ORDER BY m")
all_months = [r[0] for r in c.fetchall()]
print(f"\nAll months: {all_months}")
