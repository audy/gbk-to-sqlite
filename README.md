# gbk-to-sqlite

[![Tests](https://github.com/audy/gbk-to-sqlite/actions/workflows/test.yml/badge.svg)](https://github.com/audy/gbk-to-sqlite/actions/workflows/test.yml)

Convert GenBank files to SQLite databases with an intuitive, queryable schema.

## Summary

gbk-to-sqlite is a Python tool designed to convert GenBank (`.gbk` or `.gbk.gz`) format files into SQLite databases. This enables easier programmatic access, efficient storage, and complex querying of genomic data.

Key features:
- Fast and memory-efficient conversion of large GenBank files
- Support for both regular and gzipped GenBank files
- Comprehensive database schema that preserves all relevant GenBank information
- Automatic handling of complex features including multi-value qualifiers
- Clean Python API for programmatic usage
- SQL query interface for powerful data analysis

## Installation

Install with pip:

```bash
pip install gbk-to-sqlite
```

Or with [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv pip install gbk-to-sqlite
```

## Database Schema and Models

gbk-to-sqlite uses a relational model to represent GenBank data:

### Genome
Represents a GenBank file:
- `id`: Unique identifier (auto-generated)
- `gbk_path`: Path to the source GenBank file

### Record
Represents a sequence record in the GenBank file:
- `id`: Unique identifier (auto-generated)
- `genome`: Foreign key reference to the Genome
- `name`: The LOCUS name
- `definition`: The DEFINITION field (sequence description)
- `accession`: The ACCESSION number
- `version`: The VERSION identifier

### Feature
Represents a feature annotation (gene, CDS, etc.):
- `genome`, `record`, `feature_index`: Composite primary key
- `location_start`: Start position (0-based)
- `location_end`: End position
- `location_strand`: Strand orientation ('+', '-', or null)

### Qualifier
Represents a feature's qualifier (e.g., /gene="xyz"):
- `genome`, `record`, `feature_index`: References to the associated Feature
- `key`: Qualifier name (e.g., "gene")
- `value`: Qualifier value (e.g., "xyz"), can be null for flag qualifiers

## Examples

### Command-line Usage

Convert a single GenBank file:

```bash
gbk-to-sqlite --genbank-files sequence.gbk --sqlite-db output.sqlite
```

Convert multiple files:

```bash
gbk-to-sqlite --genbank-files file1.gbk file2.gbk.gz --sqlite-db output.sqlite
```

Use glob patterns to convert many files:

```bash
gbk-to-sqlite --genbank-glob "data/*.gbk.gz" --sqlite-db output.sqlite
```

### Python API Usage

```python
from gbk_to_sqlite import convert_gbk_to_sqlite, db, Genome, Record, Feature, Qualifier

# Initialize the database
db.init("output.sqlite")
db.connect()
db.create_tables([Genome, Record, Feature, Qualifier])

# Convert GenBank files
with db.atomic():
    convert_gbk_to_sqlite("sequence.gbk")

# Query the database
records = Record.select().where(Record.accession == "NC_000001")
for record in records:
    print(f"Record: {record.name}, Definition: {record.definition}")

    # Find all genes
    genes = Feature.select().join(Qualifier).where(
        (Feature.record == record) &
        (Qualifier.key == "gene")
    )

    for gene in genes:
        gene_name = Qualifier.select().where(
            (Qualifier.feature == gene) &
            (Qualifier.key == "gene")
        ).first().value

        print(f"Gene: {gene_name}, Location: {gene.location_start}..{gene.location_end}")

# Close the database connection
db.close()
```

## Known Limitations

- Complex locations (join, order, complement) are stored with a simplified representation
- Join locations may not preserve strand information
- Some advanced GenBank features might not be fully supported

## Development

To contribute to gbk-to-sqlite:

1. Clone the repository
2. Install development dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest tests/
   ```

## License

MIT License

Copyright (c) 2024 Austin Davis-Richardson

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
