#!/usr/bin/env python3
"""
Universal Database MCP Server
===============================
Connect to SQLite, PostgreSQL, or MySQL databases from AI agents.
Query, explore schema, insert data, and export results to CSV.

By MEOK AI Labs | https://meok.ai

Install: pip install mcp
Optional: pip install psycopg2-binary mysql-connector-python
Run:     python server.py
"""


import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import csv
import io
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 30
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous") -> Optional[str]:
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). Upgrade to Pro: https://mcpize.com/database-universal-mcp/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# Safety: SQL query validation
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS = [
    r"\bDROP\s+(TABLE|DATABASE|INDEX|SCHEMA)\b",
    r"\bTRUNCATE\b",
    r"\bALTER\s+TABLE\b.*\bDROP\b",
    r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)",  # DELETE without WHERE
    r"\bGRANT\b",
    r"\bREVOKE\b",
]


def _validate_query(sql: str, allow_write: bool = False) -> Optional[str]:
    """Validate SQL query for safety. Returns error message if unsafe."""
    sql_upper = sql.strip().upper()

    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return f"Blocked: dangerous SQL pattern detected. Use with caution or upgrade to Pro for unrestricted access."

    if not allow_write:
        write_keywords = ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
        first_word = sql_upper.split()[0] if sql_upper.split() else ""
        if first_word in write_keywords:
            return f"Write operations require explicit allow_write=True for safety."

    return None


# ---------------------------------------------------------------------------
# Database connection helpers
# ---------------------------------------------------------------------------

def _get_connection(connection_string: str):
    """Create a database connection from a connection string.

    Supported formats:
    - sqlite:///path/to/db.sqlite
    - sqlite:path/to/db.sqlite
    - postgresql://user:pass@host:port/dbname
    - mysql://user:pass@host:port/dbname
    - /path/to/file.db (treated as SQLite)
    """
    cs = connection_string.strip()

    # Plain file path -> SQLite
    if cs.startswith("/") or cs.startswith("./") or cs.endswith(".db") or cs.endswith(".sqlite"):
        return sqlite3.connect(cs), "sqlite"

    parsed = urlparse(cs)
    scheme = parsed.scheme.lower()

    if scheme in ("sqlite", "sqlite3"):
        path = parsed.path
        if path.startswith("///"):
            path = path[2:]  # sqlite:///absolute/path
        elif path.startswith("/"):
            path = path  # sqlite:/absolute/path
        return sqlite3.connect(path), "sqlite"

    elif scheme in ("postgresql", "postgres", "psycopg2"):
        try:
            import psycopg2
        except ImportError:
            raise ImportError("Install psycopg2-binary: pip install psycopg2-binary")
        conn = psycopg2.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "",
            dbname=parsed.path.lstrip("/") or "postgres")
        conn.autocommit = True
        return conn, "postgresql"

    elif scheme in ("mysql", "mysql+pymysql"):
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("Install mysql-connector-python: pip install mysql-connector-python")
        conn = mysql.connector.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "root",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or "")
        conn.autocommit = True
        return conn, "mysql"

    else:
        raise ValueError(f"Unsupported database scheme: {scheme}. Use sqlite, postgresql, or mysql.")


def _execute_query(connection_string: str, sql: str, params: Optional[list] = None) -> dict:
    """Execute a SQL query and return results."""
    conn, db_type = _get_connection(connection_string)
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        # Check if query returns rows
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchmany(1000)  # Limit to 1000 rows in free tier
            total_available = len(rows)
            if len(rows) == 1000:
                # Try to get count
                try:
                    remaining = cursor.fetchall()
                    total_available += len(remaining)
                except Exception:
                    pass

            # Convert to list of dicts
            data = []
            for row in rows[:1000]:
                record = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    # Make JSON-serializable
                    if isinstance(val, (datetime)):
                        val = val.isoformat()
                    elif isinstance(val, bytes):
                        val = val.hex()[:100] + "..." if len(val) > 50 else val.hex()
                    elif isinstance(val, memoryview):
                        val = bytes(val).hex()[:100]
                    record[col] = val
                data.append(record)

            return {
                "status": "ok",
                "columns": columns,
                "rows": data,
                "row_count": len(data),
                "total_available": total_available,
                "db_type": db_type,
            }
        else:
            affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            conn.commit()
            return {
                "status": "ok",
                "message": f"Query executed successfully. {affected} row(s) affected.",
                "rows_affected": affected,
                "db_type": db_type,
            }
    finally:
        conn.close()


