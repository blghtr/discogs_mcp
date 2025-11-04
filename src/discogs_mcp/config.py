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
#  - motivated_by: "Application requires Discogs API Consumer Key & Secret for OAuth
#    authentication (simpler than user token) and User-Agent from environment for rate
#    limit improvements (25→60 req/min) and API compliance per Discogs requirements
#    [PRD-4.2, api_summary-2.1]"
#  - implements: "Environment variable loading using python-dotenv, supports Consumer
#    Key & Secret authentication with graceful fallback to anonymous mode"
# :contract:
#  - pre: ".env file exists in project root (optional), DISCOGS_CONSUMER_KEY and
#    DISCOGS_CONSUMER_SECRET may be set or None"
#  - post: "Returns User-Agent string and optionally Consumer Key & Secret tuple,
#    supports graceful fallback to anonymous mode"
#  - invariant: "User-Agent always returns valid string, Consumer Key & Secret may
#    both be None, configuration loaded once at module import"
# :complexity: 3
# :decision_cache: "Consumer Key & Secret over user token: simpler OAuth app
#  credentials, same rate limits (60 req/min), no need for personal access token
#  generation [decision-auth-003]"
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


def get_user_agent() -> str:
    """
    Get User-Agent string for Discogs API.

    Returns the configured User-Agent string required by Discogs API.

    Returns:
        User-Agent string
    """
    return DISCOGS_USER_AGENT
