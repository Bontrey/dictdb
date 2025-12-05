#!/usr/bin/env python3
"""
Filter JSONL file based on schema fields.
Usage: python filter_jsonl.py <n> [input_file] [schema_file] [output_file]
"""

import json
import sys
import re


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


def main():
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python filter_jsonl.py <n> [input_file] [schema_file] [output_file]")
        print("  n: number of lines to process")
        print("  input_file: path to input JSONL file (default: fr-extract.jsonl)")
        print("  schema_file: path to schema JSON file (default: schema.json)")
        print("  output_file: path to output file (default: stdout)")
        sys.exit(1)

    n = int(sys.argv[1])
    input_file = sys.argv[2] if len(sys.argv) > 2 else "fr-extract.jsonl"
    schema_file = sys.argv[3] if len(sys.argv) > 3 else "schema.json"
    output_file = sys.argv[4] if len(sys.argv) > 4 else None

    # Parse schema structure
    schema = parse_schema_structure(schema_file)
    if schema:
        print(f"Filtering to schema fields: {sorted(schema.keys())}", file=sys.stderr)
    else:
        print("Warning: Using pass-through mode (no filtering)", file=sys.stderr)

    # Open output file if specified, otherwise use stdout
    output = open(output_file, 'w', encoding='utf-8') if output_file else sys.stdout

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
                output.write(json.dumps(filtered_obj, ensure_ascii=False) + '\n')
                lines_output += 1

                # Stop when we've output n lines
                if lines_output >= n:
                    break

        print(f"\nRead {lines_read} lines, output {lines_output} lines", file=sys.stderr)

    finally:
        if output_file:
            output.close()


if __name__ == "__main__":
    main()
