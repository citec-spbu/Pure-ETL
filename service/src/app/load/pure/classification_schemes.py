import json
from uuid import UUID

import polars as pl
from litestar.types import Logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.load.pure import pure_types
from app.models import Classification, ClassificationScheme

transform_schema_classification = pl.Struct(
    {
        "pureId": pure_types.pure_id,
        "uri": pl.String,
        "term": pure_types.text,
        "disabled": pl.Boolean,
    }
)

transform_schema = pl.Schema(
    {
        "uuid": pl.String,
        "pureId": pure_types.pure_id,
        "baseUri": pl.String,
        "description": pure_types.text,
        "containedClassifications": pl.List(transform_schema_classification),
        "raw": pl.String,
    }
)


def transform(classification_schemes: list) -> pl.LazyFrame:
    """Transforms classification schemes dictionary to a format ready to be loaded to the database"""
    lf = (
        pl.LazyFrame(classification_schemes)
        .select(pl.all(), pl.struct(pl.all()).struct.json_encode().alias("raw"))
        .match_to_schema(
            transform_schema,
            extra_columns="ignore",
            extra_struct_fields="ignore",
            missing_columns={"containedClassifications": pl.lit([], dtype=pl.List(transform_schema_classification))},
            missing_struct_fields="insert",
        )
        .select(
            pl.col("uuid").alias("classification_scheme_id"),
            pl.col("pureId").alias("pure_id"),
            pl.col("baseUri").alias("base_uri"),
            pure_types.parse_text(pl.col("description"), "description").struct.unnest(),
            pl.col("containedClassifications")
            .list.eval(
                pl.struct(
                    pl.element().struct.field("pureId").alias("pure_id"),
                    pl.element().struct.field("uri"),
                    pl.element().struct.field("disabled"),
                    pure_types.parse_text(pl.element().struct.field("term"), "term").struct.unnest(),
                )
            )
            .alias("classifications"),
            pl.col("raw"),
        )
    )
    return lf


def load(df: pl.DataFrame, session: Session, logger: Logger | None = None, update_raw=True):
    """
    Loads classification schemes from prepared dataframe into the database
    See `transform`
    """

    def update_classification_scheme(classification_scheme, classification_scheme_row):
        classification_scheme.pure_id = classification_scheme_row["pure_id"]
        classification_scheme.base_uri = classification_scheme_row["base_uri"]
        classification_scheme.description_ru = classification_scheme_row["description_ru"]
        classification_scheme.description_en = classification_scheme_row["description_en"]

        if update_raw or classification_scheme.raw is None:
            classification_scheme.raw = json.loads(classification_scheme_row["raw"])

    def update_classification(classification, classification_scheme, classification_row):
        classification.uri = classification_row["uri"]
        classification.term_ru = classification_row["term_ru"]
        classification.term_en = classification_row["term_en"]
        classification.disabled = classification_row["disabled"]
        classification.classification_scheme_id = classification_scheme.id

    for classification_scheme_row in df.rows(named=True):
        if logger is not None:
            logger.debug(f"Loading classification_scheme {classification_scheme_row['classification_scheme_id']}")

        classification_scheme = session.scalars(
            select(ClassificationScheme).where(
                ClassificationScheme.id == classification_scheme_row["classification_scheme_id"]
            )
        ).first()
        if classification_scheme is None:
            classification_scheme = ClassificationScheme(
                id=UUID(classification_scheme_row["classification_scheme_id"]),
            )
            update_classification_scheme(classification_scheme, classification_scheme_row)
            session.add(classification_scheme)
        else:
            update_classification_scheme(classification_scheme, classification_scheme_row)

        classifications = classification_scheme_row["classifications"]
        if classifications is not None:
            found_classifications = {
                classification.pure_id: classification
                for classification in session.scalars(
                    select(Classification).where(
                        Classification.pure_id.in_([classification["pure_id"] for classification in classifications])
                    )
                ).all()
            }
            for classification_row in classifications:
                if logger is not None:
                    logger.debug(f"Loading classification {classification_row['pure_id']}")
                classification = found_classifications.get(classification_row["pure_id"])
                if classification is None:
                    classification = Classification(pure_id=classification_row["pure_id"])
                    update_classification(classification, classification_scheme, classification_row)
                    session.add(classification)
                else:
                    update_classification(classification, classification_scheme, classification_row)
