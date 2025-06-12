from peewee import (
    Model,
    SqliteDatabase,
    AutoField,
    CharField,
    IntegerField,
    ForeignKeyField,
    TextField,
    CompositeKey,
)

# The database instance will be initialized in the main script
db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class Genome(BaseModel):
    id = AutoField()
    gbk_path = CharField(unique=True)


class Record(BaseModel):
    id = AutoField()
    genome = ForeignKeyField(Genome, backref="records", on_delete="CASCADE")
    name = CharField()
    definition = TextField(null=True)
    accession = CharField(null=True)
    version = CharField(null=True)


class Feature(BaseModel):
    genome = ForeignKeyField(Genome, backref="features", on_delete="CASCADE")
    record = ForeignKeyField(Record, backref="features", on_delete="CASCADE")
    feature_index = IntegerField()  # index of the feature within the record
    location_start = IntegerField(null=True)
    location_end = IntegerField(null=True)
    location_strand = CharField(null=True)

    class Meta:
        primary_key = CompositeKey("genome", "record", "feature_index")

    def get_qualifiers(self):
        """Get all qualifiers associated with this feature."""
        return Qualifier.select().where(
            (Qualifier.genome == self.genome)
            & (Qualifier.record == self.record)
            & (Qualifier.feature_index == self.feature_index)
        )


class Qualifier(BaseModel):
    genome = ForeignKeyField(Genome, backref="qualifiers", on_delete="CASCADE")
    record = ForeignKeyField(Record, backref="qualifiers", on_delete="CASCADE")
    feature_index = IntegerField()
    key = CharField()
    value = TextField(null=True)

    class Meta:
        indexes = ((("genome", "record", "feature_index", "key"), False),)

    @property
    def feature(self):
        """Get the associated Feature instance using the composite key."""
        return Feature.get(
            (Feature.genome == self.genome)
            & (Feature.record == self.record)
            & (Feature.feature_index == self.feature_index)
        )


# Add a FieldProxy to enable querying using Qualifier.feature in where clauses
# This is needed for expressions like: Qualifier.select().where(Qualifier.feature == some_feature)
class FeatureFieldProxy:
    def __eq__(self, other):
        if isinstance(other, Feature):
            return (
                (Qualifier.genome == other.genome)
                & (Qualifier.record == other.record)
                & (Qualifier.feature_index == other.feature_index)
            )
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Feature):
            return (
                (Qualifier.genome != other.genome)
                | (Qualifier.record != other.record)
                | (Qualifier.feature_index != other.feature_index)
            )
        return NotImplemented


# Add the field proxy as a class attribute to enable its use in queries
Qualifier.feature = FeatureFieldProxy()
