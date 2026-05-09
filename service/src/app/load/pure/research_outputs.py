import json
from uuid import UUID

import polars as pl
from litestar.types import Logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.load.pure import pure_types
from app.models import (
    OrganisationalUnit,
    Person,
    ResearchOutput,
    ResearchOutputOrganisationalUnitAssociation,
    ResearchOutputPersonAssociation,
)

transform_schema_person_association = pl.Struct(
    {
        "pureId": pure_types.pure_id,
        "person": pl.Struct(
            {
                "uuid": pl.String,
            }
        ),
        "externalPerson": pl.Struct(
            {
                "uuid": pl.String,
            }
        ),
        "personRole": pure_types.classification_type,
    }
)


def parse_person_association(expr: pl.Expr) -> pl.Expr:
    """Removes external persons"""
    return expr.list.filter(pl.element().struct.field("person").is_not_null()).list.eval(
        pl.struct(
            pure_id=pl.element().struct.field("pureId"),
            person_id=pl.element().struct.field("person").struct.field("uuid"),
            person_role_type_id=pure_types.parse_classification_type(pl.element().struct.field("personRole")),
        )
    )


def parse_external_person_association(expr: pl.Expr) -> pl.Expr:
    """Removes persons"""
    return expr.list.filter(pl.element().struct.field("externalPerson").is_not_null()).list.eval(
        pl.struct(
            pure_id=pl.element().struct.field("pureId"),
            person_id=pl.element().struct.field("externalPerson").struct.field("uuid"),
            person_role_type_id=pure_types.parse_classification_type(pl.element().struct.field("personRole")),
        )
    )


transform_schema_organisational_unit_association = pl.Struct(
    {
        "uuid": pl.String,
    }
)

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
        "personAssociations": pl.List(transform_schema_person_association),
        "organisationalUnits": pl.List(transform_schema_organisational_unit_association),
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
            missing_columns={
                "personAssociations": pl.lit([], dtype=pl.List(transform_schema_person_association)),
                "organisationalUnits": pl.lit([], dtype=pl.List(transform_schema_organisational_unit_association)),
            },
            missing_struct_fields="insert",
        )
        .select(
            pl.col("uuid").alias("research_output_id"),
            pl.col("pureId").alias("pure_id"),
            pure_types.parse_classification_type(pl.col("type")),
            pure_types.parse_classification_type(pl.col("category")).alias("category_type_id"),
            pure_types.parse_classification_type(pl.col("language")).alias("language_type_id"),
            parse_person_association(pl.col("personAssociations")).alias("person_associations"),
            parse_external_person_association(pl.col("personAssociations")).alias("external_person_associations"),
            pl.col("organisationalUnits")
            .list.eval(pl.element().struct.field("uuid"))
            .alias("organisational_unit_associations"),
            pl.col("title").struct.field("value").alias("title"),
            pl.col("raw"),
        )
    )
    return lf


def load(df: pl.DataFrame, session: Session, logger: Logger | None = None, update_raw=True):
    """
    Loads research outputs from prepared dataframe into the database
    See `transform`
    """
    for research_output_row in df.rows(named=True):
        if logger is not None:
            logger.debug(f"Loading research output {research_output_row['research_output_id']}")

        research_output = session.scalars(
            select(ResearchOutput).where(ResearchOutput.id == research_output_row["research_output_id"])
        ).first()
        if research_output is None:
            research_output = ResearchOutput(
                id=UUID(research_output_row["research_output_id"]),
            )

        research_output.pure_id = research_output_row["pure_id"]
        research_output.type_id = research_output_row["type_id"]
        research_output.category_type_id = research_output_row["category_type_id"]
        research_output.language_type_id = research_output_row["language_type_id"]
        research_output.title = research_output_row["title"]

        if update_raw or research_output.raw is None:
            research_output.raw = json.loads(research_output_row["raw"])

        # Create links

        requested_person_associations = (
            {}
            if research_output_row["person_associations"] is None
            else {UUID(person["person_id"]): person for person in research_output_row["person_associations"]}
        )

        requested_organisational_unit_associations = (
            set()
            if research_output_row["organisational_unit_associations"] is None
            else set(research_output_row["organisational_unit_associations"])
        )

        requested_person_ids = set(requested_person_associations.keys())
        requested_organisational_unit_ids = requested_organisational_unit_associations

        found_requested_person_ids = set(
            session.scalars(select(Person.id).where(Person.id.in_(requested_person_ids))).all()
        )
        found_requested_organisational_unit_ids = set(
            session.scalars(
                select(OrganisationalUnit.id).where(OrganisationalUnit.id.in_(requested_organisational_unit_ids))
            ).all()
        )

        if logger is not None:
            log_id = research_output_row["research_output_id"]
            for person_id in requested_person_ids.difference(found_requested_person_ids):
                logger.warning(
                    f"Could not assign research_output {log_id} to person {person_id}, person does not exist"
                )
            for unit_id in requested_organisational_unit_ids.difference(found_requested_organisational_unit_ids):
                logger.warning(f"Could not assign research_output {log_id} to unit {unit_id}, unit does not exist")

        person_associations_to_remove: list[ResearchOutputPersonAssociation] = []
        organisational_unit_associations_to_remove: list[ResearchOutputOrganisationalUnitAssociation] = []

        for association in research_output.person_associations:
            if association.person_id not in found_requested_person_ids:
                person_associations_to_remove.append(association)
        for association in research_output.organisational_unit_associations:
            if association.organisational_unit_id not in found_requested_organisational_unit_ids:
                organisational_unit_associations_to_remove.append(association)

        for association in person_associations_to_remove:
            if logger is not None:
                logger.debug(f"Removing association with person {association.person_id}")
            research_output.person_associations.remove(association)
        for association in organisational_unit_associations_to_remove:
            if logger is not None:
                logger.debug(f"Removing association with organisational_unit {association.organisational_unit_id}")
            research_output.organisational_unit_associations.remove(association)

        research_output_person_ids = set(association.person_id for association in research_output.person_associations)
        research_output_organisational_unit_ids = set(
            association.organisational_unit_id for association in research_output.organisational_unit_associations
        )

        for person_id in found_requested_person_ids.difference(research_output_person_ids):
            if logger is not None:
                logger.debug(f"Adding association with person {person_id}")
            pure_id = requested_person_associations[person_id]["pure_id"]
            person_role_type_id = requested_person_associations[person_id]["person_role_type_id"]
            association = ResearchOutputPersonAssociation(
                research_output_id=research_output.id,
                person_id=person_id,
                pure_id=pure_id,
                person_role_type_id=person_role_type_id,
            )
            research_output.person_associations.append(association)
        for unit_id in found_requested_organisational_unit_ids.difference(research_output_organisational_unit_ids):
            if logger is not None:
                logger.debug(f"Adding association with organisational_unit {unit_id}")
            association = ResearchOutputOrganisationalUnitAssociation(
                research_output_id=research_output.id,
                organisational_unit_id=unit_id,
            )
            research_output.organisational_unit_associations.append(association)

        session.merge(research_output)
