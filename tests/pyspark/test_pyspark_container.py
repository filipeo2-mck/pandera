"""Unit tests for pyspark container."""

from contextlib import nullcontext as does_not_raise
from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.types as T
import pytest
import pandera.pyspark as pa
import pandera.errors
from pandera.config import PanderaConfig, ValidationDepth
from pandera.pyspark import DataFrameSchema, Column

spark = SparkSession.builder.getOrCreate()


def test_pyspark_dataframeschema():
    """
    Test creating a pyspark DataFrameSchema object
    """

    schema = DataFrameSchema(
        {
            "name": Column(T.StringType()),
            "age": Column(T.IntegerType(), coerce=True, nullable=True),
        }
    )

    data = [("Neeraj", 35), ("Jask", 30)]

    df = spark.createDataFrame(data=data, schema=["name", "age"])
    df_out = schema.validate(df)

    assert df_out.pandera.errors is not None

    data = [("Neeraj", "35"), ("Jask", "a")]

    df2 = spark.createDataFrame(data=data, schema=["name", "age"])

    df_out = schema.validate(df2)

    assert not df_out.pandera.errors


def test_pyspark_dataframeschema_with_alias_types(
    config_params: PanderaConfig,
):
    """
    Test creating a pyspark DataFrameSchema object
    """

    schema = DataFrameSchema(
        columns={
            "product": Column("str", checks=pa.Check.str_startswith("B")),
            "price": Column("int", checks=pa.Check.gt(5)),
        },
        name="product_schema",
        description="schema for product info",
        title="ProductSchema",
    )

    data = [("Bread", 9), ("Butter", 15)]

    spark_schema = T.StructType(
        [
            T.StructField("product", T.StringType(), False),
            T.StructField("price", T.IntegerType(), False),
        ],
    )

    df = spark.createDataFrame(data=data, schema=spark_schema)

    df_out = schema.validate(df)

    assert not df_out.pandera.errors
    if config_params.validation_depth in [
        ValidationDepth.SCHEMA_AND_DATA,
        ValidationDepth.DATA_ONLY,
    ]:
        with pytest.raises(pandera.errors.PysparkSchemaError):
            data_fail = [("Bread", 3), ("Butter", 15)]

            df_fail = spark.createDataFrame(
                data=data_fail, schema=spark_schema
            )

            fail_df = schema.validate(df_fail)
            if fail_df.pandera.errors:
                raise pandera.errors.PysparkSchemaError


def test_pyspark_column_metadata():
    """
    Test creating a pyspark Column object with metadata
    """

    schema = DataFrameSchema(
        columns={
            "product": Column(
                "str",
                checks=pa.Check.str_startswith("B"),
                metadata={"usecase": "product_pricing", "type": ["t1", "t2"]},
            ),
            "price": Column("int", checks=pa.Check.gt(5)),
        },
        name="product_schema",
        description="schema for product info",
        title="ProductSchema",
        metadata={"category": "product"},
    )

    expected = {
        "product_schema": {
            "columns": {
                "product": {
                    "usecase": "product_pricing",
                    "type": ["t1", "t2"],
                },
                "price": None,
            },
            "dataframe": {"category": "product"},
        }
    }

    assert schema.get_metadata() == expected


def test_pyspark_sample():
    """
    Test the sample functionality of pyspark
    """

    schema = DataFrameSchema(
        columns={
            "product": Column("str", checks=pa.Check.str_startswith("B")),
            "price": Column("int", checks=pa.Check.gt(5)),
        },
        name="product_schema",
        description="schema for product info",
        title="ProductSchema",
    )

    data = [
        ("Bread", 9),
        ("Butter", 15),
        ("Ice Cream", 10),
        ("Cola", 12),
        ("Chocolate", 7),
    ]

    spark_schema = T.StructType(
        [
            T.StructField("product", T.StringType(), False),
            T.StructField("price", T.IntegerType(), False),
        ],
    )

    df = spark.createDataFrame(data=data, schema=spark_schema)

    df_out = schema.validate(df, sample=0.5)

    assert isinstance(df_out, DataFrame)


def test_pyspark_regex_column():
    """
    Test creating a pyspark DataFrameSchema object with regex columns
    """

    schema = DataFrameSchema(
        {
            # Columns with all caps names must have string values
            "[A-Z]+": Column(T.StringType(), regex=True),
        }
    )

    data = [("Neeraj", 35), ("Jask", 30)]

    df = spark.createDataFrame(data=data, schema=["NAME", "AGE"])
    df_out = schema.validate(df)

    assert df_out.pandera.errors is not None

    data = [("Neeraj", "35"), ("Jask", "a")]

    df2 = spark.createDataFrame(data=data, schema=["NAME", "AGE"])

    df_out = schema.validate(df2)

    assert not df_out.pandera.errors


