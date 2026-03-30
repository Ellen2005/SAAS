import os

from supabase import create_client

def get_supabase():
    """
    Returns the real Supabase client if keys are present and MOCK_DATA is False.
    """
    mock_flag = os.getenv("MOCK_DATA", "False").lower() == "true"
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if mock_flag or not supabase_url or not supabase_key:
        # Fallback to mock behavior if requested or keys are missing
        class MockSupabaseClient:
            def table(self, name: str):
                class MockTable:
                    def select(self, *args, **kwargs): return self
                    def insert(self, *args, **kwargs): return self
                    def eq(self, *args, **kwargs): return self
                    def execute(self): return {"data": [], "error": None}
                return MockTable()
        return MockSupabaseClient()
        
    return create_client(supabase_url, supabase_key)
