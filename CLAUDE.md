# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dictionary database processing tool that filters and extracts French dictionary entries from a large JSONL file (Wiktionary data dump). The core functionality is streaming JSONL processing with recursive schema-based filtering.

## Key Commands

**Recommended**: Use `run_filter.sh` which automatically sets up the virtual environment and dependencies:

```bash
# Filter and extract n French entries (outputs to stdout)
./run_filter.sh <n>

# Filter with custom files
./run_filter.sh <n> [input_file] [schema_file] [output_file]

# SQLite output mode
./run_filter.sh <n> --sqlite <db_file> [input_file] [schema_file]

# SQLite with LZFSE compression (iOS-optimized)
./run_filter.sh <n> --sqlite <db_file> --compress [input_file] [schema_file]

# Examples
./run_filter.sh 100                                    # First 100 French entries to stdout
./run_filter.sh 1000 fr-extract.jsonl schema.json output.jsonl  # Save to file
./run_filter.sh 1 | jq .                              # Pretty-print one entry
./run_filter.sh 1000 --sqlite dict.db --compress      # Create compressed SQLite database
```

**Alternative**: Run directly with Python (requires manual venv setup):
```bash
python3 filter_jsonl.py <n> [options]
```

## Architecture

### Core Components

**filter_jsonl.py** - Streaming JSONL processor
- **parse_schema_structure()**: Converts schema.json (with type annotations like `"string"`, `number`, `"string (optional)"`) into a parsable structure by regex replacement
- **filter_by_schema()**: Recursively filters JSON objects to match schema structure at all nesting levels
- **compress_sqlite_db()**: Compresses SQLite databases using LZFSE (Apple's compression algorithm)
- **SqliteOutput**: Handler for SQLite database output with FTS5 full-text search (dual indexes: prefix + trigram)
- **main()**: Streams input line-by-line, filters by `lang_code=="fr"`, applies recursive schema filtering, outputs exactly n matches

**run_filter.sh** - Convenience script
- Automatically creates virtual environment if not present
- Installs dependencies (pyliblzfse) from requirements.txt
- Activates venv and runs filter_jsonl.py with provided arguments

**schema.json** - Dictionary entry structure definition
- Defines allowed fields at each nesting level
- Uses type annotations: `"string"`, `number`, `"string (optional)"`
- Structure: word → pos → etymology_texts/senses/sounds/tags → nested objects

### Data Flow

1. Parse schema.json → convert type annotations to valid JSON
2. Stream fr-extract.jsonl line-by-line (6.1GB file, never loads fully)
3. For each line:
   - Parse JSON
   - Check `lang_code == "fr"` (filter criterion)
   - Recursively apply schema filtering (removes extra fields at all levels)
   - Output filtered JSON line
4. Stop after outputting exactly n matches

### Schema Filtering Behavior

The recursive filtering removes fields not in schema at every level:
- **Top-level removed**: `lang_code`, `lang`, `pos_title`, `forms`, `translations`, `synonyms`, `derived`, `related`, `anagrams`, `categories`, `attestations`
- **In senses.examples removed**: `ref` field
- **In sounds removed**: `audio`, `raw_tags`, `rhymes`, `homophone`

### Important Implementation Details

**Parameter `n` semantics**: Specifies OUTPUT count, not INPUT count. The script may read 100+ lines to output 10 French entries if the input contains mixed languages.

**Memory efficiency**: Uses line-by-line streaming to handle 6GB+ files without loading into memory.

**Schema parsing quirk**: The schema.json file uses non-standard JSON syntax with type annotations (e.g., `"string (optional)"`). These are stripped via regex before JSON parsing.

## File Organization

- **fr-extract.jsonl** (6.1GB, gitignored): Source data - Wiktionary French dictionary dump
- **schema.json**: Field structure specification for filtering
- **filter_jsonl.py**: Main processing script
- **run_filter.sh**: Convenience script with auto-setup of virtual environment
- **requirements.txt**: Python dependencies (pyliblzfse==0.4.1)
- **venv/**: Virtual environment directory (auto-created, gitignored)
- **README_filter.md**: User documentation with examples
- **.gitignore**: Excludes large data files, JSONL outputs (except schema.json), venv/, *.lzfse

## Dependencies

- **pyliblzfse**: LZFSE compression library for iOS-compatible database compression
- Installed automatically by run_filter.sh or manually via: `pip install -r requirements.txt`
