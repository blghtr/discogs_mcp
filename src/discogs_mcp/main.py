"""
Discogs MCP Server main module.

Provides MCP tools for searching and retrieving Discogs release information.
"""

import logging
from typing import Any

import discogs_client.exceptions
from fastmcp import Context, FastMCP

from discogs_mcp.api_client import DiscogsAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# LLM:METADATA
# :hierarchy: [DiscogsMCP | ServerModule]
# :relates-to:
#  - motivated_by: "MCP server providing LLM agents access to Discogs API for vinyl record identification and information retrieval as part of record recognition system [PRD-1.1]"
#  - implements: "Two MCP tools: search_releases and get_release_details for searching by multiple criteria and retrieving full release details [PRD-3]"
#  - uses: ["DiscogsAPIClient: async wrapper for Discogs API with caching and error handling"]
#  - enables: ["LLM agents: search and identify vinyl records from photos using Discogs database"]
# :contract:
#  - pre: "DiscogsAPIClient initialized, FastMCP server created"
#  - post: "Two tools registered and server ready to accept requests via HTTP transport"
#  - invariant: "Tools execute asynchronously without blocking, respect rate limits, return formatted data per PRD specifications"
# :complexity: 8
# LLM:END


# Initialize API client
api_client = DiscogsAPIClient()

# Create FastMCP server instance
mcp = FastMCP("Discogs MCP Server")


def _extract_format_names(formats: list | None) -> str | None:
    """
    Extract format names from release formats.

    Handles both object and dict formats from Discogs API.

    Args:
        formats: List of format objects or dicts

    Returns:
        Comma-separated string of format names or None
    """
    if not formats:
        return None

    format_names = []
    for f in formats:
        if isinstance(f, dict):
            # Handle dict format (e.g., {"name": "Vinyl", "qty": "1"})
            name = f.get("name") or f.get("format_name")
            if name:
                format_names.append(name)
        elif hasattr(f, "name"):
            # Handle object format
            format_names.append(f.name)
        elif isinstance(f, str):
            # Handle string format
            format_names.append(f)

    return ", ".join(format_names) if format_names else None


# LLM:METADATA
# :hierarchy: [DiscogsMCP | SearchTool]
# :relates-to:
#  - motivated_by: "LLM agent needs to search Discogs by multiple criteria extracted from vinyl record photos (title, artist, barcode, catno, year, format, country, label) to identify releases [PRD-3.1]"
#  - implements: "Discogs search with validation, async execution, result formatting, and proper error handling per PRD error table"
#  - uses: [
#      "api_client.search: async search with caching and thread pool execution",
#      "ctx.info: user-facing progress logging",
#      "ctx.error: user-facing error messages"
#  ]
# :contract:
#  - pre: "At least one search parameter is non-None and valid"
#  - post: "Returns list of formatted release dictionaries or empty list, logs errors when validation fails"
#  - invariant: "Non-blocking execution, deterministic results, always returns (even if empty), error messages logged to ctx"
# :complexity: 7
# LLM:END


