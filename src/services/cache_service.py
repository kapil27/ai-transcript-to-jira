"""Advanced caching service with multiple backends and performance optimization."""

import hashlib
import json
import time
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
import threading
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import diskcache as dc
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False

from ..utils import LoggerMixin
from ..config import get_config


class CacheService(LoggerMixin):
    """Advanced caching service with multiple backends and performance optimization."""
    
    def __init__(self):
        """Initialize caching service with fallback backends."""
        self.config = get_config()
        self._memory_cache = {}
        self._memory_cache_ttl = {}
        self._cache_lock = threading.RLock()
        
        # Initialize cache backends (with fallbacks)
        self._redis_client = None
        self._disk_cache = None
        self._setup_cache_backends()
        
        # Cache configuration
        self.default_ttl = 3600  # 1 hour default TTL
        self.max_memory_items = 1000
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # AI-specific cache settings
        self.ai_cache_ttl = 7200  # 2 hours for AI responses
        self.transcript_cache_ttl = 1800  # 30 minutes for transcript analysis
        self.context_cache_ttl = 3600  # 1 hour for context processing
        
    def _setup_cache_backends(self):
        """Setup cache backends with fallback strategy."""
        # Try Redis first (best performance for production)
        if REDIS_AVAILABLE:
            try:
                redis_url = getattr(self.config, 'redis_url', 'redis://localhost:6379/0')
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self._redis_client.ping()
                self.logger.info("Redis cache backend initialized successfully")
                return
            except Exception as e:
                self.logger.warning(f"Redis not available, falling back to disk cache: {e}")
        
        # Try DiskCache second (persistent, good performance)
        if DISKCACHE_AVAILABLE:
            try:
                cache_dir = getattr(self.config, 'cache_directory', './cache')
                self._disk_cache = dc.Cache(cache_dir, size_limit=100 * 1024 * 1024)  # 100MB limit
                self.logger.info("Disk cache backend initialized successfully")
                return
            except Exception as e:
                self.logger.warning(f"Disk cache not available, using memory only: {e}")
        
        # Fallback to memory cache only
        self.logger.info("Using in-memory cache only (not persistent)")
    
    def _generate_cache_key(self, prefix: str, data: Union[str, Dict[str, Any]]) -> str:
        """Generate consistent cache key from data."""
        if isinstance(data, dict):
            # Sort dict keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        # Create hash for consistent key length
        hash_obj = hashlib.sha256(data_str.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()[:16]}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with fallback strategy."""
        with self._cache_lock:
            # Try Redis first
            if self._redis_client:
                try:
                    value = self._redis_client.get(key)
                    if value is not None:
                        self.cache_stats['hits'] += 1
                        return json.loads(value)
                except Exception as e:
                    self.logger.warning(f"Redis get failed: {e}")
            
            # Try disk cache
            if self._disk_cache:
                try:
                    value = self._disk_cache.get(key)
                    if value is not None:
                        self.cache_stats['hits'] += 1
                        return value
                except Exception as e:
                    self.logger.warning(f"Disk cache get failed: {e}")
            
            # Try memory cache
            if key in self._memory_cache:
                # Check TTL
                if key in self._memory_cache_ttl:
                    if time.time() > self._memory_cache_ttl[key]:
                        # Expired
                        del self._memory_cache[key]
                        del self._memory_cache_ttl[key]
                        self.cache_stats['misses'] += 1
                        return None
                
                self.cache_stats['hits'] += 1
                return self._memory_cache[key]
            
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        with self._cache_lock:
            success = False
            
            # Try Redis first
            if self._redis_client:
                try:
                    self._redis_client.setex(key, ttl, json.dumps(value))
                    success = True
                except Exception as e:
                    self.logger.warning(f"Redis set failed: {e}")
            
            # Try disk cache
            if self._disk_cache:
                try:
                    self._disk_cache.set(key, value, expire=ttl)
                    success = True
                except Exception as e:
                    self.logger.warning(f"Disk cache set failed: {e}")
            
            # Always update memory cache as fallback
            self._memory_cache[key] = value
            self._memory_cache_ttl[key] = time.time() + ttl
            
            # Clean up memory cache if too large
            if len(self._memory_cache) > self.max_memory_items:
                self._cleanup_memory_cache()
            
            self.cache_stats['sets'] += 1
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from all cache backends."""
        with self._cache_lock:
            deleted = False
            
            # Delete from Redis
            if self._redis_client:
                try:
                    self._redis_client.delete(key)
                    deleted = True
                except Exception as e:
                    self.logger.warning(f"Redis delete failed: {e}")
            
            # Delete from disk cache
            if self._disk_cache:
                try:
                    self._disk_cache.delete(key)
                    deleted = True
                except Exception as e:
                    self.logger.warning(f"Disk cache delete failed: {e}")
            
            # Delete from memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
                if key in self._memory_cache_ttl:
                    del self._memory_cache_ttl[key]
                deleted = True
            
            if deleted:
                self.cache_stats['deletes'] += 1
            
            return deleted
    
    def _cleanup_memory_cache(self):
        """Clean up expired and oldest items from memory cache."""
        current_time = time.time()
        
        # Remove expired items
        expired_keys = [
            key for key, expire_time in self._memory_cache_ttl.items()
            if current_time > expire_time
        ]
        
        for key in expired_keys:
            del self._memory_cache[key]
            del self._memory_cache_ttl[key]
        
        # If still too many items, remove oldest ones
        if len(self._memory_cache) > self.max_memory_items:
            # Sort by expiration time and remove oldest
            sorted_items = sorted(
                self._memory_cache_ttl.items(),
                key=lambda x: x[1]
            )
            
            items_to_remove = len(self._memory_cache) - self.max_memory_items + 100
            for key, _ in sorted_items[:items_to_remove]:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                if key in self._memory_cache_ttl:
                    del self._memory_cache_ttl[key]
    
    def cache_ai_response(self, transcript: str, context: str, response_type: str, response: Any) -> str:
        """Cache AI response with specific key generation."""
        cache_data = {
            'transcript': transcript,
            'context': context,
            'response_type': response_type
        }
        
        key = self._generate_cache_key(f"ai_{response_type}", cache_data)
        
        cache_entry = {
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'response_type': response_type
        }
        
        self.set(key, cache_entry, self.ai_cache_ttl)
        self.logger.info(f"Cached AI response: {response_type} (key: {key[:20]}...)")
        return key
    
    def get_ai_response(self, transcript: str, context: str, response_type: str) -> Optional[Any]:
        """Get cached AI response."""
        cache_data = {
            'transcript': transcript,
            'context': context,
            'response_type': response_type
        }
        
        key = self._generate_cache_key(f"ai_{response_type}", cache_data)
        cached_entry = self.get(key)
        
        if cached_entry:
            self.logger.info(f"Cache HIT: {response_type} (key: {key[:20]}...)")
            return cached_entry['response']
        
        self.logger.info(f"Cache MISS: {response_type} (key: {key[:20]}...)")
        return None
    
    def cache_transcript_analysis(self, transcript: str, context: str, analysis: Dict[str, Any]) -> str:
        """Cache complete transcript analysis result."""
        key = self._generate_cache_key("transcript_analysis", {
            'transcript': transcript,
            'context': context
        })
        
        cache_entry = {
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        self.set(key, cache_entry, self.transcript_cache_ttl)
        self.logger.info(f"Cached transcript analysis (key: {key[:20]}...)")
        return key
    
    def get_transcript_analysis(self, transcript: str, context: str) -> Optional[Dict[str, Any]]:
        """Get cached transcript analysis."""
        key = self._generate_cache_key("transcript_analysis", {
            'transcript': transcript,
            'context': context
        })
        
        cached_entry = self.get(key)
        if cached_entry:
            self.logger.info(f"Cache HIT: transcript analysis (key: {key[:20]}...)")
            return cached_entry['analysis']
        
        self.logger.info(f"Cache MISS: transcript analysis (key: {key[:20]}...)")
        return None
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern (Redis only)."""
        if not self._redis_client:
            self.logger.warning("Pattern invalidation only supported with Redis")
            return 0
        
        try:
            keys = self._redis_client.keys(pattern)
            if keys:
                deleted = self._redis_client.delete(*keys)
                self.logger.info(f"Invalidated {deleted} cache entries matching pattern: {pattern}")
                return deleted
        except Exception as e:
            self.logger.error(f"Pattern invalidation failed: {e}")
        
        return 0
    
    def clear_all(self) -> bool:
        """Clear all cache data."""
        with self._cache_lock:
            success = True
            
            # Clear Redis
            if self._redis_client:
                try:
                    self._redis_client.flushdb()
                except Exception as e:
                    self.logger.warning(f"Redis clear failed: {e}")
                    success = False
            
            # Clear disk cache
            if self._disk_cache:
                try:
                    self._disk_cache.clear()
                except Exception as e:
                    self.logger.warning(f"Disk cache clear failed: {e}")
                    success = False
            
            # Clear memory cache
            self._memory_cache.clear()
            self._memory_cache_ttl.clear()
            
            self.logger.info("All caches cleared")
            return success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics and status."""
        cache_backends = []
        
        if self._redis_client:
            try:
                info = self._redis_client.info()
                cache_backends.append({
                    'type': 'redis',
                    'status': 'active',
                    'memory_usage': info.get('used_memory_human', 'unknown'),
                    'connected_clients': info.get('connected_clients', 0)
                })
            except:
                cache_backends.append({'type': 'redis', 'status': 'error'})
        
        if self._disk_cache:
            try:
                cache_backends.append({
                    'type': 'disk',
                    'status': 'active',
                    'size': len(self._disk_cache),
                    'volume_path': str(self._disk_cache.directory)
                })
            except:
                cache_backends.append({'type': 'disk', 'status': 'error'})
        
        cache_backends.append({
            'type': 'memory',
            'status': 'active',
            'items': len(self._memory_cache),
            'max_items': self.max_memory_items
        })
        
        hit_rate = 0
        total_operations = self.cache_stats['hits'] + self.cache_stats['misses']
        if total_operations > 0:
            hit_rate = (self.cache_stats['hits'] / total_operations) * 100
        
        return {
            'backends': cache_backends,
            'statistics': self.cache_stats,
            'hit_rate_percent': round(hit_rate, 2),
            'ttl_settings': {
                'default': self.default_ttl,
                'ai_responses': self.ai_cache_ttl,
                'transcript_analysis': self.transcript_cache_ttl,
                'context_processing': self.context_cache_ttl
            }
        }


def cached_ai_response(response_type: str, ttl: Optional[int] = None):
    """Decorator for caching AI responses."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, transcript: str, context: str = "", *args, **kwargs):
            # Get cache service (assume it's available in the service)
            cache_service = getattr(self, '_cache_service', None)
            if not cache_service:
                # No cache available, call function directly
                return func(self, transcript, context, *args, **kwargs)
            
            # Try to get cached response
            cached_response = cache_service.get_ai_response(transcript, context, response_type)
            if cached_response is not None:
                return cached_response
            
            # No cache hit, call function and cache result
            result = func(self, transcript, context, *args, **kwargs)
            cache_service.cache_ai_response(transcript, context, response_type, result)
            
            return result
        return wrapper
    return decorator
