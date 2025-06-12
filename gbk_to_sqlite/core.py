#!/usr/bin/env python3
"""
Core functionality for gbk-to-sqlite.

This module contains the main functions for converting GenBank files to SQLite databases.
"""

import gzip
import warnings
from typing import List, Dict, Any, Generator, Union, Optional, TextIO
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


def convert_gbk_to_sqlite(gbk_path: str) -> None:
    """
    Convert a GenBank file to SQLite database.

    Args:
        gbk_path (str): Path to the GenBank file to convert
    """
    genome = Genome.create(gbk_path=gbk_path)
    record_objs = []
    feature_dicts = []
    qualifier_dicts = []

    for record in iter_gb_records(gbk_path):
        record_obj = Record.create(
            genome=genome,
            name=record.name,
            definition=record.definition,
            accession=record.accession,
            version=record.version
        )
        record_objs.append(record_obj)
        for idx, feature in enumerate(record.features):
            # Skip complex Join locations that don't have strand attribute
            if not hasattr(feature.location, 'strand'):
                warnings.warn(f"Feature {idx} of record {record_obj.name} does not have strand attribute")
                location_start = feature.location.start if hasattr(feature.location, 'start') else None
                location_end = feature.location.end if hasattr(feature.location, 'end') else None
                location_strand = None
            else:
                location_start = feature.location.start
                location_end = feature.location.end
                location_strand = str(feature.location.strand) if feature.location.strand is not None else None

            feature_dicts.append(
                dict(
                    genome_id=genome.id,
                    record_id=record_obj.id,
                    feature_index=idx,
                    location_start=location_start,
                    location_end=location_end,
                    location_strand=location_strand,
                )
            )
            for q in feature.qualifiers:
                qualifier_dicts.append(
                    dict(
                        genome_id=genome.id,
                        record_id=record_obj.id,
                        feature_index=idx,
                        key=q.key,
                        value=q.value,
                    )
                )

    # Bulk insert features and qualifiers using raw SQL for improved performance
    if feature_dicts:
        _bulk_insert(feature_dicts, "feature")

    if qualifier_dicts:
        _bulk_insert(qualifier_dicts, "qualifier")


def _bulk_insert(dicts: List[Dict[str, Any]], table_name: str) -> None:
    """
    Helper function for bulk insertion using raw SQL.

    Args:
        dicts: List of dictionaries containing data to insert
        table_name: Name of the table to insert into
    """
    keys = dicts[0].keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?'] * len(keys))
    sql = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'
    values = [tuple(d[k] for k in keys) for d in dicts]
    conn = db.connection()
    cursor = conn.cursor()
    cursor.executemany(sql, values)
    conn.commit()


def create_indexes() -> None:
    """Create database indexes for optimal query performance."""
    with db:
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_qualifier_feature ON qualifier (feature);")
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_qualifier_feature_key ON qualifier (feature, key);")
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_feature_record ON feature (record);")
        db.execute_sql("CREATE INDEX IF NOT EXISTS idx_record_genome ON record (genome);")


def optimize_database() -> None:
    """Apply SQLite optimizations for bulk import performance."""
    db.execute_sql("PRAGMA synchronous = OFF;")
    db.execute_sql("PRAGMA journal_mode = MEMORY;")
    db.execute_sql("PRAGMA temp_store = MEMORY;")
    db.execute_sql("PRAGMA cache_size = 100000;")
