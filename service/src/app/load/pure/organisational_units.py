import json
import uuid

import polars as pl
from litestar.types import Logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.load.pure import pure_types
from app.models import OrganisationalUnit

transform_schema_parent = pl.Struct(
    {
        "uuid": pl.String,
    }
)

transform_schema = pl.Schema(
    {
        "uuid": pl.String,
        "pureId": pure_types.pure_id,
        "name": pure_types.text,
        "type": pure_types.classification_type,
        "parents": pl.List(transform_schema_parent),
        "ids": pure_types.ids,
        "raw": pl.String,
    }
)


def transform(organisational_units: list) -> pl.LazyFrame:
    """Transforms organisational units dictionary to a format ready to be loaded to the database"""
    lf = (
        pl.LazyFrame(organisational_units)
        .select(pl.all(), pl.struct(pl.all()).struct.json_encode().alias("raw"))
        .match_to_schema(
            transform_schema,
            extra_columns="ignore",
            extra_struct_fields="ignore",
            missing_columns={
                "parents": pl.lit([], dtype=pl.List(transform_schema_parent)),
                "ids": pl.lit([], dtype=pure_types.ids),
            },
            missing_struct_fields="insert",
        )
        .select(
            pl.col("uuid").alias("organisational_unit_id"),
            pl.col("pureId").alias("pure_id"),
            pl.col("type").struct.field("pureId").alias("type_id"),
            pure_types.parse_text(pl.col("name"), "name").struct.unnest(),
            pl.col("parents").list.eval(pl.element().struct.field("uuid")),
            pure_types.parse_ids(pl.col("ids")),
            pl.col("raw"),
        )
    )
    return lf


def load(
    df: pl.DataFrame, session: Session, logger: Logger | None = None, update_raw=True
):
    """
    Loads organisational units from prepared dataframe into the database
    See `transform_organisational_units`
    """
    for organisational_unit_row in df.rows(named=True):
        organisational_unit = session.scalars(
            select(OrganisationalUnit).where(
                OrganisationalUnit.id
                == organisational_unit_row["organisational_unit_id"]
            )
        ).first()
        if organisational_unit is None:
            organisational_unit = OrganisationalUnit(
                id=uuid.UUID(organisational_unit_row["organisational_unit_id"]),
            )

        organisational_unit.pure_id = organisational_unit_row["pure_id"]
        organisational_unit.type_id = organisational_unit_row["type_id"]
        organisational_unit.name_ru = organisational_unit_row["name_ru"]
        organisational_unit.name_en = organisational_unit_row["name_en"]
        organisational_unit.parents = organisational_unit_row["parents"]
        organisational_unit.ids = organisational_unit_row["ids"]

        if update_raw:
            organisational_unit.raw = json.loads(organisational_unit_row["raw"])
        elif organisational_unit.raw is None:
            organisational_unit.raw = json.loads(organisational_unit_row["raw"])

        session.merge(organisational_unit)
