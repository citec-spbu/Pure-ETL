import json
from typing import Any
from uuid import UUID

import polars as pl
from litestar.types import Logger
from psycopg2.extras import DateTimeTZRange
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.load.pure import pure_types
from app.models import (
    OrganisationalUnit,
    Person,
    PersonOrganisationalUnitStaffAssociation,
    PersonOrganisationalUnitStudentAssociation,
)

transform_schema_association = pl.Struct(
    {
        "organisationalUnit": pl.Struct(
            {
                "uuid": pl.String,
            }
        ),
        "period": pl.Struct(
            {
                "startDate": pl.String,
                "endDate": pl.String,
            }
        ),
    }
)


def parse_association(expr: pl.Expr) -> pl.Expr:
    return expr.list.eval(
        pl.struct(
            unit_id=pl.element()
            .struct.field("organisationalUnit")
            .struct.field("uuid"),
            period=pl.element().struct.field("period"),
        )
    )


transform_schema = pl.Schema(
    {
        "uuid": pl.String,
        "pureId": pure_types.pure_id,
        "name": pl.Struct(
            {
                "firstName": pl.String,
                "lastName": pl.String,
            }
        ),
        "orcid": pl.String,
        "ids": pure_types.ids,
        "titles": pure_types.titles,
        "staffOrganisationAssociations": pl.List(transform_schema_association),
        "studentOrganisationAssociations": pl.List(transform_schema_association),
        "raw": pl.String,
    }
)


def transform(persons: list[Any]) -> pl.LazyFrame:
    """Transforms persons dictionary to a format ready to be loaded to the database"""
    lf = (
        pl.LazyFrame(persons)
        .select(pl.all(), pl.struct(pl.all()).struct.json_encode().alias("raw"))
        .match_to_schema(
            transform_schema,
            extra_columns="ignore",
            extra_struct_fields="ignore",
            missing_columns={
                "staffOrganisationAssociations": pl.lit(
                    [], dtype=pl.List(transform_schema_association)
                ),
                "studentOrganisationAssociations": pl.lit(
                    [], dtype=pl.List(transform_schema_association)
                ),
                "ids": pl.lit([], dtype=pure_types.ids),
                "titles": pl.lit([], dtype=pure_types.titles),
                "orcid": pl.lit(None, dtype=pl.String),
            },
            missing_struct_fields="insert",
        )
        .select(
            pl.col("uuid").alias("person_id"),
            pl.col("pureId").alias("pure_id"),
            pl.col("name").struct.field("firstName").alias("first_name"),
            pl.col("name").struct.field("lastName").alias("last_name"),
            pl.col("orcid"),
            pure_types.parse_ids(pl.col("ids")),
            pure_types.parse_titles(pl.col("titles")),
            parse_association(pl.col("staffOrganisationAssociations")).alias(
                "staff_unit"
            ),
            parse_association(pl.col("studentOrganisationAssociations")).alias(
                "student_unit"
            ),
            pl.col("raw"),
        )
    )
    return lf


def load(
    df: pl.DataFrame, session: Session, logger: Logger | None = None, update_raw=True
):
    """
    Loads persons from prepared dataframe into the database
    See `transform_persons`
    """
    for person_row in df.rows(named=True):
        person = session.scalars(
            select(Person).where(Person.id == person_row["person_id"])
        ).first()
        if person is None:
            person = Person(
                id=UUID(person_row["person_id"]),
            )

        person.pure_id = person_row["pure_id"]
        person.first_name = person_row["first_name"]
        person.last_name = person_row["last_name"]
        person.orcid = person_row["orcid"]
        person.ids = person_row["ids"]
        person.titles = person_row["titles"]

        if update_raw:
            person.raw = json.loads(person_row["raw"])
        elif person.raw is None:
            person.raw = json.loads(person_row["raw"])

        requested_staff_associations = (
            {}
            if person_row["staff_unit"] is None
            else {UUID(unit["unit_id"]): unit for unit in person_row["staff_unit"]}
        )
        requested_student_associations = (
            {}
            if person_row["student_unit"] is None
            else {UUID(unit["unit_id"]): unit for unit in person_row["student_unit"]}
        )

        requested_staff_unit_ids = set(requested_staff_associations.keys())
        requested_student_unit_ids = set(requested_student_associations.keys())

        found_requested_staff_unit_ids = set(
            session.scalars(
                select(OrganisationalUnit.id).where(
                    OrganisationalUnit.id.in_(requested_staff_unit_ids)
                )
            ).all()
        )
        found_requested_student_unit_ids = set(
            session.scalars(
                select(OrganisationalUnit.id).where(
                    OrganisationalUnit.id.in_(requested_student_unit_ids)
                )
            ).all()
        )

        if logger is not None:
            for id in requested_staff_unit_ids.difference(
                found_requested_staff_unit_ids
            ):
                logger.warning(
                    f"Could not assign person {person_row["person_id"]} to unit {id} as staff, unit does not exist"
                )
            for id in requested_student_unit_ids.difference(
                found_requested_student_unit_ids
            ):
                logger.warning(
                    f"Could not assign person {person_row["person_id"]} to unit {id} as student, unit does not exist"
                )

        person_staff_associations_to_remove = []
        person_student_associations_to_remove = []

        for association in person.staff_organisation_associations:
            if association.organisational_unit_id not in found_requested_staff_unit_ids:
                person_staff_associations_to_remove.append(association)
        for association in person.student_organisation_associations:
            if (
                association.organisational_unit_id
                not in found_requested_student_unit_ids
            ):
                person_student_associations_to_remove.append(association)

        for association in person_staff_associations_to_remove:
            person.staff_organisation_associations.remove(association)
        for association in person_student_associations_to_remove:
            person.student_organisation_associations.remove(association)

        person_staff_unit_ids = set(
            association.organisational_unit_id
            for association in person.staff_organisation_associations
        )
        person_student_unit_ids = set(
            association.organisational_unit_id
            for association in person.student_organisation_associations
        )

        for unit_id in found_requested_staff_unit_ids.difference(person_staff_unit_ids):
            period = requested_staff_associations[unit_id]["period"]
            association = PersonOrganisationalUnitStaffAssociation(
                person_id=person.id,
                organisational_unit_id=unit_id,
            )
            if period is not None:
                association.period = DateTimeTZRange(
                    lower=period["startDate"], upper=period["endDate"]
                )
            person.staff_organisation_associations.append(association)
        for unit_id in found_requested_student_unit_ids.difference(
            person_student_unit_ids
        ):
            period = requested_student_associations[unit_id]["period"]
            association = PersonOrganisationalUnitStudentAssociation(
                person_id=person.id,
                organisational_unit_id=unit_id,
            )
            if period is not None:
                association.period = DateTimeTZRange(
                    lower=period["startDate"], upper=period["endDate"]
                )
            person.student_organisation_associations.append(association)

        session.merge(person)
