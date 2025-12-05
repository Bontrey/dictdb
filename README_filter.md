# JSONL Filter Script

## Usage

```bash
python3 filter_jsonl.py <n> [input_file] [schema_file] [output_file]
```

### Parameters:
- `n`: Number of lines to process (required)
- `input_file`: Path to input JSONL file (default: `fr-extract.jsonl`)
- `schema_file`: Path to schema file (default: `schema.json`)
- `output_file`: Path to output file (optional, default: stdout)

### Examples:

```bash
# Process first 10 lines, output to stdout
python3 filter_jsonl.py 10

# Process first 100 lines, save to file
python3 filter_jsonl.py 100 fr-extract.jsonl schema.json filtered-output.jsonl

# Process first 1000 lines with custom input file
python3 filter_jsonl.py 1000 my-data.jsonl

# Pipe output to another tool (e.g., jq for pretty printing a single line)
python3 filter_jsonl.py 1 | head -1 | jq .
```

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
