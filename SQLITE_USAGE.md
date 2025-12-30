# SQLite Database Usage

## Creating the Database

```bash
# Create a SQLite database with 1000 French dictionary entries
python3 filter_jsonl.py 1000 --sqlite dictionary.db

# Or with custom input/schema files
python3 filter_jsonl.py 5000 --sqlite dictionary.db fr-extract.jsonl schema.json
```

## Database Schema

The database contains:

- **entries** table: Main storage with columns:
  - `id`: Primary key (INTEGER)
  - `word`: The dictionary word (TEXT, indexed)
  - `pos`: Part of speech (TEXT)
  - `data`: Full JSON entry data (TEXT)

- **entries_fts**: FTS5 virtual table with default tokenizer (best for short prefix queries)
- **entries_fts_trigram**: FTS5 virtual table with trigram tokenizer (best for substring matching)

## Querying from Command Line

```bash
# Count entries
sqlite3 dictionary.db "SELECT COUNT(*) FROM entries;"

# Find exact word match
sqlite3 dictionary.db "SELECT id, word, pos FROM entries WHERE word = 'maison';"

# Full-text search (finds "maison", "maisons", etc.)
sqlite3 dictionary.db "SELECT e.id, e.word, e.pos FROM entries_fts fts JOIN entries e ON fts.rowid = e.id WHERE entries_fts MATCH 'maison';"

# Get full JSON data for a word
sqlite3 dictionary.db "SELECT data FROM entries WHERE word = 'livre' LIMIT 1;"

# Prefix search (words starting with "lib") - using default tokenizer
sqlite3 dictionary.db "SELECT e.id, e.word FROM entries_fts fts JOIN entries e ON fts.rowid = e.id WHERE entries_fts MATCH 'lib*' LIMIT 10;"

# Substring search (words containing "ber") - using trigram tokenizer
sqlite3 dictionary.db "SELECT e.id, e.word FROM entries_fts_trigram fts JOIN entries e ON fts.rowid = e.id WHERE entries_fts_trigram MATCH 'ber' LIMIT 10;"
```

## Using from iOS/Swift

### 1. Add the database to your Xcode project

1. Drag `dictionary.db` into your Xcode project
2. Make sure "Copy items if needed" is checked
3. Add to target membership

### 2. Swift code example

```swift
import Foundation
import SQLite3

class DictionaryDatabase {
    private var db: OpaquePointer?

    init() {
        // Open database from bundle
        if let dbPath = Bundle.main.path(forResource: "dictionary", ofType: "db") {
            if sqlite3_open(dbPath, &db) != SQLITE_OK {
                print("Error opening database")
            }
        }
    }

    deinit {
        sqlite3_close(db)
    }

    // Exact word lookup
    func lookupWord(_ word: String) -> [DictionaryEntry] {
        var entries: [DictionaryEntry] = []
        let query = "SELECT id, word, pos, data FROM entries WHERE word = ?"
        var statement: OpaquePointer?

        if sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_text(statement, 1, (word as NSString).utf8String, -1, nil)

            while sqlite3_step(statement) == SQLITE_ROW {
                let id = Int(sqlite3_column_int(statement, 0))
                let word = String(cString: sqlite3_column_text(statement, 1))
                let pos = String(cString: sqlite3_column_text(statement, 2))
                let dataString = String(cString: sqlite3_column_text(statement, 3))

                if let data = dataString.data(using: .utf8),
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    entries.append(DictionaryEntry(id: id, word: word, pos: pos, data: json))
                }
            }
        }

        sqlite3_finalize(statement)
        return entries
    }

    // Full-text search (finds partial matches)
    // Intelligently chooses between default and trigram tokenizers
    func searchWords(_ searchTerm: String) -> [SearchResult] {
        var results: [SearchResult] = []

        // Use default tokenizer for short queries (1-2 chars) with prefix matching
        // Use trigram tokenizer for longer queries if substring matching is needed
        let useDefaultTokenizer = searchTerm.count <= 2
        let tableName = useDefaultTokenizer ? "entries_fts" : "entries_fts"

        let query = """
            SELECT e.id, e.word, e.pos
            FROM \(tableName) fts
            JOIN entries e ON fts.rowid = e.id
            WHERE \(tableName) MATCH ?
            LIMIT 50
        """
        var statement: OpaquePointer?

        // Add wildcard for prefix matching
        let searchPattern = searchTerm + "*"

        if sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_text(statement, 1, (searchPattern as NSString).utf8String, -1, nil)

            while sqlite3_step(statement) == SQLITE_ROW {
                let id = Int(sqlite3_column_int(statement, 0))
                let word = String(cString: sqlite3_column_text(statement, 1))
                let pos = String(cString: sqlite3_column_text(statement, 2))
                results.append(SearchResult(id: id, word: word, pos: pos))
            }
        }

        sqlite3_finalize(statement)
        return results
    }

    // Substring search using trigram tokenizer
    func searchWordsSubstring(_ searchTerm: String) -> [SearchResult] {
        var results: [SearchResult] = []
        let query = """
            SELECT e.id, e.word, e.pos
            FROM entries_fts_trigram fts
            JOIN entries e ON fts.rowid = e.id
            WHERE entries_fts_trigram MATCH ?
            LIMIT 50
        """
        var statement: OpaquePointer?

        if sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_text(statement, 1, (searchTerm as NSString).utf8String, -1, nil)

            while sqlite3_step(statement) == SQLITE_ROW {
                let id = Int(sqlite3_column_int(statement, 0))
                let word = String(cString: sqlite3_column_text(statement, 1))
                let pos = String(cString: sqlite3_column_text(statement, 2))
                results.append(SearchResult(id: id, word: word, pos: pos))
            }
        }

        sqlite3_finalize(statement)
        return results
    }
}

struct DictionaryEntry {
    let id: Int
    let word: String
    let pos: String
    let data: [String: Any]
}

struct SearchResult {
    let id: Int
    let word: String
    let pos: String
}
```