def test_pyspark_nullable():
    """
    Test the nullable functionality of pyspark
    """

    data = [
        ("Bread", 9),
        ("Butter", 15),
        ("Ice Cream", None),
        ("Cola", 12),
        ("Chocolate", None),
    ]
    spark_schema = T.StructType(
        [
            T.StructField("product", T.StringType(), False),
            T.StructField("price", T.IntegerType(), True),
        ],
    )
    df = spark.createDataFrame(data=data, schema=spark_schema)

    # Check for `nullable=False`
    schema_nullable_false = DataFrameSchema(
        columns={
            "product": Column("str"),
            "price": Column("int", nullable=False),
        },
    )
    with does_not_raise():
        df_out = schema_nullable_false.validate(df)
    assert isinstance(df_out, DataFrame)
    assert "SERIES_CONTAINS_NULLS" in str(dict(df_out.pandera.errors))

    # Check for `nullable=True`
    schema_nullable_true = DataFrameSchema(
        columns={
            "product": Column("str"),
            "price": Column("int", nullable=True),
        },
    )
    with does_not_raise():
        df_out = schema_nullable_true.validate(df)
    assert isinstance(df_out, DataFrame)
    assert df_out.pandera.errors == {}


@pytest.fixture(scope="module")
def schema_with_datatypes():
    """
    Model containing all common datatypes for PySpark namespace.
    """
    schema = DataFrameSchema(
        {
            "non_nullable": Column(T.IntegerType(), nullable=False),
            "binary": Column(T.BinaryType()),
            "byte": Column(T.ByteType()),
            "text": Column(T.StringType()),
            "integer": Column(T.IntegerType()),
            "long": Column(T.LongType()),
            "float": Column(T.FloatType()),
            "double": Column(T.DoubleType()),
            "boolean": Column(T.BooleanType()),
            "decimal": Column(T.DecimalType()),
            "date": Column(T.DateType()),
            "timestamp": Column(T.TimestampType()),
            "timestamp_ntz": Column(T.TimestampNTZType()),
            "array": Column(T.ArrayType(T.StringType())),
            "map": Column(T.MapType(T.StringType(), T.IntegerType())),
        }
    )

    return schema


def test_schema_to_structtype(schema_with_datatypes):
    """
    Test the conversion from a schema to a StructType object through `to_structtype()`.
    """

    assert schema_with_datatypes.to_structtype() == T.StructType(
        [
            T.StructField(
                name="non_nullable", dataType=T.IntegerType(), nullable=True
            ),
            T.StructField(
                name="binary", dataType=T.BinaryType(), nullable=True
            ),
            T.StructField(name="byte", dataType=T.ByteType(), nullable=True),
            T.StructField(name="text", dataType=T.StringType(), nullable=True),
            T.StructField(
                name="integer", dataType=T.IntegerType(), nullable=True
            ),
            T.StructField(name="long", dataType=T.LongType(), nullable=True),
            T.StructField(name="float", dataType=T.FloatType(), nullable=True),
            T.StructField(
                name="double", dataType=T.DoubleType(), nullable=True
            ),
            T.StructField(
                name="boolean", dataType=T.BooleanType(), nullable=True
            ),
            T.StructField(
                name="decimal", dataType=T.DecimalType(), nullable=True
            ),
            T.StructField(name="date", dataType=T.DateType(), nullable=True),
            T.StructField(
                name="timestamp", dataType=T.TimestampType(), nullable=True
            ),
            T.StructField(
                name="timestamp_ntz", dataType=T.TimestampType(), nullable=True
            ),
            T.StructField(
                name="array",
                dataType=T.ArrayType(T.StringType()),
                nullable=True,
            ),
            T.StructField(
                name="map",
                dataType=T.MapType(T.StringType(), T.IntegerType()),
                nullable=True,
            ),
        ]
    )


def test_schema_to_ddl(schema_with_datatypes):
    """
    Test the conversion from a schema to a DDL string through `to_ddl()`.
    """

    assert schema_with_datatypes.to_ddl() == ",".join(
        [
            "non_nullable INT",
            "binary BINARY",
            "byte TINYINT",
            "text STRING",
            "integer INT",
            "long BIGINT",
            "float FLOAT",
            "double DOUBLE",
            "boolean BOOLEAN",
            "decimal DECIMAL(10,0)",
            "date DATE",
            "timestamp TIMESTAMP",
            "timestamp_ntz TIMESTAMP",
            "array ARRAY<STRING>",
            "map MAP<STRING, INT>",
        ]
    )
