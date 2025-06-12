#!/usr/bin/env python3
"""
Command-line interface for gbk-to-sqlite.

This module provides the command-line interface for converting GenBank files to SQLite databases.
"""

import sys
import os
import glob
import argparse
from tqdm import tqdm

from .models import db, Genome, Record, Feature, Qualifier
from .core import convert_gbk_to_sqlite, optimize_database, create_indexes


def main() -> None:
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Convert one or more GenBank files to a SQLite database.")
    parser.add_argument("--genbank-files", nargs="+", help="Input GenBank file(s)")
    parser.add_argument('--genbank-glob', type=str, help='glob-string of genbank files')
    parser.add_argument("--sqlite-db", help="Output SQLite database file")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for bulk inserts")
    args = parser.parse_args()

    if args.genbank_files:
        genbank_files = args.genbank_files
    elif args.genbank_glob:
        genbank_files = glob.glob(args.genbank_glob)
    else:
        print("Error: No input files specified.")
        sys.exit(1)

    # Check all files exist before proceeding
    for gbk_path in genbank_files:
        if not os.path.exists(gbk_path):
            print(f"Error: Input file {gbk_path} does not exist.")
            sys.exit(1)

    # Initialize Peewee DB and create tables
    db.init(args.sqlite_db)
    db.connect()

    # Apply optimizations for bulk import performance
    optimize_database()

    # Create tables if they don't exist
    db.create_tables([Genome, Record, Feature, Qualifier])

    with db.atomic():
        for gbk_path in tqdm(genbank_files, desc="Loading"):
            convert_gbk_to_sqlite(gbk_path, batch_size=args.batch_size)

    # Create indexes after all bulk inserts for optimal performance
    create_indexes()
    db.close()


if __name__ == "__main__":
    main()
