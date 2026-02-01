from typing import Any, Optional
from datetime import datetime, timedelta
from threading import Lock

class CacheManager:
    # Gerenciador simples de cache em memória com expiração, restrita a um único processo (Single Worker)
    def __init__(self):
        self._cache = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        # Retorna valor do cache se existir e não expirou
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry['expires_at']:
                    return entry['value']
                else:
                    # Expirou, remover
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        # Armazena valor no cache
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=ttl)
            }
    
    def delete(self, key: str):
        # Remove item do cache
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        # Limpa todo o cache
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self):
        # Remove entradas expiradas
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now >= entry['expires_at']
            ]
            for key in expired_keys:
                del self._cache[key]

# Instância global do cache
cache_manager = CacheManager()
