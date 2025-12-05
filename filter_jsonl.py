#!/usr/bin/env python3
"""
Filter JSONL file based on schema fields.
Usage: python filter_jsonl.py <n> [input_file] [schema_file] [output_file]
       python filter_jsonl.py <n> --sqlite output.db [input_file] [schema_file]
"""

import json
import sys
import re
import sqlite3
import os


def parse_schema_structure(schema_file):
    """
    Parse schema file to understand the structure and allowed fields at each level.
    Returns a schema dict that can be used for recursive filtering.
    """
    with open(schema_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace type annotations with valid JSON values for parsing
    # Handle patterns like "string (optional)" or "string"
    content = re.sub(r'"string\s*\([^)]*\)"', '""', content)
    content = re.sub(r'"string"', '""', content)
    content = re.sub(r'\bnumber\b', '0', content)
    content = re.sub(r',(\s*[}\]])', r'\1', content)  # Remove trailing commas

    try:
        schema = json.loads(content)
        return schema
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse schema as JSON: {e}", file=sys.stderr)
        print(f"First 200 chars of cleaned content: {content[:200]}", file=sys.stderr)
        return None


def filter_by_schema(obj, schema):
    """
    Recursively filter an object based on the schema structure.
    """
    if schema is None:
        return obj

    if isinstance(schema, dict) and isinstance(obj, dict):
        # Filter dictionary keys based on schema
        result = {}
        for key in schema.keys():
            if key in obj:
                result[key] = filter_by_schema(obj[key], schema[key])
        return result

    elif isinstance(schema, list) and len(schema) > 0:
        # Schema defines an array structure
        if isinstance(obj, list):
            # Apply the schema of the first element to all elements
            element_schema = schema[0]
            return [filter_by_schema(item, element_schema) for item in obj]
        else:
            return obj

    else:
        # Primitive value or no schema defined
        return obj


def init_sqlite_db(db_path):
    """
    Initialize SQLite database with schema for dictionary entries.
    Uses FTS5 for full-text search on the word field.
    """
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create main table for dictionary entries
    cursor.execute('''
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            pos TEXT,
            data TEXT NOT NULL
        )
    ''')

    # Create FTS5 virtual table for full-text search on word field
    cursor.execute('''
        CREATE VIRTUAL TABLE entries_fts USING fts5(
            word,
            content=entries,
            content_rowid=id
        )
    ''')

    # Create triggers to keep FTS5 table in sync
    cursor.execute('''
        CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, word) VALUES (new.id, new.word);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER entries_ad AFTER DELETE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, word) VALUES('delete', old.id, old.word);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER entries_au AFTER UPDATE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, word) VALUES('delete', old.id, old.word);
            INSERT INTO entries_fts(rowid, word) VALUES (new.id, new.word);
        END
    ''')

    # Create index on word for non-FTS queries
    cursor.execute('CREATE INDEX idx_word ON entries(word)')

    conn.commit()
    return conn


class SqliteOutput:
    """Handler for SQLite database output."""

    def __init__(self, db_path):
        self.conn = init_sqlite_db(db_path)
        self.cursor = self.conn.cursor()
        self.batch = []
        self.batch_size = 100

    def write(self, filtered_obj):
        """Write a filtered entry to the database."""
        word = filtered_obj.get('word', '')
        pos = filtered_obj.get('pos', '')
        data = json.dumps(filtered_obj, ensure_ascii=False)

        self.batch.append((word, pos, data))

        if len(self.batch) >= self.batch_size:
            self.flush()

    def flush(self):
        """Flush batch to database."""
        if self.batch:
            self.cursor.executemany(
                'INSERT INTO entries (word, pos, data) VALUES (?, ?, ?)',
                self.batch
            )
            self.conn.commit()
            self.batch = []

    def close(self):
        """Close database connection."""
        self.flush()
        self.conn.close()


class JsonlOutput:
    """Handler for JSONL output."""

    def __init__(self, output_file):
        self.output = open(output_file, 'w', encoding='utf-8') if output_file else sys.stdout
        self.should_close = output_file is not None

    def write(self, filtered_obj):
        """Write a filtered entry as JSONL."""
        self.output.write(json.dumps(filtered_obj, ensure_ascii=False) + '\n')

    def close(self):
        """Close output file."""
        if self.should_close:
            self.output.close()


def main():
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  JSONL: python3 filter_jsonl.py <n> [input_file] [schema_file] [output_file]")
        print("  SQLite: python3 filter_jsonl.py <n> --sqlite <db_file> [input_file] [schema_file]")
        print()
        print("Arguments:")
        print("  n: number of entries to output")
        print("  input_file: path to input JSONL file (default: fr-extract.jsonl)")
        print("  schema_file: path to schema JSON file (default: schema.json)")
        print("  output_file: path to output file (default: stdout)")
        print("  db_file: path to SQLite database file (with --sqlite)")
        sys.exit(1)

    # Parse arguments
    n = int(sys.argv[1])

    # Check for --sqlite flag
    use_sqlite = False
    db_file = None
    arg_offset = 2

    if len(sys.argv) > 2 and sys.argv[2] == '--sqlite':
        use_sqlite = True
        if len(sys.argv) < 4:
            print("Error: --sqlite requires a database file path", file=sys.stderr)
            sys.exit(1)
        db_file = sys.argv[3]
        arg_offset = 4

    # Parse remaining arguments
    if use_sqlite:
        input_file = sys.argv[arg_offset] if len(sys.argv) > arg_offset else "fr-extract.jsonl"
        schema_file = sys.argv[arg_offset + 1] if len(sys.argv) > arg_offset + 1 else "schema.json"
        output_handler = SqliteOutput(db_file)
        print(f"Output mode: SQLite database -> {db_file}", file=sys.stderr)
    else:
        input_file = sys.argv[arg_offset] if len(sys.argv) > arg_offset else "fr-extract.jsonl"
        schema_file = sys.argv[arg_offset + 1] if len(sys.argv) > arg_offset + 1 else "schema.json"
        output_file = sys.argv[arg_offset + 2] if len(sys.argv) > arg_offset + 2 else None
        output_handler = JsonlOutput(output_file)
        print(f"Output mode: JSONL -> {output_file or 'stdout'}", file=sys.stderr)

    # Parse schema structure
    schema = parse_schema_structure(schema_file)
    if schema:
        print(f"Filtering to schema fields: {sorted(schema.keys())}", file=sys.stderr)
    else:
        print("Warning: Using pass-through mode (no filtering)", file=sys.stderr)

    try:
        # Process input file line by line
        lines_read = 0
        lines_output = 0

        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                lines_read += 1

                # Parse JSON line
                obj = json.loads(line)

                # Filter by lang_code == "fr"
                if obj.get('lang_code') != 'fr':
                    continue

                # Filter to schema fields (recursively)
                filtered_obj = filter_by_schema(obj, schema)

                # Write filtered object
                output_handler.write(filtered_obj)
                lines_output += 1

                # Stop when we've output n lines
                if lines_output >= n:
                    break

        print(f"\nRead {lines_read} lines, output {lines_output} entries", file=sys.stderr)

    finally:
        output_handler.close()


if __name__ == "__main__":
    main()
