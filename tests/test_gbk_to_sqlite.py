import os
import tempfile
import pytest
import gzip
import warnings

from gbk_to_sqlite.models import db, Genome, Feature, Qualifier, Record
from gbk_to_sqlite import core

# ===== Test Fixtures =====


@pytest.fixture
def minimal_gbk_content():
    return """\
LOCUS       TEST0001               10 bp    DNA     linear   UNA 01-JAN-2000
DEFINITION  Minimal test sequence.
ACCESSION   TEST0001
VERSION     TEST0001.1
FEATURES             Location/Qualifiers
     gene            1..10
                     /gene="foo"
                     /product="bar"
ORIGIN
        1 atgctagcta
//
"""


@pytest.fixture
def multiqual_gbk_content():
    return """\
LOCUS       TEST0002               10 bp    DNA     linear   UNA 01-JAN-2000
DEFINITION  Test sequence with multi-valued qualifier.
ACCESSION   TEST0002
VERSION     TEST0002.1
FEATURES             Location/Qualifiers
     gene            1..10
                     /gene="foo"
                     /note="first note"
                     /note="second note"
ORIGIN
        1 atgctagcta
//
"""


@pytest.fixture
def negative_strand_gbk_content():
    return """\
LOCUS       TEST0003               10 bp    DNA     linear   UNA 01-JAN-2000
DEFINITION  Negative strand feature test.
ACCESSION   TEST0003
VERSION     TEST0003.1
FEATURES             Location/Qualifiers
     gene            complement(1..10)
                     /gene="negfoo"
                     /product="negbar"
ORIGIN
        1 atgctagcta
//
"""


@pytest.fixture
def join_location_gbk_content():
    return """\
LOCUS       TEST0004               15 bp    DNA     linear   UNA 01-JAN-2000
DEFINITION  Join location feature test.
ACCESSION   TEST0004
VERSION     TEST0004.1
FEATURES             Location/Qualifiers
     gene            join(1..5,11..15)
                     /gene="joinfoo"
                     /product="joinbar"
ORIGIN
        1 atgctatgct atgct
//
"""


@pytest.fixture
def null_qualifier_gbk_content():
    return """\
LOCUS       TESTNULL               10 bp    DNA     linear   UNA 01-JAN-2000
DEFINITION  Null qualifier test.
ACCESSION   TESTNULL
VERSION     TESTNULL.1
FEATURES             Location/Qualifiers
     gene            1..10
                     /pseudo
                     /gene="nullfoo"
ORIGIN
        1 atgctagcta
//
"""


@pytest.fixture
def db_with_tables(tmp_path):
    """Create a database with tables"""
    db_path = tmp_path / "test.sqlite"
    db.init(str(db_path))
    db.connect()
    db.create_tables([Genome, Record, Feature, Qualifier])
    try:
        yield db_path
    finally:
        db.close()


@pytest.fixture
def minimal_gbk_file(tmp_path, minimal_gbk_content):
    """Create a GenBank file with minimal content"""
    gbk_path = tmp_path / "minimal.gbk"
    with open(gbk_path, "w") as f:
        f.write(minimal_gbk_content)
    return gbk_path


@pytest.fixture
def multiqual_gbk_file(tmp_path, multiqual_gbk_content):
    """Create a GenBank file with multiple qualifiers"""
    gbk_path = tmp_path / "multiqual.gbk"
    with open(gbk_path, "w") as f:
        f.write(multiqual_gbk_content)
    return gbk_path


@pytest.fixture
def negative_strand_gbk_file(tmp_path, negative_strand_gbk_content):
    """Create a GenBank file with negative strand features"""
    gbk_path = tmp_path / "negative.gbk"
    with open(gbk_path, "w") as f:
        f.write(negative_strand_gbk_content)
    return gbk_path


@pytest.fixture
def join_location_gbk_file(tmp_path, join_location_gbk_content):
    """Create a GenBank file with join locations"""
    gbk_path = tmp_path / "join.gbk"
    with open(gbk_path, "w") as f:
        f.write(join_location_gbk_content)
    return gbk_path


@pytest.fixture
def null_qualifier_gbk_file(tmp_path, null_qualifier_gbk_content):
    """Create a GenBank file with null qualifiers"""
    gbk_path = tmp_path / "null.gbk"
    with open(gbk_path, "w") as f:
        f.write(null_qualifier_gbk_content)
    return gbk_path


