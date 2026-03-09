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

### Version 0.1.1 (Hotfix) - Advanced Formatting & Corruption Fixes
- Added features for structurally mutating tables: `modify_hwpx_table_row`, `delete_hwpx_table`, `copy_hwpx_table`
- Discovered and fixed a critical ZIP repacking issue causing HWPX file corruption because of Hancom's strict OCF structure requirement. Uncompressed `mimetype` files are now guaranteed to be the first file in the ZIP archive.
- Corrected internal XML indexing (such as `hp:tbl` `rowCnt` and `hp:cellAddr` `rowAddr`) handling when adding or removing table rows. Previously, added rows duplicated unique identifiers which corrupted the grid data model.
- Prevented automatic XML declaration changes by standardizing how Python's ElementTree reserializes modified node structures, preserving the original schema metadata precisely.

### Resources & Technical Documentation
- [HWPX Format Overview - Hancom Tech](https://tech.hancom.com/hwpxformat/)
- [Parsing HWP - Hancom Tech](https://tech.hancom.com/python-hwp-parsing-1/)
- [Parsing HWPX Part 1 - Hancom Tech](https://tech.hancom.com/python-hwpx-parsing-1/)
- [Parsing HWPX Part 2 - Hancom Tech](https://tech.hancom.com/python-hwpx-parsing-2/)
