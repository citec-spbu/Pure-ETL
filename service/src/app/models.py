from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from psycopg2.extras import DateTimeTZRange
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import BIGINT


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PersonOrganisationalUnitStaffAssociation(Base):
    __tablename__ = "persons_organisational_units_staff_association"
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.person_id"), primary_key=True
    )
    organisational_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("organisational_units.organisational_unit_id"), primary_key=True
    )
    period: Mapped[Optional[DateTimeTZRange]] = mapped_column(TSTZRANGE)
    person: Mapped["Person"] = relationship(
        back_populates="staff_organisation_associations",
    )
    organisational_unit: Mapped["OrganisationalUnit"] = relationship(
        back_populates="persons_staff",
    )


class PersonOrganisationalUnitStudentAssociation(Base):
    __tablename__ = "persons_organisational_units_student_association"
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.person_id"), primary_key=True
    )
    organisational_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("organisational_units.organisational_unit_id"), primary_key=True
    )
    period: Mapped[Optional[DateTimeTZRange]] = mapped_column(TSTZRANGE)
    person: Mapped["Person"] = relationship(
        back_populates="student_organisation_associations",
    )
    organisational_unit: Mapped["OrganisationalUnit"] = relationship(
        back_populates="persons_students",
    )


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[UUID] = mapped_column(name="person_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    first_name: Mapped[Optional[str]]
    last_name: Mapped[Optional[str]]
    titles: Mapped[Optional[list]] = mapped_column(JSONB)
    ids: Mapped[Optional[list]] = mapped_column(JSONB)
    orcid: Mapped[Optional[str]] = mapped_column()
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    staff_organisation_associations: Mapped[
        List[PersonOrganisationalUnitStaffAssociation]
    ] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    student_organisation_associations: Mapped[
        List[PersonOrganisationalUnitStudentAssociation]
    ] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )


class OrganisationalUnit(Base):
    __tablename__ = "organisational_units"
    id: Mapped[UUID] = mapped_column(name="organisational_unit_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    type_id: Mapped[Optional[int]] = mapped_column(BIGINT)
    name_ru: Mapped[Optional[str]] = mapped_column()
    name_en: Mapped[Optional[str]] = mapped_column()
    parents: Mapped[list[UUID]] = mapped_column(JSONB, default=list)
    ids: Mapped[Optional[list]] = mapped_column(JSONB)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    persons_staff: Mapped[List[PersonOrganisationalUnitStaffAssociation]] = (
        relationship(
            back_populates="organisational_unit",
            cascade="all, delete-orphan",
        )
    )
    persons_students: Mapped[List[PersonOrganisationalUnitStudentAssociation]] = (
        relationship(
            back_populates="organisational_unit",
            cascade="all, delete-orphan",
        )
    )


class ResearchOutput(Base):
    __tablename__ = "research_outputs"
    id: Mapped[UUID] = mapped_column(name="research_output_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    type_id: Mapped[Optional[int]] = mapped_column(BIGINT)
    category_type_id: Mapped[Optional[int]] = mapped_column(BIGINT)
    language_type_id: Mapped[Optional[int]] = mapped_column(BIGINT)
    title: Mapped[Optional[str]] = mapped_column()
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)


class ClassificationScheme(Base):
    __tablename__ = "classification_schemes"
    id: Mapped[UUID] = mapped_column(name="classification_scheme_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    base_uri: Mapped[str] = mapped_column()
    description_ru: Mapped[Optional[str]] = mapped_column()
    description_en: Mapped[Optional[str]] = mapped_column()
    classifications: Mapped[List["Classification"]] = relationship(
        back_populates="classification_scheme", cascade="all, delete"
    )
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)


class Classification(Base):
    __tablename__ = "classification"
    pure_id: Mapped[int] = mapped_column(
        BIGINT, name="classification_pure_id", primary_key=True
    )
    uri: Mapped[str] = mapped_column()
    term_ru: Mapped[Optional[str]] = mapped_column()
    term_en: Mapped[Optional[str]] = mapped_column()
    disabled: Mapped[bool] = mapped_column(default=False)
    classification_scheme_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "classification_schemes.classification_scheme_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    classification_scheme: Mapped[ClassificationScheme] = relationship(
        back_populates="classifications"
    )
