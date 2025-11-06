"""
Configuration module for Discogs MCP Server.

Loads environment variables and provides application configuration.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LLM:METADATA
# :hierarchy: [Configuration | EnvironmentLoader]
# :relates-to:
#  - motivated_by: "Application requires Discogs API authentication: Consumer Key & Secret identify application, but user_token (personal access token) is required for authenticated requests per Discogs API requirements (401 errors without it) [PRD-4.2, api_summary-2.1]"
#  - implements: "Environment variable loading using python-dotenv, supports Consumer Key & Secret and user_token authentication with graceful fallback to anonymous mode"
# :contract:
#  - pre: ".env file exists in project root (optional), DISCOGS_CONSUMER_KEY, DISCOGS_CONSUMER_SECRET, and DISCOGS_USER_TOKEN may be set or None"
#  - post: "Returns User-Agent string, Consumer Key & Secret tuple, and user_token string, supports graceful fallback to anonymous mode"
#  - invariant: "User-Agent always returns valid string, Consumer Key & Secret may both be None, user_token may be None, configuration loaded once at module import"
# :complexity: 3
# :decision_cache: "user_token over full OAuth: simpler personal access token from Discogs settings (no OAuth flow needed), sufficient for API search and retrieval operations, recommended by Discogs for personal use [decision-auth-004]"
# LLM:END


# Discogs User-Agent (mandatory for API)
DISCOGS_USER_AGENT: str = "DiscogsMCP/1.0"


def get_discogs_credentials() -> tuple[str | None, str | None]:
    """
    Get Discogs Consumer Key & Secret from environment.

    Returns the Discogs Consumer Key and Secret from DISCOGS_CONSUMER_KEY
    and DISCOGS_CONSUMER_SECRET environment variables.
    Returns (None, None) if not set (anonymous mode).

    Returns:
        Tuple of (consumer_key, consumer_secret) if both set, (None, None) otherwise
    """
    consumer_key = os.getenv("DISCOGS_CONSUMER_KEY")
    consumer_secret = os.getenv("DISCOGS_CONSUMER_SECRET")
    return (consumer_key, consumer_secret)


def get_discogs_user_token() -> str | None:
    """
    Get Discogs personal access token from environment.

    Returns the Discogs personal access token (user_token) from DISCOGS_USER_TOKEN
    environment variable. This token is required for authenticated API requests.
    Returns None if not set.

    Returns:
        User token string if set, None otherwise
    """
    return os.getenv("DISCOGS_USER_TOKEN")


def get_user_agent() -> str:
    """
    Get User-Agent string for Discogs API.

    Returns the configured User-Agent string required by Discogs API.

    Returns:
        User-Agent string
    """
    return DISCOGS_USER_AGENT
