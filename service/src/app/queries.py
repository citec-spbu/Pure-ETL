import datetime
from collections.abc import Callable
from uuid import UUID

import sqlalchemy
from sqlalchemy import CTE, func
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import aliased

from app.models import (
    OrganisationalUnit,
    Person,
    PersonOrganisationalUnitStaffAssociation,
    PersonOrganisationalUnitStudentAssociation,
    ResearchOutput,
    ResearchOutputOrganisationalUnitAssociation,
    ResearchOutputPersonAssociation,
)

spbu = UUID("abf8fae5-478f-4b63-8a8c-944750655c44")
pm_id = UUID("0435d70c-2eef-4944-90ed-649c9118ccac")
mat_id = UUID("833d4dea-d7a1-44f3-8775-c71744aed7d5")
phys_id = UUID("bbbdaec2-8b49-4e63-a317-7343570b0bf1")

faculties = [
    pm_id,
    mat_id,
    phys_id,
]


def select_units_with_all_children_text():
    """
    Serves as an example for querying persons and organisational units relationship

    Example usage:
    ```
    df = polars.read_database(
        sqlalchemy.sql.text(query_units_with_all_children_text()),
        conn,
    )
    ```
    """
    return """
    with recursive units_parents as (
        select
            ou.organisational_unit_id,
            uuid(parent_text) as parent
        from organisational_units ou
        left outer join lateral jsonb_array_elements_text(
            case jsonb_typeof(ou.parents)
                when 'array' then ou.parents
                else '[]' end
       ) as parent_text on true
    ),
    units_parents_filtered_start as (
        select up.*
        from units_parents up
        join organisational_units ou
        on up.organisational_unit_id = ou.organisational_unit_id
        where ou.type_id = 17278
    ),
    united_recursively AS (
        select
            up.organisational_unit_id,
            up.organisational_unit_id as highest_parent,
            1 as level
            from units_parents_filtered_start up
        UNION all
        select
            up.organisational_unit_id,
            u.highest_parent,
            u.level + 1 as level
        from units_parents up
        inner join united_recursively u
        on up.parent = u.organisational_unit_id
    )
    select * from united_recursively
    order by level, highest_parent, organisational_unit_id;
    """


def units_parents() -> sqlalchemy.Select:
    """
    Destructures json `parents` list into many rows for all units

    Columns returned:
    - `organisational_unit_id` - `uuid`
    - `parent_id` - `uuid`
    """
    return (
        sqlalchemy.select(
            OrganisationalUnit.id.label("organisational_unit_id"),
            func.uuid(sqlalchemy.column("parent_text")).label("parent_id"),
        )
        .select_from(OrganisationalUnit)
        .outerjoin(
            func.jsonb_array_elements_text(
                sqlalchemy.case(
                    (
                        func.jsonb_typeof(OrganisationalUnit.parents) == "array",
                        OrganisationalUnit.parents,
                    ),
                    else_=sqlalchemy.literal("[]", type_=sqlalchemy.String),
                )
            ).lateral("parent_text"),
            sqlalchemy.true(),
        )
    )


