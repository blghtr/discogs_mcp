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
#  - motivated_by: "Application requires Discogs API authentication token and User-Agent from environment for rate limit improvements (25→60 req/min) and API compliance per Discogs requirements [PRD-4.2, api_summary-2.1]"
#  - implements: "Environment variable loading using python-dotenv, supports both authenticated and anonymous API access modes"
# :contract:
#  - pre: ".env file exists in project root (optional), DISCOGS_USER_TOKEN may be set or None"
#  - post: "Returns User-Agent string and optionally authenticated token, supports graceful fallback to anonymous mode"
#  - invariant: "User-Agent always returns valid string, token may be None, configuration loaded once at module import"
# :complexity: 3
# LLM:END


# Discogs User-Agent (mandatory for API)
DISCOGS_USER_AGENT: str = "DiscogsMCP/1.0"


def get_discogs_token() -> str | None:
    """
    Get Discogs user token from environment.

    Returns the Discogs user token from DISCOGS_USER_TOKEN environment
    variable. Returns None if not set (anonymous mode).

    Returns:
        Discogs user token string if set, None otherwise
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
