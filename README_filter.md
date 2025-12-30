# JSONL Filter Script

## Quick Start

Use the `run_filter.sh` script to run the filter with all dependencies:

```bash
./run_filter.sh <n> [options]
```

This script automatically:
- Sets up the virtual environment if it doesn't exist
- Installs required dependencies (pyliblzfse) from requirements.txt
- Activates the environment and runs filter_jsonl.py

No manual setup required - just run the script!

## Usage

### JSONL Output Mode
```bash
./run_filter.sh <n> [input_file] [schema_file] [output_file]
# or
python3 filter_jsonl.py <n> [input_file] [schema_file] [output_file]
```

### SQLite Output Mode
```bash
./run_filter.sh <n> --sqlite <db_file> [input_file] [schema_file]
# or
python3 filter_jsonl.py <n> --sqlite <db_file> [input_file] [schema_file]
```

### Compressed SQLite Output Mode
```bash
./run_filter.sh <n> --sqlite <db_file> --compress [input_file] [schema_file]
# or
python3 filter_jsonl.py <n> --sqlite <db_file> --compress [input_file] [schema_file]
```
This creates a compressed database file using LZFSE compression (Apple's compression algorithm optimized for iOS/macOS).

### Parameters:
- `n`: Number of entries to output (optional, processes entire file if not specified)
- `input_file`: Path to input JSONL file (default: `fr-extract.jsonl`)
- `schema_file`: Path to schema file (default: `schema.json`)
- `output_file`: Path to output file (optional, default: stdout)
- `db_file`: Path to SQLite database file (with `--sqlite` flag)
- `--compress`: Compress the SQLite database using LZFSE (creates `.lzfse` file)

### Examples:

**JSONL output:**
```bash
# Process first 10 entries, output to stdout
./run_filter.sh 10

# Process first 100 entries, save to file
./run_filter.sh 100 fr-extract.jsonl schema.json filtered-output.jsonl

# Process first 1000 entries with custom input file
./run_filter.sh 1000 my-data.jsonl

# Pipe output to another tool (e.g., jq for pretty printing a single entry)
./run_filter.sh 1 | head -1 | jq .
```

**SQLite output:**
```bash
# Create SQLite database with 1000 entries
./run_filter.sh 1000 --sqlite dictionary.db

# Create database with custom files
./run_filter.sh 5000 --sqlite french.db fr-extract.jsonl schema.json

# Create compressed database (LZFSE format, optimized for iOS/macOS)
./run_filter.sh 1000 --sqlite dictionary.db --compress

# Query the database
sqlite3 dictionary.db "SELECT word, pos FROM entries LIMIT 10;"

# Full-text search (prefix matching)
sqlite3 dictionary.db "SELECT e.word FROM entries_fts fts JOIN entries e ON fts.rowid = e.id WHERE entries_fts MATCH 'lib*' LIMIT 10;"

# Full-text search (substring matching with trigram index)
sqlite3 dictionary.db "SELECT e.word FROM entries_fts_trigram fts JOIN entries e ON fts.rowid = e.id WHERE entries_fts_trigram MATCH 'lib' LIMIT 10;"
```

See [SQLITE_USAGE.md](SQLITE_USAGE.md) for detailed SQLite usage including iOS/Swift examples.

## How it works

The script:
1. Parses the schema file to understand the structure at all levels
2. Processes the input JSONL file line-by-line (streaming)
3. **Filters to only include entries where `lang_code` is "fr"**
4. **Recursively filters each JSON object to only include schema fields** (at all nesting levels)
5. Outputs exactly `n` filtered JSON objects (continues reading until n matching lines are found)

This approach avoids loading the entire file into memory, making it suitable for very large files.

**Recursive filtering examples:**
- Top-level: Only includes `word`, `pos`, `etymology_texts`, `senses`, `sounds`, `tags`
- In `senses`: Only includes `glosses`, `categories`, `examples`, `tags`
- In `examples`: Only includes `text`, `bold_text_offsets` (filters out `ref`, etc.)
- In `sounds`: Only includes `ipa`, `ogg_url`, `mp3_url`, `wav_url` (filters out `audio`, `raw_tags`, `rhymes`, `homophone`, etc.)

**Note:** The parameter `n` specifies the number of lines to OUTPUT, not the number of lines to READ. The script will continue reading the input file until it finds `n` entries that match the filter criteria (lang_code == "fr").
