import tempfile, os, sqlite3
from backend.api.services.nlq_service import run_nlq

fd, path = tempfile.mkstemp(suffix='.db')
os.close(fd)
try:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE rna_sequences (id INTEGER PRIMARY KEY, accession TEXT, sequence TEXT)")
    conn.executemany("INSERT INTO rna_sequences (accession, sequence) VALUES (?, ?)", [("RNA001","AUGC"),("RNA002","GGCA")])
    conn.commit()
    conn.close()

    class Response:
        data = [{"credentials": f"sqlite:///{path}", "db_type": "sqlite", "connection_method": "direct"}]

    class Query:
        def select(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def limit(self, *args, **kwargs): return self
        def execute(self): return Response()

    class Supabase:
        def table(self, name): return Query()

    out = run_nlq("user-1", "list all tables", Supabase())
    print('SQL:', out.get('sql'))
    print('Row count:', out.get('row_count'))
    print('Rows:', out.get('rows'))
    print('Schema hint:\n', out.get('schema_used'))
finally:
    try:
        os.remove(path)
    except Exception:
        pass
