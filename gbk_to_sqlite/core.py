#!/usr/bin/env python3
"""
Core functionality for gbk-to-sqlite.

This module contains the main functions for converting GenBank files to SQLite databases.
"""

import gzip
import warnings
from typing import List, Dict, Any, Generator, Union, Optional, TextIO
import logging
import gb_io

from .models import db, Genome, Record, Feature, Qualifier


def iter_gb_records(gbk_path: str) -> Generator:
    """
    Iterate through records in a GenBank file.

    Args:
        gbk_path (str): Path to the GenBank file (.gbk or .gbk.gz)

    Yields:
        Record objects from the GenBank file
    """
    if gbk_path.endswith(".gz"):
        with gzip.open(gbk_path, "rt") as file_obj:
            yield from gb_io.iter(file_obj)
    else:
        yield from gb_io.iter(gbk_path)


def convert_gbk_to_sqlite(gbk_path: str, batch_size: int = 5000) -> None:
    """
    Convert a GenBank file to SQLite database.

    Args:
        gbk_path (str): Path to the GenBank file to convert
        batch_size (int): Number of records to insert in each batch
    """
    logging.info(f"Converting {gbk_path} to SQLite database using batch size {batch_size}")
    genome = Genome.create(gbk_path=gbk_path)
    record_objs = []
    feature_tuples = []
    qualifier_tuples = []
    feature_columns = (
        "genome_id",
        "record_id",
        "feature_index",
        "location_start",
        "location_end",
        "location_strand",
    )
    qualifier_columns = ("genome_id", "record_id", "feature_index", "key", "value")

    for record in iter_gb_records(gbk_path):
        record_obj = Record.create(
            genome=genome,
            name=record.name,
            definition=record.definition,
            accession=record.accession,
            version=record.version,
        )
        record_objs.append(record_obj)
        for idx, feature in enumerate(record.features):
            # Skip complex Join locations that don't have strand attribute
            if not hasattr(feature.location, "strand"):
                warnings.warn(
                    f"Feature {idx} of record {record_obj.name} does not have strand attribute"
                )
                location_start = (
                    feature.location.start if hasattr(feature.location, "start") else None
                )
                location_end = feature.location.end if hasattr(feature.location, "end") else None
                location_strand = None
            else:
                location_start = feature.location.start
                location_end = feature.location.end
                location_strand = (
                    str(feature.location.strand) if feature.location.strand is not None else None
                )

            feature_tuples.append(
                (
                    genome.id,
                    record_obj.id,
                    idx,
                    location_start,
                    location_end,
                    location_strand,
                )
            )

            # Process feature batch if we've reached batch_size
            if len(feature_tuples) >= batch_size:
                _bulk_insert_tuples(feature_tuples, "feature", feature_columns)
                feature_tuples = []
            for q in feature.qualifiers:
                qualifier_tuples.append(
                    (
                        genome.id,
                        record_obj.id,
                        idx,
                        q.key,
                        q.value,
                    )
                )

                # Process qualifier batch if we've reached batch_size
                if len(qualifier_tuples) >= batch_size:
                    _bulk_insert_tuples(qualifier_tuples, "qualifier", qualifier_columns)
                    qualifier_tuples = []

    # Insert any remaining features and qualifiers
    if feature_tuples:
        _bulk_insert_tuples(feature_tuples, "feature", feature_columns)

    if qualifier_tuples:
        _bulk_insert_tuples(qualifier_tuples, "qualifier", qualifier_columns)


def _bulk_insert_tuples(values: List[tuple], table_name: str, columns: tuple) -> None:
    """
    Helper function for bulk insertion using raw SQL with tuples.

    Args:
        values: List of tuples containing data to insert
        table_name: Name of the table to insert into
        columns: Tuple of column names matching the value tuples
    """
    if not values:
        return

    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    conn = db.connection()
    cursor = conn.cursor()
    cursor.executemany(sql, values)
    conn.commit()


def create_indexes() -> None:
    """Create database indexes for optimal query performance."""
    with db:
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_qualifier_feature ON qualifier (feature);")
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_qualifier_feature_key ON qualifier (feature, key);"
        )
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_feature_record ON feature (record);")
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_record_genome ON record (genome);")


def optimize_database() -> None:
    """Apply SQLite optimizations for bulk import performance."""
    db.execute_sql("PRAGMA synchronous = OFF;")
    db.execute_sql("PRAGMA journal_mode = MEMORY;")
    db.execute_sql("PRAGMA temp_store = MEMORY;")
    db.execute_sql("PRAGMA cache_size = 100000;")
