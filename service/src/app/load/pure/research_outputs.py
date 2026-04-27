import json
import uuid

import polars as pl
from litestar.types import Logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.load.pure import pure_types
from app.models import ResearchOutput

transform_schema = pl.Schema(
    {
        "uuid": pl.String,
        "pureId": pure_types.pure_id,
        "type": pure_types.classification_type,
        "category": pure_types.classification_type,
        "language": pure_types.classification_type,
        "title": pl.Struct(
            {
                "value": pl.String,
                "formatted": pl.Boolean,
            }
        ),
        "raw": pl.String,
    }
)


def transform(research_outputs: list) -> pl.LazyFrame:
    """Transforms research outputs dictionary to a format ready to be loaded to the database"""
    lf = (
        pl.LazyFrame(research_outputs)
        .select(pl.all(), pl.struct(pl.all()).struct.json_encode().alias("raw"))
        .match_to_schema(
            transform_schema,
            extra_columns="ignore",
            extra_struct_fields="ignore",
            missing_columns={},
            missing_struct_fields="insert",
        )
        .select(
            pl.col("uuid").alias("research_output_id"),
            pl.col("pureId").alias("pure_id"),
            pure_types.parse_classification_type(pl.col("type")),
            pure_types.parse_classification_type(pl.col("category")).alias(
                "category_type_id"
            ),
            pure_types.parse_classification_type(pl.col("language")).alias(
                "language_type_id"
            ),
            pl.col("title").struct.field("value").alias("title"),
            pl.col("raw"),
        )
    )
    return lf


def load(
    df: pl.DataFrame, session: Session, logger: Logger | None = None, update_raw=True
):
    """
    Loads research outputs from prepared dataframe into the database
    See `transform`
    """
    for research_output_row in df.rows(named=True):
        research_output = session.scalars(
            select(ResearchOutput).where(
                ResearchOutput.id == research_output_row["research_output_id"]
            )
        ).first()
        if research_output is None:
            research_output = ResearchOutput(
                id=uuid.UUID(research_output_row["research_output_id"]),
            )

        research_output.pure_id = research_output_row["pure_id"]
        research_output.type_id = research_output_row["type_id"]
        research_output.category_type_id = research_output_row["category_type_id"]
        research_output.language_type_id = research_output_row["language_type_id"]
        research_output.title = research_output_row["title"]

        if update_raw or research_output.raw is None:
            research_output.raw = json.loads(research_output_row["raw"])

        session.merge(research_output)
