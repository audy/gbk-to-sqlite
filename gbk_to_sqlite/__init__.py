"""
gbk-to-sqlite - Convert GenBank files to SQLite databases

This package provides utilities for converting GenBank format files
to SQLite databases with a structured schema.
"""

__version__ = "0.1.0"

from .models import db, Genome, Record, Feature, Qualifier
from .core import convert_gbk_to_sqlite, iter_gb_records

__all__ = [
    "db",
    "Genome",
    "Record",
    "Feature",
    "Qualifier",
    "convert_gbk_to_sqlite",
    "iter_gb_records",
]