@pytest.fixture
def minimal_gbk_file_gz(tmp_path, minimal_gbk_content):
    """Create a gzipped GenBank file with minimal content"""
    gbk_path = tmp_path / "minimal.gbk.gz"
    with gzip.open(gbk_path, "wt") as f:
        f.write(minimal_gbk_content)
    return gbk_path


@pytest.fixture
def converted_minimal_db(db_with_tables, minimal_gbk_file):
    """Convert minimal gbk file to database"""
    db.init(str(db_with_tables))
    with db.atomic():
        core.convert_gbk_to_sqlite(str(minimal_gbk_file))
    return db_with_tables


# ===== Test Functions =====


# Tests for iter_gb_records function
def test_iter_gb_records_reads_regular_file(minimal_gbk_file):
    """Test iter_gb_records with a regular GenBank file"""
    records = list(core.iter_gb_records(str(minimal_gbk_file)))
    assert len(records) == 1
    assert records[0].name == "TEST0001"


def test_iter_gb_records_reads_gzipped_file(minimal_gbk_file_gz):
    """Test iter_gb_records with a gzipped GenBank file"""
    records = list(core.iter_gb_records(str(minimal_gbk_file_gz)))
    assert len(records) == 1
    assert records[0].name == "TEST0001"


# Tests for record metadata
def test_convert_gbk_to_sqlite_stores_record_name(converted_minimal_db):
    """Test that the record name is stored correctly"""
    db.init(str(converted_minimal_db))
    name = Record.select().first().name
    assert name == "TEST0001"


def test_convert_gbk_to_sqlite_stores_record_definition(converted_minimal_db):
    """Test that the record definition is stored correctly"""
    db.init(str(converted_minimal_db))
    definition = Record.select().first().definition
    assert "Minimal test sequence." in definition


def test_convert_gbk_to_sqlite_stores_record_accession(converted_minimal_db):
    """Test that the record accession is stored correctly"""
    db.init(str(converted_minimal_db))
    accession = Record.select().first().accession
    assert accession == "TEST0001"


def test_convert_gbk_to_sqlite_stores_record_version(converted_minimal_db):
    """Test that the record version is stored correctly"""
    db.init(str(converted_minimal_db))
    version = Record.select().first().version
    assert version == "TEST0001.1"


# Tests for feature location attributes
def test_convert_gbk_to_sqlite_stores_feature_location_start(converted_minimal_db):
    """Test that the feature start location is stored correctly"""
    db.init(str(converted_minimal_db))
    start = Feature.select().first().location_start
    assert start == 0  # 0-based indexing


def test_convert_gbk_to_sqlite_stores_feature_location_end(converted_minimal_db):
    """Test that the feature end location is stored correctly"""
    db.init(str(converted_minimal_db))
    end = Feature.select().first().location_end
    assert end == 10


def test_convert_gbk_to_sqlite_stores_feature_location_strand_positive(converted_minimal_db):
    """Test that the positive strand is stored correctly"""
    db.init(str(converted_minimal_db))
    strand = Feature.select().first().location_strand
    assert strand == "+"


def test_convert_gbk_to_sqlite_stores_feature_location_strand_negative(
    db_with_tables, negative_strand_gbk_file
):
    """Test that the negative strand is stored correctly"""
    db.init(str(db_with_tables))
    with db.atomic():
        core.convert_gbk_to_sqlite(str(negative_strand_gbk_file))
    strand = Feature.select().first().location_strand
    assert strand == "-"


# Tests for feature qualifiers
def test_convert_gbk_to_sqlite_stores_feature_gene_qualifier(converted_minimal_db):
    """Test that the gene qualifier is stored correctly"""
    db.init(str(converted_minimal_db))
    feature = Feature.select().first()
    gene_qual = (
        Qualifier.select().where((Qualifier.feature == feature) & (Qualifier.key == "gene")).first()
    )
    assert gene_qual is not None
    assert gene_qual.value == "foo"


def test_convert_gbk_to_sqlite_stores_feature_product_qualifier(converted_minimal_db):
    """Test that the product qualifier is stored correctly"""
    db.init(str(converted_minimal_db))
    feature = Feature.select().first()
    product_qual = (
        Qualifier.select()
        .where((Qualifier.feature == feature) & (Qualifier.key == "product"))
        .first()
    )
    assert product_qual is not None
    assert product_qual.value == "bar"


