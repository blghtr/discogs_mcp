"""
Caching module for Discogs MCP Server.

Provides TTL-based in-memory caching for API responses.
"""

import logging
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# LLM:METADATA
# :hierarchy: [Caching | TTLCacheManager]
# :relates-to:
#  - motivated_by: "Reduce API load and improve response time by caching Discogs API responses for 30 days, critical for staying within rate limits (60 req/min) during repeated searches [PRD-4.1, api_summary-3.3]"
#  - implements: "In-memory TTL cache using cachetools with 30-day expiration, supports max 1024 entries for LRU eviction"
# :contract:
#  - pre: "Cache initialized with maxsize and ttl constants"
#  - post: "Returns TTLCache instance ready for decorator-based caching of API responses"
#  - invariant: "Cache persists for 30 days per entry, automatically evicts oldest entries when maxsize exceeded, thread-safe for asyncio usage"
# :complexity: 2
# LLM:END


# Global cache configuration
CACHE_MAXSIZE: int = 1024
CACHE_TTL_SECONDS: int = 30 * 24 * 60 * 60  # 30 days in seconds


# Create global TTL cache instance
api_cache: TTLCache[str, Any] = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL_SECONDS)

logger.info(
    f"Initialized API cache: maxsize={CACHE_MAXSIZE}, "
    f"ttl={CACHE_TTL_SECONDS} seconds ({CACHE_TTL_SECONDS // (24*60*60)} days)"
)
