# hwpx_mcp

FastMCP server for parsing and creatively manipulating Korean HWPX (Hangul Word Processor) files. 

## Features
- **Read & List**: Reads `.hwpx` (ZIP) format and extracts XML text contents (`<hp:t>`). Lists all HWPX files in a directory.
- **Advanced Table Manipulation**:
  - `update_hwpx_table_content`: Finds a specific table by index and replaces cell text safely.
  - `modify_hwpx_table_row`: Duplicates the last row to create properly-styled empty rows (`add`) or removes them (`delete`).
  - `delete_hwpx_table` & `copy_hwpx_table`: Remove or clone entire structural table blocks.
- **Image Overwriting**:
  - `replace_hwpx_image`: Replaces standard BinData images dynamically without breaking target HWPX layouts!

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
**Current release: v0.1.0**
- Initial release: v0.0.1
