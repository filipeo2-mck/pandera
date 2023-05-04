"""Unit tests for pyspark container."""
from typing import Union

from pyspark.sql import SparkSession
import pyspark.sql.types as T
import pyspark.sql.functions as F
import pytest
import pandera.pyspark as pa
import pandera.errors
from pandera.pyspark import DataFrameSchema, Column
from pandera.errors import SchemaErrors

spark = SparkSession.builder.getOrCreate()


def test_pyspark_dataframeschema():
    """
    Test creating a pyspark DataFrameSchema object
    """

    schema = DataFrameSchema(
        {
            "name": Column(T.StringType()),
            "age": Column(T.IntegerType(), coerce=True),
        }
    )

    data = [("Neeraj", 35), ("Jask", 30)]

    df = spark.createDataFrame(data=data, schema=["name", "age"])
    df_out = schema.report_errors(df)

    assert df_out.pandera.errors != None

    data = [("Neeraj", "35"), ("Jask", "a")]

    df2 = spark.createDataFrame(data=data, schema=["name", "age"])

    df_out = schema.report_errors(df2)

    assert not df_out.pandera.errors


def test_pyspark_dataframeschema_with_alias_types():
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

    df_out = schema.report_errors(df)

    assert not df_out.pandera.errors

    with pytest.raises(pandera.errors.PysparkSchemaError):
        data_fail = [("Bread", 3), ("Butter", 15)]

        df_fail = spark.createDataFrame(data=data_fail, schema=spark_schema)

        fail_df = schema.report_errors(df_fail)
        if fail_df.pandera.errors:
            raise pandera.errors.PysparkSchemaError
