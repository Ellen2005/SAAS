"""Test Oracle connection."""
from sqlalchemy import create_engine, text

url = "oracle+oracledb://cnps_demo:cnps_demo_2026@localhost:1521/?service_name=ORCLPDB"
print(f"Testing: {url}")
print(f"oracledb version: ", end="")

try:
    import oracledb
    print(oracledb.__version__)
except:
    print("NOT INSTALLED")

try:
    engine = create_engine(
        url,
        connect_args={"tcp_connect_timeout": 10},
        pool_pre_ping=True
    )
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM DUAL")).fetchone()
        print(f"OK: {result[0]}")
        
        # List tables
        tables = conn.execute(text("SELECT table_name FROM user_tables ORDER BY table_name")).fetchall()
        print(f"Tables ({len(tables)}):")
        for t in tables:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t[0]}")).scalar()
            print(f"  - {t[0]}: {cnt:,} rows")
    engine.dispose()
except Exception as e:
    print(f"FAILED: {e}")
    
    # Try without connect_args
    print("\nTrying without connect_args...")
    try:
        engine2 = create_engine(url, pool_pre_ping=True)
        with engine2.connect() as conn2:
            result2 = conn2.execute(text("SELECT 1 FROM DUAL")).fetchone()
            print(f"OK without connect_args: {result2[0]}")
        engine2.dispose()
    except Exception as e2:
        print(f"Also failed: {e2}")