import sqlalchemy

from app.models import (
    OrganisationalUnit,
    Person,
    ResearchOutput,
)


def search_units(
    pattern: str,
    case_insensitive=False,
    name_ru=False,
    name_en=False,
    organisational_unit_id=False,
    type_id=False,
    pure_id=False,
) -> sqlalchemy.Select:
    """
    Uses PostgreSQL pattern matching.

    Columns returned:
    - `organisational_unit_id` - `uuid`
    - `name_ru` - `text`
    - `name_en` - `text`
    - `pure_id` - integer
    - `type_id` - integer
    """

    def filter(item):
        return item.ilike(pattern) if case_insensitive else item.like(pattern)

    return (
        sqlalchemy.select(
            OrganisationalUnit.id.label("organisational_unit_id"),
            OrganisationalUnit.name_ru,
            OrganisationalUnit.name_en,
            OrganisationalUnit.pure_id,
            OrganisationalUnit.type_id,
        )
        .select_from(OrganisationalUnit)
        .where(
            (
                filter(sqlalchemy.cast(OrganisationalUnit.id, sqlalchemy.String))
                if organisational_unit_id
                else sqlalchemy.false()
            )
            | (filter(OrganisationalUnit.name_ru) if name_ru else sqlalchemy.false())
            | (filter(OrganisationalUnit.name_en) if name_en else sqlalchemy.false())
            | (
                filter(sqlalchemy.cast(OrganisationalUnit.pure_id, sqlalchemy.String))
                if pure_id
                else sqlalchemy.false()
            )
            | (
                filter(sqlalchemy.cast(OrganisationalUnit.type_id, sqlalchemy.String))
                if type_id
                else sqlalchemy.false()
            )
        )
    )


def search_persons(
    pattern: str,
    case_insensitive=False,
    person_id=False,
    first_name=False,
    last_name=False,
    pure_id=False,
    orcid=False,
) -> sqlalchemy.Select:
    """
    Uses PostgreSQL pattern matching.

    Columns returned:
    - `person_id` - `uuid`
    - `first_name` - `text`
    - `first_name` - `text`
    - `pure_id` - integer
    - `orcid` - `text`
    """

    def filter(item):
        return item.ilike(pattern) if case_insensitive else item.like(pattern)

    return (
        sqlalchemy.select(
            Person.id.label("person_id"),
            Person.first_name,
            Person.last_name,
            Person.pure_id,
            Person.orcid,
        )
        .select_from(Person)
        .where(
            (filter(sqlalchemy.cast(Person.id, sqlalchemy.String)) if person_id else sqlalchemy.false())
            | (filter(Person.first_name) if first_name else sqlalchemy.false())
            | (filter(Person.last_name) if last_name else sqlalchemy.false())
            | (filter(sqlalchemy.cast(Person.pure_id, sqlalchemy.String)) if pure_id else sqlalchemy.false())
            | (filter(Person.orcid) if orcid else sqlalchemy.false())
        )
    )


def search_research_outputs(
    pattern: str,
    case_insensitive=False,
    research_output_id=False,
    title=False,
    pure_id=False,
) -> sqlalchemy.Select:
    """
    Uses PostgreSQL pattern matching.

    Columns returned:
    - `research_output_id` - `uuid`
    - `title` - `text`
    - `pure_id` - integer
    - `type_id` - integer
    - `language_type_id` - integer
    - `category_type_id` - integer
    """

    def filter(item):
        return item.ilike(pattern) if case_insensitive else item.like(pattern)

    return (
        sqlalchemy.select(
            ResearchOutput.id.label("research_output_id"),
            ResearchOutput.title,
            ResearchOutput.pure_id,
            ResearchOutput.type_id,
            ResearchOutput.language_type_id,
            ResearchOutput.category_type_id,
        )
        .select_from(ResearchOutput)
        .where(
            (
                filter(sqlalchemy.cast(ResearchOutput.id, sqlalchemy.String))
                if research_output_id
                else sqlalchemy.false()
            )
            | (filter(ResearchOutput.title) if title else sqlalchemy.false())
            | (filter(sqlalchemy.cast(ResearchOutput.pure_id, sqlalchemy.String)) if pure_id else sqlalchemy.false())
        )
    )