def select_units_with_all_children(
    filter_units_by_id: None | list[UUID] = None,
    filter_units_by_type_id: None | list[int] = None,
) -> sqlalchemy.Select:
    """
    Recursively collects all children remembering the first parent.

    Possible filters:
    - `filter_units_by_id`
    - `filter_units_by_type`

    Only one can be used at a time

    Columns returned:
    - `organisational_unit_id` - `uuid`
    - `highest_parent_organisational_unit_id` - `uuid`
    - `recursion_level` - integer

    Example usage:
    ```
    df = polars.read_database(query_units_with_all_children(), conn)
    ```
    """

    def units_parents_filtered_type_ids(
        type_ids: None | list[int] = None,
    ) -> Callable[[CTE], CTE]:
        """
        Filter for units by type id. Default is hardcoded level 1.
        """

        if type_ids is None:
            type_ids = [17278]

        def filtered(units_parents_cte: CTE) -> CTE:
            return (
                sqlalchemy.select(units_parents_cte)
                .select_from(units_parents_cte)
                .join(
                    OrganisationalUnit,
                    units_parents_cte.c.organisational_unit_id == OrganisationalUnit.id,
                )
                .where(OrganisationalUnit.type_id.in_(type_ids))
                .cte()
            )

        return filtered

    def units_parents_filtered_unit_ids(unit_ids: list[UUID]) -> Callable[[CTE], CTE]:
        """
        Filter for units by organisational_unit_id
        """

        def filtered(units_parents_cte: CTE) -> CTE:
            return (
                sqlalchemy.select(units_parents_cte)
                .select_from(units_parents_cte)
                .where(units_parents_cte.c.organisational_unit_id.in_(unit_ids))
                .cte()
            )

        return filtered

    units_parents_cte = units_parents().cte()

    if filter_units_by_id is not None:
        units_parents_filtered_cte = units_parents_filtered_unit_ids(filter_units_by_id)(units_parents_cte)
    elif filter_units_by_type_id is not None:
        units_parents_filtered_cte = units_parents_filtered_type_ids(filter_units_by_type_id)(units_parents_cte)
    else:
        units_parents_filtered_cte = units_parents_filtered_type_ids()(units_parents_cte)

    united_recursively_anchor = sqlalchemy.select(
        units_parents_filtered_cte.c.organisational_unit_id,
        units_parents_filtered_cte.c.organisational_unit_id.label("highest_parent_organisational_unit_id"),
        sqlalchemy.literal(1).label("recursion_level"),
    ).cte(recursive=True)

    united_recursively_recursion = sqlalchemy.select(
        units_parents_cte.c.organisational_unit_id,
        united_recursively_anchor.c.highest_parent_organisational_unit_id,
        (united_recursively_anchor.c.recursion_level + 1).label("recursion_level"),
    ).where(units_parents_cte.c.parent_id == united_recursively_anchor.c.organisational_unit_id)

    united_recursively = united_recursively_anchor.union_all(united_recursively_recursion)

    return sqlalchemy.select(united_recursively).order_by(
        united_recursively.c.recursion_level,
        united_recursively.c.highest_parent_organisational_unit_id,
        united_recursively.c.organisational_unit_id,
    )


def find_unit_parents(
    unit_id: UUID,
) -> sqlalchemy.Select:
    """
    Recursively collects all parents of the unit.

    Columns returned:
    - `organisational_unit_id` - `uuid`
    - `parent_id` - `uuid`
    - `recursion_level` - integer

    Example usage:
    ```
    df = polars.read_database(find_unit_parents(unit_id), conn)
    ```
    """

    units_parents_cte = units_parents().cte()

    united_recursively_anchor = (
        sqlalchemy.select(
            units_parents_cte.c.organisational_unit_id,
            units_parents_cte.c.parent_id,
            sqlalchemy.literal(1).label("recursion_level"),
        )
        .where(units_parents_cte.c.organisational_unit_id == unit_id)
        .cte(recursive=True)
    )

    united_recursively_recursion = sqlalchemy.select(
        units_parents_cte.c.organisational_unit_id,
        units_parents_cte.c.parent_id,
        (united_recursively_anchor.c.recursion_level + 1).label("recursion_level"),
    ).where(units_parents_cte.c.organisational_unit_id == united_recursively_anchor.c.parent_id)

    united_recursively = united_recursively_anchor.union_all(united_recursively_recursion)

    return sqlalchemy.select(united_recursively).order_by(
        united_recursively.c.recursion_level.desc(),
        united_recursively.c.organisational_unit_id,
        united_recursively.c.parent_id,
    )


