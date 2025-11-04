"""
Discogs API client wrapper with async support.

Provides async wrapper around synchronous discogs_client library
to prevent blocking the FastMCP event loop.
"""

import asyncio
import hashlib
import json
import logging
from typing import Any

import discogs_client
from cachetools import cached
from discogs_client.exceptions import DiscogsAPIError, HTTPError

from discogs_mcp.cache import api_cache
from discogs_mcp.config import get_discogs_credentials, get_user_agent

logger = logging.getLogger(__name__)

# LLM:METADATA
# :hierarchy: [DiscogsAPI | APIClient]
# :relates-to:
#  - motivated_by: "Synchronous discogs_client library must be wrapped in async functions using asyncio.to_thread to prevent blocking FastMCP event loop when making network calls to Discogs API [api_summary-3.1]"
#  - implements: "Async wrapper with thread pool execution, caching integration via @cached decorator on sync methods, proper error handling for HTTP errors and rate limits"
#  - uses: [
#      "discogs_client.Client: official Python client for Discogs API with synchronous network calls",
#      "asyncio.to_thread: offloads blocking calls to thread pool maintaining async semantics",
#      "cachetools.@cached: applies 30-day TTL caching to sync wrapper methods"
#  ]
#  - enables: [
#      "search_releases: async search functionality with caching, supports all PRD search parameters",
#      "get_release_details: async release detail retrieval with caching, handles 404 errors"
#  ]
# :contract:
#  - pre: "Discogs client initialized with User-Agent, Consumer Key & Secret may be None for anonymous mode"
#  - post: "Async methods return Release objects or raise exceptions, sync methods return objects suitable for caching"
#  - invariant: "Non-blocking event loop, deterministic results for same inputs, respects Discogs rate limits (60 req/min with auth, 25 without)"
# :complexity: 7
# :decision_cache: "asyncio.to_thread over httpx rewrite: preserves discogs_client functionality including built-in rate limiting and error handling, simpler than maintaining custom HTTP client [decision-async-wrapper-001]; Consumer Key & Secret over user token: simpler OAuth app credentials, same rate limits (60 req/min), no need for personal access token generation [decision-auth-003]"
# LLM:END


class DiscogsAPIClient:
    """
    Async wrapper for Discogs API client.

    Provides async methods that execute blocking discogs_client calls
    in a thread pool to prevent event loop blocking.
    """

    def __init__(self) -> None:
        """
        Initialize Discogs API client with User-Agent and optional Consumer Key & Secret.

        Creates discogs_client instance with configured User-Agent.
        Consumer Key & Secret are optional for anonymous access (lower rate limits).
        """
        user_agent = get_user_agent()
        consumer_key, consumer_secret = get_discogs_credentials()

        if consumer_key and consumer_secret:
            self.client = discogs_client.Client(
                user_agent,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
            )
            logger.info("Discogs client initialized with Consumer Key & Secret (60 req/min)")
        else:
            self.client = discogs_client.Client(user_agent)
            logger.info("Discogs client initialized anonymously (25 req/min)")

    def _create_search_cache_key(self, **kwargs: Any) -> str:
        """
        Create deterministic cache key for search parameters.

        Generates hash from sorted parameter dictionary, excluding None values.
        Ensures same parameters always produce same key.

        Args:
            **kwargs: Search parameters (filtered by _search_sync)

        Returns:
            Cache key string (hex digest of hash)
        """
        # Remove None values and sort for determinism
        params = {k: v for k, v in kwargs.items() if v is not None}
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        cache_key = hashlib.sha256(sorted_params.encode()).hexdigest()
        return f"search_{cache_key}"

    @cached(
        api_cache, key=lambda self, **kwargs: self._create_search_cache_key(**kwargs)
    )
    def _search_sync(self, **kwargs: Any) -> list[Any]:
        """
        Synchronous search wrapper with caching.

        Executes discogs_client search, extracts first page of results,
        and returns list suitable for caching. Must be called from
        thread pool (via asyncio.to_thread).

        Args:
            **kwargs: Search parameters (title, artist, year, etc.)

        Returns:
            List of Release objects from first page

        Raises:
            HTTPError: API request failed
            DiscogsAPIError: Rate limit or other API error
        """
        # Map title parameter to release_title for discogs_client
        search_params = dict(kwargs)
        if "title" in search_params:
            search_params["release_title"] = search_params.pop("title")

        # Always search for releases specifically
        search_params["type"] = "release"

        logger.debug(f"Searching Discogs: {search_params}")

        # Execute search
        results = self.client.search(**search_params)

        # Extract first page (blocking operation)
        first_page = [r for r in results.page(0)]

        logger.info(f"Search returned {len(first_page)} results")

        return first_page

    async def search(self, **kwargs: Any) -> list[Any]:
        """
        Async search for Discogs releases.

        Searches Discogs API with provided criteria, returns first page
        of results. Executes blocking call in thread pool to prevent
        event loop blocking.

        Args:
            **kwargs: Search parameters
                - title: Release title
                - artist: Artist name
                - year: Release year
                - format: Format (e.g., 'Vinyl', 'CD')
                - country: Country code
                - label: Label name
                - catno: Catalog number
                - barcode: Barcode

        Returns:
            List of Release objects from first page

        Raises:
            HTTPError: API request failed
            DiscogsAPIError: Rate limit or other API error
        """
        logger.info(f"Async search initiated with params: {kwargs}")

        try:
            results = await asyncio.to_thread(self._search_sync, **kwargs)
            logger.debug(f"Search completed: {len(results)} results")
            return results

        except HTTPError as e:
            logger.error(f"HTTP error during search: {e}")
            if e.status_code == 404:
                # No results found, return empty list
                return []
            raise

        except DiscogsAPIError as e:
            logger.error(f"Discogs API error during search: {e}")
            # Rate limit (429) or other API errors
            raise

    @cached(api_cache, key=lambda self, release_id: f"release_{release_id}")
    def _get_release_sync(self, release_id: int) -> Any:
        """
        Synchronous release retrieval wrapper with caching.

        Executes discogs_client release retrieval by ID.
        Must be called from thread pool (via asyncio.to_thread).

        Args:
            release_id: Discogs release ID

        Returns:
            Release object with full details

        Raises:
            HTTPError: Release not found or API error
            DiscogsAPIError: Rate limit or other API error
        """
        logger.debug(f"Retrieving release {release_id}")

        release = self.client.release(release_id)

        logger.info(f"Successfully retrieved release {release_id}: {release.title}")

        return release

    async def get_release(self, release_id: int) -> Any:
        """
        Async get Discogs release by ID.

        Retrieves full release details from Discogs API.
        Executes blocking call in thread pool to prevent event loop blocking.

        Args:
            release_id: Discogs release ID

        Returns:
            Release object with full details including tracklist, images, etc.

        Raises:
            HTTPError: Release not found (404) or other API error
            DiscogsAPIError: Rate limit or other API error
        """
        logger.info(f"Async get release initiated: release_id={release_id}")

        try:
            release = await asyncio.to_thread(self._get_release_sync, release_id)
            logger.debug(f"Release retrieval completed: {release.title}")
            return release

        except HTTPError as e:
            logger.error(f"HTTP error retrieving release {release_id}: {e}")
            if e.status_code == 404:
                raise ValueError(f"Release {release_id} not found")
            raise

        except DiscogsAPIError as e:
            logger.error(f"Discogs API error retrieving release {release_id}: {e}")
            raise