def test_convert_gbk_to_sqlite_stores_multiple_instances_of_same_qualifier(
    db_with_tables, multiqual_gbk_file
):
    """Test that multiple instances of the same qualifier are stored correctly"""
    db.init(str(db_with_tables))
    with db.atomic():
        core.convert_gbk_to_sqlite(str(multiqual_gbk_file))
    feature = Feature.select().first()
    notes = [
        q.value
        for q in Qualifier.select().where(
            (Qualifier.feature == feature) & (Qualifier.key == "note")
        )
    ]
    assert len(notes) == 2
    assert "first note" in notes
    assert "second note" in notes


def test_convert_gbk_to_sqlite_stores_null_qualifier_value(db_with_tables, null_qualifier_gbk_file):
    """Test that null qualifier values are stored correctly"""
    db.init(str(db_with_tables))
    with db.atomic():
        core.convert_gbk_to_sqlite(str(null_qualifier_gbk_file))
    feature = Feature.select().first()
    pseudo_qual = (
        Qualifier.select()
        .where((Qualifier.feature == feature) & (Qualifier.key == "pseudo"))
        .first()
    )
    assert pseudo_qual is not None
    assert pseudo_qual.value is None


# Tests for special cases
def test_convert_gbk_to_sqlite_handles_gzipped_files(db_with_tables, minimal_gbk_file_gz):
    """Test handling of gzipped GenBank files"""
    db.init(str(db_with_tables))
    with db.atomic():
        core.convert_gbk_to_sqlite(str(minimal_gbk_file_gz))
    genome = Genome.select().first()
    assert genome is not None
    assert ".gz" in genome.gbk_path


def test_convert_gbk_to_sqlite_handles_join_locations(db_with_tables, join_location_gbk_file):
    """Test handling of join locations"""
    db.init(str(db_with_tables))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with db.atomic():
            core.convert_gbk_to_sqlite(str(join_location_gbk_file))

        # Check that a warning was issued
        assert len(w) >= 1
        assert "does not have strand attribute" in str(w[0].message)

    # Verify the record was still stored
    record = Record.select().where(Record.name == "TEST0004").first()
    assert record is not None

    # Verify the feature was stored with its qualifiers
    feature = Feature.select().where(Feature.record == record).first()
    assert feature is not None

    # Check that the qualifiers were stored correctly
    gene_qual = (
        Qualifier.select().where((Qualifier.feature == feature) & (Qualifier.key == "gene")).first()
    )
    assert gene_qual.value == "joinfoo"

    product_qual = (
        Qualifier.select()
        .where((Qualifier.feature == feature) & (Qualifier.key == "product"))
        .first()
    )
    assert product_qual.value == "joinbar"


# Tests for Feature methods
def test_feature_get_qualifiers_method(converted_minimal_db):
    """Test the Feature.get_qualifiers method"""
    db.init(str(converted_minimal_db))
    feature = Feature.select().first()
    qualifiers = feature.get_qualifiers()

    # Check that all qualifiers are returned
    assert qualifiers.count() == 2

    # Check that the qualifiers have the correct keys and values
    qualifier_dict = {q.key: q.value for q in qualifiers}
    assert qualifier_dict["gene"] == "foo"
    assert qualifier_dict["product"] == "bar"


# Tests for database relationships
def test_feature_record_relationship(converted_minimal_db):
    """Test that the Feature to Record relationship is correctly established"""
    db.init(str(converted_minimal_db))
    feature = Feature.select().first()
    record = feature.record

    assert record is not None
    assert record.name == "TEST0001"


def test_qualifier_feature_relationship(converted_minimal_db):
    """Test that the Qualifier to Feature relationship is correctly established"""
    db.init(str(converted_minimal_db))
    qualifier = Qualifier.select().first()

    # Get the feature through the database instead of the property
    feature = Feature.get(
        (Feature.genome == qualifier.genome)
        & (Feature.record == qualifier.record)
        & (Feature.feature_index == qualifier.feature_index)
    )

    assert feature is not None
    assert isinstance(feature, Feature)

    # Verify the feature is correctly associated
    assert feature.record.name == "TEST0001"
