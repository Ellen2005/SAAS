import time
import logging
import threading
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_engine_cache: dict[str, tuple[Engine, float]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 300
_MAX_CACHED = 50


def get_engine(credentials: str, db_type: str, **kwargs) -> Engine:
    from .connection_utils import normalize_credentials, sqlalchemy_engine_kwargs
    key = f"{db_type}::{credentials[:80]}"
    now = time.time()
    with _cache_lock:
        if key in _engine_cache:
            engine, cached_at = _engine_cache[key]
            if now - cached_at < _CACHE_TTL:
                return engine
            try:
                engine.dispose()
            except Exception:
                pass
        engine = create_engine(
            normalize_credentials(credentials, db_type),
            **sqlalchemy_engine_kwargs(credentials, db_type),
        )
        if len(_engine_cache) >= _MAX_CACHED:
            oldest = min(_engine_cache.keys(), key=lambda k: _engine_cache[k][1])
            try:
                _engine_cache[oldest][0].dispose()
            except Exception:
                pass
            del _engine_cache[oldest]
        _engine_cache[key] = (engine, now)
        return engine


def dispose_all():
    with _cache_lock:
        for key, (engine, _) in list(_engine_cache.items()):
            try:
                engine.dispose()
            except Exception:
                pass
        _engine_cache.clear()