### 3. Using with SwiftUI

```swift
struct DictionarySearchView: View {
    @State private var searchText = ""
    @State private var results: [SearchResult] = []
    private let db = DictionaryDatabase()

    var body: some View {
        NavigationView {
            List(results, id: \.id) { result in
                VStack(alignment: .leading) {
                    Text(result.word)
                        .font(.headline)
                    Text(result.pos)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .searchable(text: $searchText)
            .onChange(of: searchText) { newValue in
                results = db.searchWords(newValue)
            }
            .navigationTitle("French Dictionary")
        }
    }
}
```

## Choosing Between FTS5 Indexes

The database includes two FTS5 indexes optimized for different query patterns:

### entries_fts (Default Tokenizer)
- **Best for**: Short prefix queries (1-2 characters) like `a*`, `li*`
- **Use when**: User is typing a search query and you want fast prefix matching
- **Example**: `WHERE entries_fts MATCH 'li*'` efficiently finds "liberté", "livre", "lire"

### entries_fts_trigram (Trigram Tokenizer)
- **Best for**: Substring matching anywhere in the word
- **Use when**: You need to find words containing a sequence of characters
- **Limitation**: Less efficient for very short prefixes (<3 characters)
- **Example**: `WHERE entries_fts_trigram MATCH 'ber'` finds "liberté", "auberge"

### Recommendation
For autocomplete/search-as-you-type features:
- Use **entries_fts** for queries of 1-2 characters
- Switch to **entries_fts_trigram** for queries of 3+ characters if you need substring matching
- Or simply use **entries_fts** for all prefix queries (most common use case)

## FTS5 Query Syntax

The full-text search supports:

- **Prefix search**: `lib*` matches "libre", "liberté", "libération"
- **Exact phrase**: `"maison blanche"` matches exact phrase
- **AND operator**: `maison AND blanc` (both terms must appear)
- **OR operator**: `maison OR appartement`
- **NOT operator**: `maison NOT -appartement`

Examples:
```sql
-- Words starting with "lib"
WHERE entries_fts MATCH 'lib*'

-- Words starting with "mai" OR "més"
WHERE entries_fts MATCH 'mai* OR més*'
```

## Performance Notes

- Two FTS5 indexes provide optimal performance for different query patterns:
  - `entries_fts` (default tokenizer): Fast prefix queries of any length
  - `entries_fts_trigram`: Efficient substring matching (3+ characters)
- Regular B-tree index on `word` column for exact lookups
- JSON data stored as TEXT (parse on retrieval)
- Batch inserts (100 rows at a time) during database creation for optimal write performance
- Both FTS5 indexes are kept in sync automatically via triggers
