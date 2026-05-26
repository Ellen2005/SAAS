import os
from pathlib import Path

from supabase import create_client
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class MockSupabaseResponse:
    def __init__(self, data=None, count=0):
        self.data = data or []
        self.count = count


class MockSupabaseTable:
    def __init__(self, name: str):
        self.name = name

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def upsert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def gt(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def contains(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        return MockSupabaseResponse()


class MockSupabaseAuthAdmin:
    def list_users(self, *args, **kwargs):
        class Result:
            users = []

        return Result()


class MockSupabaseAuth:
    def __init__(self):
        self.admin = MockSupabaseAuthAdmin()

    def get_user(self, token):
        class Result:
            user = None

        return Result()


class MockSupabaseClient:
    def __init__(self):
        self.auth = MockSupabaseAuth()

    def table(self, name: str):
        return MockSupabaseTable(name)


def get_supabase():
    """
    Returns the real Supabase client when keys are present.
    The fallback client is empty and never returns demo/business data.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        return MockSupabaseClient()
        
    return create_client(supabase_url, supabase_key)
