# Universal Database MCP Server
**By MEOK AI Labs** | [meok.ai](https://meok.ai)

Connect AI agents to any SQL database. Query data, explore schemas, insert rows, and export results to CSV. Supports SQLite (built-in), PostgreSQL, and MySQL with a single unified interface.

## Tools

| Tool | Description |
|------|-------------|
| `query_sql` | Execute any SQL query with safety validation |
| `list_tables` | List all tables in a database |
| `describe_table` | Get column names, types, nullability, row count |
| `insert_row` | Insert a row using a simple key-value dictionary |
| `export_to_csv` | Run a SELECT and save results as CSV |

## Installation

```bash
# Core (SQLite support included)
pip install mcp

# PostgreSQL support
pip install psycopg2-binary

# MySQL support
pip install mysql-connector-python
```

## Usage

### Run the server

```bash
python server.py
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "database": {
      "command": "python",
      "args": ["/path/to/database-universal-mcp/server.py"]
    }
  }
}
```

### Connection string formats

| Database | Format |
|----------|--------|
| SQLite (file) | `sqlite:///path/to/db.sqlite` or just `/path/to/file.db` |
| PostgreSQL | `postgresql://user:pass@localhost:5432/mydb` |
| MySQL | `mysql://user:pass@localhost:3306/mydb` |

### Example calls

**List tables in a SQLite database:**
```
Tool: list_tables
Input: {"connection_string": "/Users/me/data/app.db"}
Output: {"tables": ["users", "orders", "products"], "count": 3, "db_type": "sqlite"}
```

**Describe a table:**
```
Tool: describe_table
Input: {"connection_string": "/Users/me/data/app.db", "table_name": "users"}
Output: {"columns": [{"name": "id", "type": "INTEGER", "primary_key": true}, {"name": "email", "type": "TEXT", "nullable": false}], "row_count": 1523}
```

**Query data:**
```
Tool: query_sql
Input: {"connection_string": "postgresql://admin:secret@localhost/myapp", "sql": "SELECT name, email FROM users WHERE created_at > '2026-01-01' LIMIT 10"}
Output: {"columns": ["name", "email"], "rows": [{"name": "Alice", "email": "alice@example.com"}, ...], "row_count": 10}
```

**Insert a row:**
```
Tool: insert_row
Input: {"connection_string": "/tmp/test.db", "table_name": "notes", "data": {"title": "Meeting notes", "body": "Discussed Q2 roadmap", "created_at": "2026-04-13"}}
Output: {"message": "Inserted 1 row into notes"}
```

**Export to CSV:**
```
Tool: export_to_csv
Input: {"connection_string": "/Users/me/data/app.db", "sql": "SELECT * FROM orders WHERE total > 100"}
Output: {"output": "/tmp/export_20260413_143022.csv", "rows_exported": 47}
```

## Safety

- **Dangerous queries blocked**: DROP TABLE, TRUNCATE, DELETE without WHERE, GRANT/REVOKE are rejected
- **Write guard**: INSERT/UPDATE/DELETE require explicit `allow_write=True`
- **Row limit**: Free tier returns max 1000 rows per query
- **No credentials stored**: Connection strings are used per-call, never persisted

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 30 calls/day, 1000 rows max | $0 |
| Pro | Unlimited + connection pooling + batch operations | $12/mo |
| Enterprise | Custom + audit logging + VPC support | Contact us |

## License

MIT
