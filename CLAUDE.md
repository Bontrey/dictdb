# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dictionary database processing tool that filters and extracts French dictionary entries from a large JSONL file (Wiktionary data dump). The core functionality is streaming JSONL processing with recursive schema-based filtering.

## Key Commands

```bash
# Filter and extract n French entries (outputs to stdout)
python3 filter_jsonl.py <n>

# Filter with custom files
python3 filter_jsonl.py <n> [input_file] [schema_file] [output_file]

# Examples
python3 filter_jsonl.py 100                                    # First 100 French entries to stdout
python3 filter_jsonl.py 1000 fr-extract.jsonl schema.json output.jsonl  # Save to file
python3 filter_jsonl.py 1 | jq .                              # Pretty-print one entry
```

## Architecture

### Core Components

**filter_jsonl.py** - Streaming JSONL processor
- **parse_schema_structure()**: Converts schema.json (with type annotations like `"string"`, `number`, `"string (optional)"`) into a parsable structure by regex replacement
- **filter_by_schema()**: Recursively filters JSON objects to match schema structure at all nesting levels
- **main()**: Streams input line-by-line, filters by `lang_code=="fr"`, applies recursive schema filtering, outputs exactly n matches

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
- **README_filter.md**: User documentation with examples
- **.gitignore**: Excludes large data files and JSONL outputs (except schema.json)