def select_units_with_all_children_named(
    units: None | CTE = None,
) -> sqlalchemy.Select:
    """
    Accepts the result of `select_units_with_all_children` as cte and attaches more data.

    Columns expected in the provided cte:
    - `organisational_unit_id` - `uuid`
    - `highest_parent_organisational_unit_id` - `uuid`
    - `recursion_level` - integer

    Columns returned:
    - All from provided `units` cte
    - `name_ru` - `text`
    - `type_id` - integer
    - `highest_parent_name_ru` - `text`
    - `highest_parent_type_id` - integer
    """

    if units is None:
        units = select_units_with_all_children().cte()

    unit_itself = aliased(OrganisationalUnit, name="ou_unit_itself")
    unit_parent = aliased(OrganisationalUnit, name="ou_unit_parent")

    return (
        sqlalchemy.select(
            units,
            unit_itself.name_ru,
            unit_itself.type_id,
            unit_parent.name_ru.label("highest_parent_name_ru"),
            unit_parent.type_id.label("highest_parent_type_id"),
        )
        .select_from(units)
        .outerjoin(
            unit_itself,
            units.c.organisational_unit_id == unit_itself.id,
        )
        .outerjoin(
            unit_parent,
            units.c.highest_parent_organisational_unit_id == unit_parent.id,
        )
    )


def select_persons_named_for_units(
    units: None | CTE = None,
    staff=True,
    outerjoin=False,
    date: None | datetime.datetime = None,
    period_overlaps: None | Range = None,
    period_contained: None | Range = None,
) -> sqlalchemy.Select:
    """
    Persons joined as staff or students with `select_units_with_all_children_named` as cte.

    Params:
    - `staff` - controls whether to join as staff or as students
    - `outerjoin` - controls whether to perform left outer join from persons - returns persons without links
    - `date` - date that needs to be inside of the link period
    - `period_overlaps` - period that needs to overlap with the link period
    - `period_contained` - period that needs to be fully contained within the link period

    Columns expected in the provided cte:
    - `organisational_unit_id` - `uuid`

    Columns returned:
    - `person_id` - `uuid`
    - `first_name` - `text`
    - `last_name` - `text`
    - `period_start`
    - `period_end`
    - All from provided `units` cte
    """

    if units is None:
        units = select_units_with_all_children_named().cte()

    query = sqlalchemy.select(
        Person.id.label("person_id"),
        Person.first_name,
        Person.last_name,
        units,
        func.lower(
            PersonOrganisationalUnitStaffAssociation.period
            if staff
            else PersonOrganisationalUnitStudentAssociation.period
        ).label("period_start"),
        func.upper(
            PersonOrganisationalUnitStaffAssociation.period
            if staff
            else PersonOrganisationalUnitStudentAssociation.period
        ).label("period_end"),
    ).select_from(Person)

    if staff:
        query = (
            query.join(Person.staff_organisation_associations, isouter=outerjoin)
            .join(
                units,
                units.c.organisational_unit_id == PersonOrganisationalUnitStaffAssociation.organisational_unit_id,
                isouter=outerjoin,
            )
            .where(
                (
                    PersonOrganisationalUnitStaffAssociation.period.contains(date)
                    if date is not None
                    else sqlalchemy.true()
                )
                & (
                    PersonOrganisationalUnitStaffAssociation.period.contains(period_contained)
                    if period_contained is not None
                    else sqlalchemy.true()
                )
                & (
                    PersonOrganisationalUnitStaffAssociation.period.overlaps(period_overlaps)
                    if period_overlaps is not None
                    else sqlalchemy.true()
                )
            )
        )
    else:
        query = (
            query.join(Person.student_organisation_associations, isouter=outerjoin)
            .join(
                units,
                units.c.organisational_unit_id == PersonOrganisationalUnitStudentAssociation.organisational_unit_id,
                isouter=outerjoin,
            )
            .where(
                (
                    PersonOrganisationalUnitStudentAssociation.period.contains(date)
                    if date is not None
                    else sqlalchemy.true()
                )
                & (
                    PersonOrganisationalUnitStudentAssociation.period.contains(period_contained)
                    if period_contained is not None
                    else sqlalchemy.true()
                )
                & (
                    PersonOrganisationalUnitStudentAssociation.period.overlaps(period_overlaps)
                    if period_overlaps is not None
                    else sqlalchemy.true()
                )
            )
        )

    return query