@mcp.tool()
async def search_releases(
    ctx: Context,
    title: str | None = None,
    artist: str | None = None,
    barcode: str | None = None,
    label: str | None = None,
    catno: str | None = None,
    year: int | None = None,
    format: str | None = None,
    country: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search for vinyl releases on Discogs.

    Searches the Discogs database for releases matching the provided criteria.
    At least one search parameter must be provided.

    Args:
        title: Release title
        artist: Artist name
        barcode: Barcode number
        label: Record label name
        catno: Catalog number
        year: Release year
        format: Format (e.g., 'Vinyl', 'CD', 'Cassette')
        country: Country of release (country code)

    Returns:
        List of matching releases with basic information (id, title, artist,
        year, format, label, country, barcode, catno)

    Example:
        >>> search_releases(artist="Nirvana", year=1991, format="Vinyl")
        [{"id": 123, "title": "Nevermind", "artist": "Nirvana", ...}]
    """
    # Validation: at least one parameter required
    if not any([title, artist, barcode, label, catno, year, format, country]):
        await ctx.error("At least one search parameter must be provided.")
        return []

    # Prepare search parameters
    search_params = {
        k: v
        for k, v in {
            "title": title,
            "artist": artist,
            "barcode": barcode,
            "label": label,
            "catno": catno,
            "year": year,
            "format": format,
            "country": country,
        }.items()
        if v is not None
    }

    logger.info(f"Search initiated: {search_params}")
    await ctx.info(f"Searching Discogs with {len(search_params)} criteria")

    try:
        # Execute search
        releases = await api_client.search(**search_params)

        # Format results
        formatted_results = []
        for release in releases:
            # Extract basic fields
            result = {
                "id": release.id,
                "title": release.title,
                "artist": (
                    ", ".join([a.name for a in release.artists])
                    if release.artists
                    else None
                ),
                "year": release.year,
                "format": _extract_format_names(release.formats),
                "label": (
                    ", ".join([label.name for label in release.labels])
                    if release.labels
                    else None
                ),
                "country": release.country,
            }

            # Extract barcode from identifiers
            barcode_list = []
            if hasattr(release, "identifiers"):
                for identifier in release.identifiers:
                    if identifier.type == "Barcode":
                        barcode_list.append(identifier.value)
            if (
                not barcode_list
                and hasattr(release, "data")
                and release.data.get("barcode")
            ):
                barcode_list.append(release.data["barcode"])
            result["barcode"] = ", ".join(barcode_list) if barcode_list else None

            # Extract catalog numbers
            catno_list = []
            if release.labels:
                for label in release.labels:
                    if hasattr(label, "catno") and label.catno:
                        catno_list.append(label.catno)
            result["catno"] = ", ".join(catno_list) if catno_list else None

            formatted_results.append(result)

        logger.info(f"Search completed: {len(formatted_results)} results")
        await ctx.info(f"Found {len(formatted_results)} matching releases")

        return formatted_results

    except discogs_client.exceptions.HTTPError as e:
        # Handle HTTP errors gracefully
        if e.status_code == 404:
            # No results found
            logger.info("Search returned no results")
            await ctx.info("No releases found matching criteria")
            return []
        else:
            # Other HTTP errors
            error_msg = f"Discogs API error ({e.status_code}): {str(e)}"
            logger.error(error_msg)
            await ctx.error(error_msg)
            return []

    except discogs_client.exceptions.DiscogsAPIError as e:
        # Handle API errors (rate limits, etc.)
        error_msg = f"Discogs API error: {str(e)}"
        logger.error(error_msg)
        await ctx.error("Discogs API error. Please retry in a moment.")
        return []

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await ctx.error("An error occurred while searching. Please try again.")
        return []


# LLM:METADATA
# :hierarchy: [DiscogsMCP | DetailsTool]
# :relates-to:
#  - motivated_by: "After identifying a release via search, LLM agent needs full details including genres, styles, tracklist, and cover images for comprehensive record identification [PRD-3.2]"
#  - implements: "Discogs release detail retrieval with validation, async execution, comprehensive data extraction, and proper error handling per PRD error table"
#  - uses: [
#      "api_client.get_release: async retrieval with caching and thread pool execution",
#      "ctx.info: user-facing progress logging",
#      "ctx.error: user-facing error messages"
#  ]
# :contract:
#  - pre: "release_id is positive integer"
#  - post: "Returns formatted release dictionary with all fields or None if not found, logs errors when validation fails"
#  - invariant: "Non-blocking execution, deterministic for same ID, always returns formatted dict or None, error messages logged to ctx"
# :complexity: 7
# LLM:END


@mcp.tool()
async def get_release_details(ctx: Context, release_id: int) -> dict[str, Any] | None:
    """
    Get detailed information about a specific Discogs release.

    Retrieves complete information for a release including genres, styles,
    tracklist, and cover images.

    Args:
        release_id: Discogs release ID (positive integer)

    Returns:
        Dictionary with full release details including:
        - Basic fields: id, title, artist, year, format, label, country, barcode, catno
        - Additional fields: genres, styles, tracklist, thumb, cover_image, uri

    Example:
        >>> get_release_details(release_id=1293022)
        {"id": 1293022, "title": "Nevermind", "genres": ["Rock"], ...}

    Raises:
        ValueError: If release_id is invalid
    """
    # Validation: release_id must be positive
    if not release_id or release_id <= 0:
        error_msg = "Release ID must be a positive integer."
        logger.warning(f"Invalid release_id: {release_id}")
        await ctx.error(error_msg)
        return None

    logger.info(f"Details retrieval initiated: release_id={release_id}")
    await ctx.info(f"Retrieving details for release {release_id}")

    try:
        # Execute retrieval
        release = await api_client.get_release(release_id)

        # Format result
        result = {
            # Basic fields
            "id": release.id,
            "title": release.title,
            "artist": (
                ", ".join([a.name for a in release.artists])
                if release.artists
                else None
            ),
            "year": release.year,
            "format": _extract_format_names(release.formats),
            "label": (
                ", ".join([label.name for label in release.labels])
                if release.labels
                else None
            ),
            "country": release.country,
        }

        # Extract barcode
        barcode_list = []
        if hasattr(release, "identifiers"):
            for identifier in release.identifiers:
                if identifier.type == "Barcode":
                    barcode_list.append(identifier.value)
        if (
            not barcode_list
            and hasattr(release, "data")
            and release.data.get("barcode")
        ):
            barcode_list.append(release.data["barcode"])
        result["barcode"] = ", ".join(barcode_list) if barcode_list else None

        # Extract catalog numbers
        catno_list = []
        if release.labels:
            for label in release.labels:
                if hasattr(label, "catno") and label.catno:
                    catno_list.append(label.catno)
        result["catno"] = ", ".join(catno_list) if catno_list else None

        # Additional fields
        result["genres"] = release.genres if hasattr(release, "genres") else []
        result["styles"] = release.styles if hasattr(release, "styles") else []

        # Tracklist
        tracklist = []
        if hasattr(release, "tracklist") and release.tracklist:
            for track in release.tracklist:
                tracklist.append(
                    {
                        "position": (
                            track.position if hasattr(track, "position") else None
                        ),
                        "title": track.title if hasattr(track, "title") else None,
                        "duration": (
                            track.duration if hasattr(track, "duration") else None
                        ),
                    }
                )
        result["tracklist"] = tracklist

        # Images
        result["thumb"] = release.thumb if hasattr(release, "thumb") else None

        cover_image = None
        if hasattr(release, "images") and release.images:
            cover_image = release.images[0].get("uri") if release.images[0] else None
        result["cover_image"] = cover_image

        result["uri"] = release.uri if hasattr(release, "uri") else None

        logger.info(f"Details retrieval completed: {release.title}")
        await ctx.info(f"Successfully retrieved details for '{release.title}'")

        return result

    except ValueError as e:
        # Release not found (404)
        error_msg = str(e)
        logger.warning(error_msg)
        await ctx.error(error_msg)
        return None

    except discogs_client.exceptions.DiscogsAPIError as e:
        # API errors
        error_msg = f"Discogs API error: {str(e)}"
        logger.error(error_msg)
        await ctx.error("Discogs API error. Please retry in a moment.")
        return None

    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error retrieving release {release_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await ctx.error(
            "An error occurred while retrieving release details. Please try again."
        )
        return None


def main() -> None:
    """Main entry point for the application."""
    logger.info("Starting Discogs MCP Server")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
