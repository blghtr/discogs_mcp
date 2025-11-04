# discogs-mcp

A model context protocol (MCP) for interacting with Discogs

## Installation

Install the package with uv:

```bash
uv sync --dev
```

### Configuration

Create a `.env` file in the project root (optional but recommended):

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your Discogs Consumer Key & Secret:

```env
DISCOGS_CONSUMER_KEY=your_consumer_key_here
DISCOGS_CONSUMER_SECRET=your_consumer_secret_here
```

**Getting your Discogs Consumer Key & Secret:**
1. Go to https://www.discogs.com/settings/developers
2. Create a new application (or use existing one)
3. Copy the Consumer Key and Consumer Secret
4. Add both to your `.env` file

**Note:** Consumer Key & Secret are optional but recommended. Without them, you get 25 requests/minute. With authentication, you get 60 requests/minute.

## Usage

You can run the MCP:

```bash
uv run discogs-mcp
```

Or install globally and run:

```bash
uvx discogs-mcp
```

## Development

### Local Setup

```bash
# Clone the repository
git clone https://github.com/blghtr/discogs_mcp.git
cd discogs_mcp

# Install development dependencies
uv sync --dev

# Set up environment (create .env file)
cp .env.example .env
# Edit .env and add your Discogs Consumer Key & Secret

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install
```

### Testing

Run the test suite:

```bash
uv run pytest
```

### Linting and Formatting

Check code quality:

```bash
# Run Ruff linter
uv run ruff check src/ tests/

# Auto-fix with Ruff
uv run ruff check --fix src/ tests/

# Check Black formatting
uv run black --check src/ tests/

# Format code with Black
uv run black src/ tests/
```

### MCP Tools

This server provides two MCP tools for LLM agents:

1. **`search_releases`**: Search Discogs for vinyl releases by various criteria
   - Parameters: `title`, `artist`, `year`, `format`, `country`, `label`, `catno`, `barcode`
   - At least one parameter must be provided
   - Returns: List of matching releases with basic info

2. **`get_release_details`**: Get detailed information about a specific release
   - Parameters: `release_id` (required)
   - Returns: Full release details including genres, styles, tracklist, images

Both tools use 30-day caching to minimize API calls and improve performance.


## License

MIT