def select_research_outputs_for_units(
    units: None | CTE = None,
    outerjoin=False,
) -> sqlalchemy.Select:
    """
    Research outputs joined with `select_units_with_all_children_named` as cte.

    Params:
    - `outerjoin` - controls whether to perform left outer join from research
      outputs - returns research ouputs without links

    Columns expected in the provided cte:
    - `organisational_unit_id` - `uuid`

    Columns returned:
    - `research_output_id` - `uuid`
    - `research_output_title` - `text`
    - `research_output_pure_id` - integer
    - `research_output_type_id` - integer
    - `research_output_language_type_id` - integer
    - `research_output_category_type_id` - integer
    - All from the provided `units` cte
    """

    if units is None:
        units = select_units_with_all_children_named(
            units=select_units_with_all_children(filter_units_by_id=[spbu]).cte()
        ).cte()

    return (
        sqlalchemy.select(
            ResearchOutput.id.label("research_output_id"),
            ResearchOutput.title.label("research_output_title"),
            ResearchOutput.pure_id.label("research_output_pure_id"),
            ResearchOutput.type_id.label("research_output_type_id"),
            ResearchOutput.category_type_id.label("research_output_category_type_id"),
            ResearchOutput.language_type_id.label("research_output_language_type_id"),
            units,
        )
        .select_from(ResearchOutput)
        .join(ResearchOutput.organisational_unit_associations, isouter=outerjoin)
        .join(
            units,
            units.c.organisational_unit_id == ResearchOutputOrganisationalUnitAssociation.organisational_unit_id,
            isouter=outerjoin,
        )
    )


def select_highest_units_persons_count_named(
    persons: None | CTE = None,
) -> sqlalchemy.Select:
    """
    Units with number of persons associated as staff with them and their children recursively.
    Accepts `select_persons_named_for_units` output as cte.

    Columns expected in the provided cte:
    - `highest_parent_organisational_unit_id` - `uuid`
    - `person_id` - `uuid`

    Columns returned:
    - `highest_parent_organisational_unit_id` - `uuid`
    - `highest_parent_name_ru` - `text`
    - `persons_count` - integer
    """

    if persons is None:
        persons = select_persons_named_for_units().cte()

    units = (
        sqlalchemy.select(
            persons.c.highest_parent_organisational_unit_id,
            func.count(func.distinct(persons.c.person_id)).label("persons_count"),
        )
        .select_from(persons)
        .group_by(persons.c.highest_parent_organisational_unit_id)
        .where(persons.c.highest_parent_organisational_unit_id.is_not(None))
        .cte()
    )
    return (
        sqlalchemy.select(
            units,
            OrganisationalUnit.name_ru.label("highest_parent_name_ru"),
        )
        .select_from(units)
        .join(
            OrganisationalUnit,
            units.c.highest_parent_organisational_unit_id == OrganisationalUnit.id,
        )
    )


def select_persons_with_research_outputs() -> sqlalchemy.Select:
    """
    Columns returned:
    - `person_id` - `uuid`
    - `first_name` - `text`
    - `last_name` - `text`
    - `person_role_type_id` - integer
    - `research_output_id` - `uuid`
    - `title` - `text`
    - `pure_id` - integer
    - `type_id` - integer
    - `language_type_id` - integer
    - `category_type_id` - integer
    """

    return (
        sqlalchemy.select(
            Person.id.label("person_id"),
            Person.first_name,
            Person.last_name,
            ResearchOutputPersonAssociation.person_role_type_id,
            ResearchOutput.id.label("research_output_id"),
            ResearchOutput.title,
            ResearchOutput.pure_id,
            ResearchOutput.type_id,
            ResearchOutput.category_type_id,
            ResearchOutput.language_type_id,
        )
        .select_from(ResearchOutput)
        .join(ResearchOutput.person_associations)
        .join(ResearchOutputPersonAssociation.person)
    )


def query_units(
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


def query_persons(
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


def query_research_outputs(
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
