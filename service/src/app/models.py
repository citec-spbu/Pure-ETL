from datetime import UTC, datetime
from uuid import UUID

from psycopg2.extras import DateTimeTZRange
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import BIGINT


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class PersonOrganisationalUnitStaffAssociation(Base):
    __tablename__ = "persons_organisational_units_staff_associations"
    pure_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.person_id"), index=True)
    organisational_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("organisational_units.organisational_unit_id"), index=True
    )
    period: Mapped[DateTimeTZRange | None] = mapped_column(TSTZRANGE)
    person: Mapped[Person] = relationship(
        back_populates="staff_organisation_associations",
    )
    organisational_unit: Mapped[OrganisationalUnit] = relationship(
        back_populates="persons_staff",
    )


class PersonOrganisationalUnitStudentAssociation(Base):
    __tablename__ = "persons_organisational_units_student_associations"
    pure_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.person_id"), index=True)
    organisational_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("organisational_units.organisational_unit_id"), index=True
    )
    period: Mapped[DateTimeTZRange | None] = mapped_column(TSTZRANGE)
    person: Mapped[Person] = relationship(
        back_populates="student_organisation_associations",
    )
    organisational_unit: Mapped[OrganisationalUnit] = relationship(
        back_populates="persons_students",
    )


class ResearchOutputPersonAssociation(Base):
    __tablename__ = "research_outputs_persons_associations"
    research_output_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_outputs.research_output_id"), primary_key=True, index=True
    )
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.person_id"), primary_key=True, index=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    person_role_type_id: Mapped[int | None] = mapped_column(BIGINT)
    research_output: Mapped[ResearchOutput] = relationship(
        back_populates="person_associations",
    )
    person: Mapped[Person] = relationship(
        back_populates="research_output_associations",
    )


class ResearchOutputOrganisationalUnitAssociation(Base):
    __tablename__ = "research_outputs_organisational_units_associations"
    research_output_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_outputs.research_output_id"), primary_key=True, index=True
    )
    organisational_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("organisational_units.organisational_unit_id"), primary_key=True, index=True
    )
    research_output: Mapped[ResearchOutput] = relationship(
        back_populates="organisational_unit_associations",
    )
    organisational_unit: Mapped[OrganisationalUnit] = relationship(
        back_populates="research_output_associations",
    )


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[UUID] = mapped_column(name="person_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    titles: Mapped[list | None] = mapped_column(JSONB)
    ids: Mapped[list | None] = mapped_column(JSONB)
    orcid: Mapped[str | None] = mapped_column()
    raw: Mapped[dict | None] = mapped_column(JSONB)
    staff_organisation_associations: Mapped[list[PersonOrganisationalUnitStaffAssociation]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    student_organisation_associations: Mapped[list[PersonOrganisationalUnitStudentAssociation]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    research_output_associations: Mapped[list[ResearchOutputPersonAssociation]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )


class OrganisationalUnit(Base):
    __tablename__ = "organisational_units"
    id: Mapped[UUID] = mapped_column(name="organisational_unit_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    type_id: Mapped[int | None] = mapped_column(BIGINT)
    name_ru: Mapped[str | None] = mapped_column()
    name_en: Mapped[str | None] = mapped_column()
    parents: Mapped[list[str]] = mapped_column(JSONB, default=list)
    ids: Mapped[list | None] = mapped_column(JSONB)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    persons_staff: Mapped[list[PersonOrganisationalUnitStaffAssociation]] = relationship(
        back_populates="organisational_unit",
        cascade="all, delete-orphan",
    )
    persons_students: Mapped[list[PersonOrganisationalUnitStudentAssociation]] = relationship(
        back_populates="organisational_unit",
        cascade="all, delete-orphan",
    )
    research_output_associations: Mapped[list[ResearchOutputOrganisationalUnitAssociation]] = relationship(
        back_populates="organisational_unit",
        cascade="all, delete-orphan",
    )


class ResearchOutput(Base):
    __tablename__ = "research_outputs"
    id: Mapped[UUID] = mapped_column(name="research_output_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    type_id: Mapped[int | None] = mapped_column(BIGINT)
    category_type_id: Mapped[int | None] = mapped_column(BIGINT)
    language_type_id: Mapped[int | None] = mapped_column(BIGINT)
    title: Mapped[str | None] = mapped_column()
    publication_statuses: Mapped[list | None] = mapped_column(JSONB)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    person_associations: Mapped[list[ResearchOutputPersonAssociation]] = relationship(
        back_populates="research_output",
        cascade="all, delete-orphan",
    )
    organisational_unit_associations: Mapped[list[ResearchOutputOrganisationalUnitAssociation]] = relationship(
        back_populates="research_output",
        cascade="all, delete-orphan",
    )


class ClassificationScheme(Base):
    __tablename__ = "classification_schemes"
    id: Mapped[UUID] = mapped_column(name="classification_scheme_id", primary_key=True)
    pure_id: Mapped[int] = mapped_column(BIGINT, unique=True)
    base_uri: Mapped[str] = mapped_column()
    description_ru: Mapped[str | None] = mapped_column()
    description_en: Mapped[str | None] = mapped_column()
    classifications: Mapped[list[Classification]] = relationship(
        back_populates="classification_scheme", cascade="all, delete"
    )
    raw: Mapped[dict | None] = mapped_column(JSONB)


class Classification(Base):
    __tablename__ = "classifications"
    pure_id: Mapped[int] = mapped_column(BIGINT, name="classification_pure_id", primary_key=True)
    uri: Mapped[str] = mapped_column()
    term_ru: Mapped[str | None] = mapped_column()
    term_en: Mapped[str | None] = mapped_column()
    disabled: Mapped[bool] = mapped_column(default=False)
    classification_scheme_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "classification_schemes.classification_scheme_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        index=True,
    )
    classification_scheme: Mapped[ClassificationScheme] = relationship(back_populates="classifications")
