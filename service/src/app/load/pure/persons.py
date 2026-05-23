import json
from datetime import datetime
from typing import Any
from uuid import UUID

import polars as pl
from litestar.types import Logger
from psycopg2.extras import DateTimeTZRange
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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
        "pureId": pure_types.pure_id,
    }
)


def parse_association(expr: pl.Expr) -> pl.Expr:
    return expr.list.eval(
        pl.struct(
            pure_id=pl.element().struct.field("pureId"),
            unit_id=pl.element().struct.field("organisationalUnit").struct.field("uuid"),
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
                "staffOrganisationAssociations": pl.lit([], dtype=pl.List(transform_schema_association)),
                "studentOrganisationAssociations": pl.lit([], dtype=pl.List(transform_schema_association)),
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
            parse_association(pl.col("staffOrganisationAssociations")).alias("staff_unit"),
            parse_association(pl.col("studentOrganisationAssociations")).alias("student_unit"),
            pl.col("raw"),
        )
    )
    return lf


def load(df: pl.DataFrame, session: Session, logger: Logger | None = None, update_raw=True):
    """
    Loads persons from prepared dataframe into the database
    See `transform`
    """

    rows = df.rows(named=True)

    def update_person(person, person_row):
        person.pure_id = person_row["pure_id"]
        person.first_name = person_row["first_name"]
        person.last_name = person_row["last_name"]
        person.orcid = person_row["orcid"]
        person.ids = person_row["ids"]
        person.titles = person_row["titles"]

        if update_raw or person.raw is None:
            person.raw = json.loads(person_row["raw"])

    person_ids = [person_row["person_id"] for person_row in rows]

    found_persons = {
        person.id: person
        for person in session.scalars(
            select(Person)
            .where(Person.id.in_(person_ids))
            .options(
                selectinload(Person.staff_organisation_associations),
                selectinload(Person.student_organisation_associations),
            )
        ).all()
    }

    for person_row in rows:
        if logger is not None:
            logger.debug(f"Loading person {person_row['person_id']}")

        person = found_persons.get(UUID(person_row["person_id"]))
        if person is None:
            person = Person(
                id=UUID(person_row["person_id"]),
            )
            update_person(person, person_row)
            session.add(person)
        else:
            update_person(person, person_row)

        # Create links

        requested_staff_associations: dict[int, dict] = (
            {}
            if person_row["staff_unit"] is None
            else {association["pure_id"]: association for association in person_row["staff_unit"]}
        )
        requested_student_associations: dict[int, dict] = (
            {}
            if person_row["student_unit"] is None
            else {association["pure_id"]: association for association in person_row["student_unit"]}
        )

        requested_staff_association_ids = set(requested_staff_associations.keys())
        requested_student_association_ids = set(requested_student_associations.keys())

        requested_staff_unit_ids = set(association["unit_id"] for association in requested_staff_associations.values())
        requested_student_unit_ids = set(
            association["unit_id"] for association in requested_student_associations.values()
        )

        requested_unit_ids = requested_staff_unit_ids.union(requested_student_unit_ids)

        found_requested_unit_ids = set(
            session.scalars(select(OrganisationalUnit.id).where(OrganisationalUnit.id.in_(requested_unit_ids))).all()
        )

        found_units_requested_staff_association_ids = set(
            association["pure_id"]
            for association in requested_staff_associations.values()
            if UUID(association["unit_id"]) in found_requested_unit_ids
        )
        found_units_requested_student_association_ids = set(
            association["pure_id"]
            for association in requested_student_associations.values()
            if UUID(association["unit_id"]) in found_requested_unit_ids
        )

        if logger is not None:
            for unit_id in requested_staff_unit_ids.difference(found_requested_unit_ids):
                logger.warning(
                    f"Could not add person {person_row['person_id']} to unit {unit_id} as staff, unit does not exist"
                )
            for unit_id in requested_student_unit_ids.difference(found_requested_unit_ids):
                logger.warning(
                    f"Could not add person {person_row['person_id']} to unit {unit_id} as student, unit does not exist"
                )

        person_staff_associations_to_remove: list[PersonOrganisationalUnitStaffAssociation] = []
        person_student_associations_to_remove: list[PersonOrganisationalUnitStudentAssociation] = []

        for association in person.staff_organisation_associations:
            if association.pure_id not in requested_staff_association_ids:
                person_staff_associations_to_remove.append(association)
        for association in person.student_organisation_associations:
            if association.pure_id not in requested_student_association_ids:
                person_student_associations_to_remove.append(association)

        for association in person_staff_associations_to_remove:
            if logger is not None:
                logger.debug(
                    f"Removing staff association {association.pure_id} with unit {association.organisational_unit_id}"
                )
            person.staff_organisation_associations.remove(association)
        for association in person_student_associations_to_remove:
            if logger is not None:
                logger.debug(
                    f"Removing student association {association.pure_id} with unit {association.organisational_unit_id}"
                )
            person.student_organisation_associations.remove(association)

        person_staff_association_ids = set(
            association.pure_id for association in person.staff_organisation_associations
        )
        person_student_association_ids = set(
            association.pure_id for association in person.student_organisation_associations
        )

        person_staff_associations_map = {
            association.pure_id: association for association in person.staff_organisation_associations
        }
        person_student_associations_map = {
            association.pure_id: association for association in person.student_organisation_associations
        }

        def parse_period(period):
            return DateTimeTZRange(
                lower=datetime.fromisoformat(period["startDate"]) if period["startDate"] else None,
                upper=datetime.fromisoformat(period["endDate"]) if period["endDate"] else None,
            )

        for pure_id in requested_staff_association_ids.intersection(person_staff_association_ids):
            association = person_staff_associations_map[pure_id]
            requested_association = requested_staff_associations[pure_id]
            if logger is not None:
                logger.debug(f"Updating staff association {pure_id} with unit {association.organisational_unit_id}")
            period = requested_association["period"]
            if period is not None:
                association.period = parse_period(period)
            association.organisational_unit_id = UUID(requested_association["unit_id"])
        for pure_id in requested_student_association_ids.intersection(person_student_association_ids):
            association = person_student_associations_map[pure_id]
            requested_association = requested_student_associations[pure_id]
            if logger is not None:
                logger.debug(f"Updating student association {pure_id} with unit {association.organisational_unit_id}")
            period = requested_association["period"]
            if period is not None:
                association.period = parse_period(period)
            association.organisational_unit_id = UUID(requested_association["unit_id"])

        for pure_id in found_units_requested_staff_association_ids.difference(person_staff_association_ids):
            requested_association = requested_staff_associations[pure_id]
            if logger is not None:
                logger.debug(f"Adding staff association {pure_id} with unit {requested_association['unit_id']}")
            period = requested_association["period"]
            association = PersonOrganisationalUnitStaffAssociation(
                pure_id=pure_id,
                person_id=person.id,
                organisational_unit_id=UUID(requested_association["unit_id"]),
            )
            if period is not None:
                association.period = parse_period(period)
            person.staff_organisation_associations.append(association)
        for pure_id in found_units_requested_student_association_ids.difference(person_student_association_ids):
            requested_association = requested_student_associations[pure_id]
            if logger is not None:
                logger.debug(f"Adding student association {pure_id} with unit {requested_association['unit_id']}")
            period = requested_association["period"]
            association = PersonOrganisationalUnitStudentAssociation(
                pure_id=pure_id,
                person_id=person.id,
                organisational_unit_id=UUID(requested_association["unit_id"]),
            )
            if period is not None:
                association.period = parse_period(period)
            person.student_organisation_associations.append(association)
