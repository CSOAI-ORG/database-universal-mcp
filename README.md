<div align="center">

# Database Universal MCP

**MCP server for database universal mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-database-universal-mcp)](https://pypi.org/project/meok-database-universal-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Database Universal MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `query_sql` | Execute a SQL query against a database. Supports SQLite, PostgreSQL, and MySQL. |
| `list_tables` | List all tables in a database. |
| `describe_table` | Describe a table's schema: column names, types, nullability, defaults, |
| `insert_row` | Insert a single row into a table. Column names and values are passed |
| `export_to_csv` | Execute a SELECT query and export results to a CSV file. |

## Installation

```bash
pip install meok-database-universal-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "database-universal-mcp": {
      "command": "python",
      "args": ["-m", "meok_database_universal_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
