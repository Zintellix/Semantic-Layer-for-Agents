import time
from threading import Lock
from typing import Any, Optional, Dict, Tuple

class TTLCache:
    """A lightweight, thread-safe in-memory TTL cache."""
    def __init__(self, ttl_seconds: int = 60, max_size: int = 1000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                expiry, value = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        with self._lock:
            # Simple eviction if cache gets too large
            if len(self._cache) >= self.max_size:
                # Evict expired items first
                now = time.time()
                expired = [k for k, v in self._cache.items() if v[0] < now]
                for k in expired:
                    del self._cache[k]
                
                # If still full, clear the cache (naive eviction for simplicity)
                if len(self._cache) >= self.max_size:
                    self._cache.clear()
                    
            self._cache[key] = (time.time() + self.ttl, value)

    def invalidate(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()

# Global query cache instance (TTL 5 minutes)
query_cache = TTLCache(ttl_seconds=300)

def cached_query(key: str, resolver_func, *args, **kwargs):
    """Helper to fetch from cache or resolve and cache."""
    val = query_cache.get(key)
    if val is not None:
        return val
    val = resolver_func(*args, **kwargs)
    query_cache.set(key, val)
    return val
