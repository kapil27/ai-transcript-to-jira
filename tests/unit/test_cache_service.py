"""Tests for the CacheService class."""

import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from src.services.cache_service import CacheService


class TestCacheService:
    """Test cases for CacheService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for disk cache
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock config to use temp directory
        with patch('src.services.cache_service.get_config') as mock_config:
            mock_config.return_value.cache_directory = self.temp_dir
            self.cache_service = CacheService()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clear cache and remove temp directory
        try:
            self.cache_service.clear_all()
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass  # Ignore cleanup errors
    
    def test_cache_service_initialization(self):
        """Test cache service initializes with fallback backends."""
        stats = self.cache_service.get_stats()
        assert 'backends' in stats
        assert len(stats['backends']) >= 1  # At least memory cache
        
        # Memory cache should always be available
        memory_backend = next((b for b in stats['backends'] if b['type'] == 'memory'), None)
        assert memory_backend is not None
        assert memory_backend['status'] == 'active'
    
    def test_basic_cache_operations(self):
        """Test basic get/set/delete operations."""
        # Test set and get
        key = "test_key"
        value = {"test": "data", "number": 42}
        
        success = self.cache_service.set(key, value, ttl=300)
        assert success is True
        
        retrieved_value = self.cache_service.get(key)
        assert retrieved_value == value
        
        # Test delete
        deleted = self.cache_service.delete(key)
        assert deleted is True
        
        # Verify deletion
        retrieved_after_delete = self.cache_service.get(key)
        assert retrieved_after_delete is None
    
    def test_cache_key_generation(self):
        """Test cache key generation for consistent hashing."""
        transcript = "This is a test transcript"
        context = "Test project context"
        
        # Generate keys for same data should be identical
        key1 = self.cache_service._generate_cache_key("test", {"transcript": transcript, "context": context})
        key2 = self.cache_service._generate_cache_key("test", {"transcript": transcript, "context": context})
        assert key1 == key2
        
        # Different data should generate different keys
        key3 = self.cache_service._generate_cache_key("test", {"transcript": "different", "context": context})
        assert key1 != key3
    
    def test_ai_response_caching(self):
        """Test AI response caching functionality."""
        transcript = "Meeting transcript about project planning"
        context = "Software development project"
        response_type = "parse_transcript"
        response_data = [{"summary": "Task 1", "description": "Test task"}]
        
        # Cache AI response
        cache_key = self.cache_service.cache_ai_response(transcript, context, response_type, response_data)
        assert cache_key is not None
        assert cache_key.startswith(f"ai_{response_type}:")
        
        # Retrieve cached response
        cached_response = self.cache_service.get_ai_response(transcript, context, response_type)
        assert cached_response == response_data
        
        # Test cache miss with different data
        no_response = self.cache_service.get_ai_response("different transcript", context, response_type)
        assert no_response is None
    
    def test_transcript_analysis_caching(self):
        """Test transcript analysis caching."""
        transcript = "Meeting about feature development"
        context = "Web application project"
        analysis = {
            "tasks": [{"summary": "Implement feature X"}],
            "qa_items": [{"question": "When is deadline?", "answer": "Next week"}],
            "tasks_count": 1,
            "qa_count": 1
        }
        
        # Cache analysis
        cache_key = self.cache_service.cache_transcript_analysis(transcript, context, analysis)
        assert cache_key is not None
        
        # Retrieve cached analysis
        cached_analysis = self.cache_service.get_transcript_analysis(transcript, context)
        assert cached_analysis == analysis
        
        # Test cache miss
        no_analysis = self.cache_service.get_transcript_analysis("different", context)
        assert no_analysis is None
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        initial_stats = self.cache_service.get_stats()
        initial_hits = initial_stats['statistics']['hits']
        initial_misses = initial_stats['statistics']['misses']
        initial_sets = initial_stats['statistics']['sets']
        
        # Perform cache operations
        key = "stats_test"
        value = "test_value"
        
        # Cache miss
        self.cache_service.get(key)
        
        # Cache set
        self.cache_service.set(key, value)
        
        # Cache hit
        self.cache_service.get(key)
        
        # Check updated statistics
        final_stats = self.cache_service.get_stats()
        assert final_stats['statistics']['hits'] == initial_hits + 1
        assert final_stats['statistics']['misses'] == initial_misses + 1
        assert final_stats['statistics']['sets'] == initial_sets + 1
        
        # Test hit rate calculation
        if final_stats['statistics']['hits'] + final_stats['statistics']['misses'] > 0:
            assert 'hit_rate_percent' in final_stats
            assert 0 <= final_stats['hit_rate_percent'] <= 100
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL and expiration (memory cache)."""
        import time
        
        key = "ttl_test"
        value = "expires_soon"
        short_ttl = 1  # 1 second
        
        # Set with short TTL
        self.cache_service.set(key, value, ttl=short_ttl)
        
        # Should be available immediately
        retrieved = self.cache_service.get(key)
        assert retrieved == value
        
        # Wait for expiration (add small buffer)
        time.sleep(1.1)
        
        # Should be expired
        expired_value = self.cache_service.get(key)
        assert expired_value is None
    
    def test_memory_cache_cleanup(self):
        """Test memory cache cleanup when limit is reached."""
        # Fill memory cache beyond limit
        original_limit = self.cache_service.max_memory_items
        self.cache_service.max_memory_items = 5  # Set low limit for testing
        
        # Add more items than the limit
        for i in range(10):
            self.cache_service.set(f"key_{i}", f"value_{i}")
        
        # Force cleanup
        self.cache_service._cleanup_memory_cache()
        
        # Memory cache should be within limits
        assert len(self.cache_service._memory_cache) <= self.cache_service.max_memory_items
        
        # Restore original limit
        self.cache_service.max_memory_items = original_limit
    
    def test_clear_all_caches(self):
        """Test clearing all cache data."""
        # Add test data
        self.cache_service.set("test1", "value1")
        self.cache_service.set("test2", "value2")
        
        # Verify data exists
        assert self.cache_service.get("test1") == "value1"
        assert self.cache_service.get("test2") == "value2"
        
        # Clear all caches
        success = self.cache_service.clear_all()
        assert success is True
        
        # Verify data is cleared
        assert self.cache_service.get("test1") is None
        assert self.cache_service.get("test2") is None
    
    def test_cache_with_complex_data_types(self):
        """Test caching with various data types."""
        test_cases = [
            ("string", "simple string"),
            ("list", [1, 2, 3, "mixed", {"nested": "dict"}]),
            ("dict", {"key": "value", "number": 42, "nested": {"level": 2}}),
            ("bool", True),
            ("none", None),
            ("float", 3.14159)
        ]
        
        for key, value in test_cases:
            self.cache_service.set(key, value)
            retrieved = self.cache_service.get(key)
            assert retrieved == value, f"Failed for data type: {key}"
    
    @patch('src.services.cache_service.REDIS_AVAILABLE', False)
    @patch('src.services.cache_service.DISKCACHE_AVAILABLE', False)
    def test_memory_only_fallback(self):
        """Test fallback to memory-only cache when other backends unavailable."""
        with patch('src.services.cache_service.get_config'):
            cache_service = CacheService()
            
            # Should work with memory cache only
            cache_service.set("memory_test", "memory_value")
            assert cache_service.get("memory_test") == "memory_value"
            
            stats = cache_service.get_stats()
            # Should only have memory backend
            memory_backends = [b for b in stats['backends'] if b['type'] == 'memory']
            assert len(memory_backends) == 1
    
    def test_cache_decorator_simulation(self):
        """Test the caching decorator concept."""
        # Simulate the cached_ai_response decorator behavior
        transcript = "Test transcript for decorator"
        context = "Test context"
        response_type = "test_extraction"
        expected_response = [{"task": "Test task from decorator"}]
        
        # First call - cache miss, should call function
        cache_key = f"ai_{response_type}"
        cached = self.cache_service.get_ai_response(transcript, context, response_type)
        assert cached is None  # Cache miss
        
        # Simulate function execution and caching
        self.cache_service.cache_ai_response(transcript, context, response_type, expected_response)
        
        # Second call - cache hit, should return cached value
        cached = self.cache_service.get_ai_response(transcript, context, response_type)
        assert cached == expected_response  # Cache hit
