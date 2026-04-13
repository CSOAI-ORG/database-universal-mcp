# Universal Database MCP Server

> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

Connect AI agents to any SQL database. Query data, explore schemas, insert rows, and export results to CSV. Supports SQLite, PostgreSQL, and MySQL with a single unified interface.

[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/database-universal)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

## Tools

| Tool | Description |
|------|-------------|
| `query_sql` | Execute a SQL query (SQLite, PostgreSQL, MySQL) |
| `list_tables` | List all tables in a database |
| `describe_table` | Describe a table's schema with column details |
| `insert_row` | Insert a single row into a table |
| `export_to_csv` | Execute a SELECT query and export results to CSV |

## Quick Start

```bash
pip install mcp
git clone https://github.com/CSOAI-ORG/database-universal-mcp.git
cd database-universal-mcp
python server.py
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "database-universal": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/database-universal-mcp"
    }
  }
}
```

## Pricing

| Plan | Price | Requests |
|------|-------|----------|
| Free | $0/mo | 30 calls/day, 1000 rows max |
| Pro | $12/mo | Unlimited + connection pooling + batch operations |
| Enterprise | Contact us | Custom + audit logging + VPC support |

[Get on MCPize](https://mcpize.com/mcp/database-universal)

## Part of MEOK AI Labs

This is one of 255+ MCP servers by MEOK AI Labs. Browse all at [meok.ai](https://meok.ai) or [GitHub](https://github.com/CSOAI-ORG).

---
**MEOK AI Labs** | [meok.ai](https://meok.ai) | nicholas@meok.ai | United Kingdom