def _list_tables(connection_string: str) -> dict:
    """List all tables in the database."""
    conn, db_type = _get_connection(connection_string)
    try:
        cursor = conn.cursor()
        if db_type == "sqlite":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        elif db_type == "postgresql":
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            """)
        elif db_type == "mysql":
            cursor.execute("SHOW TABLES")

        tables = [row[0] for row in cursor.fetchall()]
        return {"status": "ok", "tables": tables, "count": len(tables), "db_type": db_type}
    finally:
        conn.close()


def _describe_table(connection_string: str, table_name: str) -> dict:
    """Describe a table's schema."""
    # Validate table name (prevent injection)
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return {"error": "Invalid table name"}

    conn, db_type = _get_connection(connection_string)
    try:
        cursor = conn.cursor()
        columns = []

        if db_type == "sqlite":
            cursor.execute(f"PRAGMA table_info({table_name})")
            for row in cursor.fetchall():
                columns.append({
                    "name": row[1],
                    "type": row[2],
                    "nullable": not row[3],
                    "default": row[4],
                    "primary_key": bool(row[5]),
                })
            # Row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

        elif db_type == "postgresql":
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name))
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                })
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

        elif db_type == "mysql":
            cursor.execute(f"DESCRIBE {table_name}")
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[4],
                    "primary_key": row[3] == "PRI",
                })
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

        return {
            "status": "ok",
            "table": table_name,
            "columns": columns,
            "column_count": len(columns),
            "row_count": row_count,
            "db_type": db_type,
        }
    finally:
        conn.close()


def _insert_row(connection_string: str, table_name: str, data: dict) -> dict:
    """Insert a row into a table."""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return {"error": "Invalid table name"}

    conn, db_type = _get_connection(connection_string)
    try:
        cursor = conn.cursor()
        columns = list(data.keys())
        values = list(data.values())

        # Validate column names
        for col in columns:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                return {"error": f"Invalid column name: {col}"}

        col_str = ", ".join(columns)

        if db_type == "sqlite":
            placeholders = ", ".join(["?"] * len(values))
        else:
            placeholders = ", ".join(["%s"] * len(values))

        sql = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()

        return {
            "status": "ok",
            "message": f"Inserted 1 row into {table_name}",
            "table": table_name,
            "columns": columns,
        }
    finally:
        conn.close()


def _validate_output_path(output_path: str) -> Optional[str]:
    """Validate output file path against traversal attacks."""
    blocked = ["/etc/", "/var/", "/proc/", "/sys/", "/dev/", ".."]
    for pattern in blocked:
        if pattern in output_path:
            return f"Access denied: path contains blocked pattern '{pattern}'"
    real = os.path.realpath(output_path)
    parent = os.path.dirname(real)
    if not os.path.isdir(parent):
        return f"Directory does not exist: {parent}"
    return None


def _export_to_csv(connection_string: str, sql: str, output_path: str) -> dict:
    """Execute a query and export results to CSV."""
    path_err = _validate_output_path(output_path)
    if path_err:
        return {"error": path_err}

    result = _execute_query(connection_string, sql)
    if result.get("status") != "ok":
        return result

    rows = result.get("rows", [])
    columns = result.get("columns", [])

    if not rows:
        return {"error": "No data to export"}

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "status": "ok",
        "output": output_path,
        "rows_exported": len(rows),
        "columns": columns,
        "file_size_bytes": os.path.getsize(output_path),
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Universal Database MCP",
    instructions="Database connector for SQLite, PostgreSQL, and MySQL. Query data, explore schema, insert rows, and export to CSV. By MEOK AI Labs.")


@mcp.tool()
def query_sql(connection_string: str, sql: str, allow_write: bool = False, api_key: str = "") -> dict:
    """Execute a SQL query against a database. Supports SQLite, PostgreSQL, and MySQL.

    Connection string examples:
    - SQLite: 'sqlite:///path/to/db.sqlite' or just '/path/to/file.db'
    - PostgreSQL: 'postgresql://user:pass@localhost:5432/mydb'
    - MySQL: 'mysql://user:pass@localhost:3306/mydb'

    Args:
        connection_string: Database connection URI
        sql: SQL query to execute
        allow_write: Set True for INSERT/UPDATE/DELETE (safety guard)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    safety = _validate_query(sql, allow_write)
    if safety:
        return {"error": safety}
    try:
        return _execute_query(connection_string, sql)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_tables(connection_string: str, api_key: str = "") -> dict:
    """List all tables in a database.

    Args:
        connection_string: Database connection URI
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _list_tables(connection_string)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def describe_table(connection_string: str, table_name: str, api_key: str = "") -> dict:
    """Describe a table's schema: column names, types, nullability, defaults,
    primary keys, and row count.

    Args:
        connection_string: Database connection URI
        table_name: Name of the table to describe
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _describe_table(connection_string, table_name)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def insert_row(connection_string: str, table_name: str, data: dict, api_key: str = "") -> dict:
    """Insert a single row into a table. Column names and values are passed
    as a dictionary.

    Args:
        connection_string: Database connection URI
        table_name: Target table name
        data: Dictionary of column_name -> value pairs
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _insert_row(connection_string, table_name, data)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def export_to_csv(connection_string: str, sql: str, output_path: str = "", api_key: str = "") -> dict:
    """Execute a SELECT query and export results to a CSV file.

    Args:
        connection_string: Database connection URI
        sql: SELECT query to execute
        output_path: Path for the output CSV (default: temp file)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    safety = _validate_query(sql, allow_write=False)
    if safety:
        return {"error": safety}
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(), f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    try:
        return _export_to_csv(connection_string, sql, output_path)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
