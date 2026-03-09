# hwpx_mcp

FastMCP server for parsing Korean HWPX (Hangul Word Processor) files.

## Features
- Reads `.hwpx` (ZIP) format and extracts XML text contents (`<hp:t>`).
- Supports listing `.hwpx` files in directories.

## Installation & Usage

Requires Python 3.10+ and `uv` or `pip`.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage with Antigravity / Claude Desktop (mcp.json)
```json
{
  "mcpServers": {
    "hwpx-parser": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/hwpx_mcp.py"]
    }
  }
}
```

## Version
Initial release: v0.0.1
