"""
Check Oracle configuration — find service names and PDBs.
"""
import sys
import os

try:
    import oracledb
except ImportError:
    print("Installing oracledb...")
    os.system(f"{sys.executable} -m pip install oracledb")
    import oracledb

# Try connecting as sysdba (thick mode for local)
try:
    oracledb.init_oracle_client()
except Exception:
    pass  # thin mode works too

try:
    # Thin mode connection works without Oracle client
    conn = oracledb.connect(
        user="sys",
        password="oracle",  # common default
        dsn="localhost:1521/XEPDB1",
        mode=oracledb.AUTH_MODE_SYSDBA,
    )
except Exception as e:
    print(f"XEPDB1 failed: {e}")
    try:
        conn = oracledb.connect(
            user="sys",
            password="oracle",
            dsn="localhost:1521/XE",
            mode=oracledb.AUTH_MODE_SYSDBA,
        )
    except Exception as e2:
        print(f"XE also failed: {e2}")
        try:
            conn = oracledb.connect(
                user="sys",
                password="oracle",
                dsn="localhost:1521/ORCLPDB",
                mode=oracledb.AUTH_MODE_SYSDBA,
            )
        except Exception as e3:
            print(f"ORCLPDB also failed: {e3}")
            print("\nCould not auto-detect. Ask user for password.")
            sys.exit(1)

# Query services
cursor = conn.cursor()
print("\n=== Oracle Services ===")
cursor.execute("SELECT name, pdb FROM v$services ORDER BY name")
for row in cursor.fetchall():
    print(f"  Service: {row[0]:20s}  PDB: {row[1] or 'CDB$ROOT'}")

print("\n=== Pluggable Databases ===")
cursor.execute("SELECT name, open_mode FROM v$pdbs")
for row in cursor.fetchall():
    print(f"  {row[0]:20s}  Mode: {row[1]}")

print("\n=== CDB Info ===")
cursor.execute("SELECT name, open_mode FROM v$database")
row = cursor.fetchone()
if row:
    print(f"  DB: {row[0]:20s}  Mode: {row[1]}")

print("\n=== TNS Listener Status ===")
cursor.execute("SELECT value FROM v$parameter WHERE name = 'local_listener'")
for row in cursor.fetchall():
    print(f"  Listener: {row[0]}")

print("\n=== Users that exist ===")
cursor.execute("SELECT username FROM dba_users WHERE username LIKE 'CNPS%' OR username LIKE '%DEMO%'")
users = cursor.fetchall()
if users:
    for row in users:
        print(f"  {row[0]}")
else:
    print("  No CNPS/DEMO users found yet")

conn.close()
print("\n✅ Done.")