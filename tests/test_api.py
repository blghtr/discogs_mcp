"""
Unit tests for Discogs MCP Server tools.

Tests search_releases and get_release_details with mocked API client.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context

# LLM:METADATA
# :hierarchy: [UnitTest | DiscogsMCP | SearchToolTests]
# :covers:
#  - target: "search_releases function"
#  - requirement: "Search releases by multiple criteria, validate inputs, format results per PRD-3.1"
# :scenario: "Various search scenarios: valid search, empty results, validation errors"
# :priority: "P0"
# :complexity: 4
# LLM:END


@pytest.fixture
def mock_ctx():
    """Create mock Context for MCP tools."""
    ctx = MagicMock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.fixture
def mock_release():
    """Create mock Release object with proper structure."""
    # Create mock objects for nested attributes
    mock_artist = MagicMock()
    mock_artist.name = "Nirvana"

    mock_format = MagicMock()
    mock_format.name = "Vinyl"

    mock_label = MagicMock()
    mock_label.name = "DGC Records"
    mock_label.catno = "GED-24425"

    mock_identifier = MagicMock()
    mock_identifier.type = "Barcode"
    mock_identifier.value = "720642442518"

    # Create main release mock
    mock_release = MagicMock()
    mock_release.id = 123456
    mock_release.title = "Nevermind"
    mock_release.artists = [mock_artist]
    mock_release.year = 1991
    mock_release.formats = [mock_format]
    mock_release.labels = [mock_label]
    mock_release.country = "US"
    mock_release.identifiers = [mock_identifier]

    return mock_release


class TestSearchReleases:
    """Test cases for search_releases tool."""

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_search_valid_with_results(
        self, mock_api_client, mock_ctx, mock_release
    ):
        """Test valid search that returns results."""
        # Import here to avoid circular import issues
        from discogs_mcp.main import search_releases

        # Setup mock
        mock_api_client.search = AsyncMock(return_value=[mock_release])

        # Execute - extract function from FunctionTool wrapper
        result = await search_releases.fn(mock_ctx, artist="Nirvana", year=1991)

        # Verify
        assert len(result) == 1
        assert result[0]["id"] == 123456
        assert result[0]["title"] == "Nevermind"
        assert result[0]["artist"] == "Nirvana"
        assert result[0]["year"] == 1991
        assert result[0]["format"] == "Vinyl"
        assert result[0]["label"] == "DGC Records"
        assert result[0]["country"] == "US"
        assert result[0]["barcode"] == "720642442518"
        assert result[0]["catno"] == "GED-24425"

        mock_ctx.info.assert_awaited()
        mock_api_client.search.assert_awaited_once_with(artist="Nirvana", year=1991)

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_search_valid_no_results(self, mock_api_client, mock_ctx):
        """Test valid search with no results."""
        from discogs_mcp.main import search_releases

        # Setup mock
        mock_api_client.search = AsyncMock(return_value=[])

        # Execute - extract function from FunctionTool wrapper
        result = await search_releases.fn(mock_ctx, artist="UnknownArtist")

        # Verify
        assert result == []
        mock_ctx.info.assert_awaited()

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_search_no_parameters_error(self, mock_api_client, mock_ctx):
        """Test search with no parameters returns error."""
        from discogs_mcp.main import search_releases

        # Execute
        result = await search_releases.fn(mock_ctx)

        # Verify
        assert result == []
        mock_ctx.error.assert_awaited_once_with(
            "At least one search parameter must be provided."
        )
        # API client should not be called for validation errors
        assert not mock_api_client.search.called

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_search_404_handling(self, mock_api_client, mock_ctx):
        """Test search handles 404 gracefully."""
        from discogs_mcp.main import search_releases

        # Setup mock
        http_error = Exception()
        http_error.status_code = 404
        mock_api_client.search = AsyncMock(side_effect=http_error)

        # Execute
        result = await search_releases.fn(mock_ctx, artist="Test")

        # Verify
        assert result == []
        mock_ctx.info.assert_awaited()

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_search_api_error_handling(self, mock_api_client, mock_ctx):
        """Test search handles API errors gracefully."""
        from discogs_mcp.main import search_releases

        # Setup mock
        mock_api_client.search = AsyncMock(side_effect=Exception("API Error"))

        # Execute
        result = await search_releases.fn(mock_ctx, artist="Test")

        # Verify
        assert result == []
        mock_ctx.error.assert_awaited()

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_search_all_parameters(self, mock_api_client, mock_ctx, mock_release):
        """Test search with all parameters."""
        from discogs_mcp.main import search_releases

        # Setup mock
        mock_api_client.search = AsyncMock(return_value=[mock_release])

        # Execute with all parameters
        result = await search_releases.fn(
            mock_ctx,
            title="Nevermind",
            artist="Nirvana",
            barcode="720642442518",
            label="DGC Records",
            catno="GED-24425",
            year=1991,
            format="Vinyl",
            country="US",
        )

        # Verify
        assert len(result) == 1
        mock_api_client.search.assert_awaited_once_with(
            title="Nevermind",
            artist="Nirvana",
            barcode="720642442518",
            label="DGC Records",
            catno="GED-24425",
            year=1991,
            format="Vinyl",
            country="US",
        )


# LLM:METADATA
# :hierarchy: [UnitTest | DiscogsMCP | DetailsToolTests]
# :covers:
#  - target: "get_release_details function"
#  - requirement: "Retrieve release by ID, validate inputs, format complete details per PRD-3.2"
# :scenario: "Various detail scenarios: valid retrieval, 404 errors, validation errors"
# :priority: "P0"
# :complexity: 5
# LLM:END


@pytest.fixture
def mock_release_full():
    """Create mock Release object with all detail fields."""
    # Mock track objects
    mock_track1 = MagicMock()
    mock_track1.position = "A1"
    mock_track1.title = "Smells Like Teen Spirit"
    mock_track1.duration = "5:01"

    mock_track2 = MagicMock()
    mock_track2.position = "A2"
    mock_track2.title = "In Bloom"
    mock_track2.duration = "4:14"

    # Mock images
    mock_image = {"uri": "https://example.com/cover.jpg"}

    # Create release mock
    mock_release = MagicMock()
    # Create proper mock objects for nested attributes
    mock_artist_full = MagicMock()
    mock_artist_full.name = "Nirvana"

    mock_format_full = MagicMock()
    mock_format_full.name = "Vinyl"

    mock_label_full = MagicMock()
    mock_label_full.name = "DGC Records"
    mock_label_full.catno = "GED-24425"

    mock_identifier_full = MagicMock()
    mock_identifier_full.type = "Barcode"
    mock_identifier_full.value = "720642442518"

    # Setup main release mock
    mock_release.id = 789012
    mock_release.title = "Nevermind"
    mock_release.artists = [mock_artist_full]
    mock_release.year = 1991
    mock_release.formats = [mock_format_full]
    mock_release.labels = [mock_label_full]
    mock_release.country = "US"
    mock_release.identifiers = [mock_identifier_full]
    mock_release.genres = ["Rock", "Alternative"]
    mock_release.styles = ["Grunge", "Alternative Rock"]
    mock_release.tracklist = [mock_track1, mock_track2]
    mock_release.thumb = "https://example.com/thumb.jpg"
    mock_release.images = [mock_image]
    mock_release.uri = "https://www.discogs.com/release/789012"

    return mock_release


class TestGetReleaseDetails:
    """Test cases for get_release_details tool."""

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_get_details_valid(
        self, mock_api_client, mock_ctx, mock_release_full
    ):
        """Test valid release details retrieval."""
        from discogs_mcp.main import get_release_details

        # Setup mock
        mock_api_client.get_release = AsyncMock(return_value=mock_release_full)

        # Execute
        result = await get_release_details.fn(mock_ctx, release_id=789012)

        # Verify
        assert result is not None
        assert result["id"] == 789012
        assert result["title"] == "Nevermind"
        assert result["artist"] == "Nirvana"
        assert result["year"] == 1991
        assert result["format"] == "Vinyl"
        assert result["label"] == "DGC Records"
        assert result["country"] == "US"
        assert result["barcode"] == "720642442518"
        assert result["catno"] == "GED-24425"
        assert result["genres"] == ["Rock", "Alternative"]
        assert result["styles"] == ["Grunge", "Alternative Rock"]
        assert len(result["tracklist"]) == 2
        assert result["tracklist"][0]["title"] == "Smells Like Teen Spirit"
        assert result["tracklist"][0]["duration"] == "5:01"
        assert result["thumb"] == "https://example.com/thumb.jpg"
        assert result["cover_image"] == "https://example.com/cover.jpg"
        assert result["uri"] == "https://www.discogs.com/release/789012"

        mock_ctx.info.assert_awaited()
        mock_api_client.get_release.assert_awaited_once_with(789012)

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_get_details_invalid_id_zero(self, mock_api_client, mock_ctx):
        """Test invalid release_id (zero) returns error."""
        from discogs_mcp.main import get_release_details

        # Execute
        result = await get_release_details.fn(mock_ctx, release_id=0)

        # Verify
        assert result is None
        mock_ctx.error.assert_awaited_once_with(
            "Release ID must be a positive integer."
        )
        # API client should not be called for validation errors
        assert not mock_api_client.get_release.called

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_get_details_invalid_id_negative(self, mock_api_client, mock_ctx):
        """Test invalid release_id (negative) returns error."""
        from discogs_mcp.main import get_release_details

        # Execute
        result = await get_release_details.fn(mock_ctx, release_id=-1)

        # Verify
        assert result is None
        mock_ctx.error.assert_awaited_once_with(
            "Release ID must be a positive integer."
        )

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_get_details_404_handling(self, mock_api_client, mock_ctx):
        """Test 404 handling for non-existent release."""
        from discogs_mcp.main import get_release_details

        # Setup mock
        mock_api_client.get_release = AsyncMock(
            side_effect=ValueError("Release 999999 not found")
        )

        # Execute
        result = await get_release_details.fn(mock_ctx, release_id=999999)

        # Verify
        assert result is None
        mock_ctx.error.assert_awaited_once_with("Release 999999 not found")

    @pytest.mark.asyncio
    @patch("discogs_mcp.main.api_client")
    async def test_get_details_api_error_handling(self, mock_api_client, mock_ctx):
        """Test API error handling."""
        from discogs_mcp.main import get_release_details

        # Setup mock
        mock_api_client.get_release = AsyncMock(side_effect=Exception("API Error"))

        # Execute
        result = await get_release_details.fn(mock_ctx, release_id=123)

        # Verify
        assert result is None
        mock_ctx.error.assert_awaited()
