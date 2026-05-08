from typing import Callable
from uuid import UUID

import sqlalchemy
from sqlalchemy import CTE, func
from sqlalchemy.orm import aliased

from app.models import (
    OrganisationalUnit,
    Person,
    PersonOrganisationalUnitStaffAssociation,
)

pm_id = UUID("0435d70c-2eef-4944-90ed-649c9118ccac")
mat_id = UUID("833d4dea-d7a1-44f3-8775-c71744aed7d5")
phys_id = UUID("bbbdaec2-8b49-4e63-a317-7343570b0bf1")

faculties = [
    pm_id,
    mat_id,
    phys_id,
]


def query_units_with_all_children_text():
    """
    Serves as an example for querying persons and organisational units relationship

    Example usage:
    ```
    df = polars.read_database(sqlalchemy.sql.text(query_units_with_all_children_text()), conn)
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


def units_parents_filtered_all_level_1() -> Callable[[CTE], CTE]:
    """
    Filter for units that are level 1 (type_id 17278, hardcoded for now)
    """

    def filtered(units_parents_cte: CTE) -> CTE:
        return (
            sqlalchemy.select(units_parents_cte)
            .select_from(units_parents_cte)
            .join(
                OrganisationalUnit,
                units_parents_cte.c.organisational_unit_id == OrganisationalUnit.id,
            )
            .where(OrganisationalUnit.type_id == 17278)
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


def select_units_with_all_children(
    units_parents_filtered: Callable[[CTE], CTE],
) -> sqlalchemy.Select:
    """
    Recursively collects all children remembering the first parent.

    Possible filters:
        - `units_parents_filtered_all_level_1()`
        - `units_parents_filtered_unit_ids(unit_ids)`
    Example usage:
    ```
    df = polars.read_database(query_units_with_all_children(
        units_parents_filtered_all_level_1()
    ), conn)
    ```
    """
    units_parents_cte = (
        sqlalchemy.select(
            OrganisationalUnit.id.label("organisational_unit_id"),
            func.uuid(sqlalchemy.column("parent_text")).label("parent"),
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
        .cte()
    )

    units_parents_filtered_cte = units_parents_filtered(units_parents_cte)

    united_recursively_anchor = sqlalchemy.select(
        units_parents_filtered_cte.c.organisational_unit_id,
        units_parents_filtered_cte.c.organisational_unit_id.label("highest_parent"),
        sqlalchemy.literal(1).label("level"),
    ).cte(recursive=True)

    united_recursively_recursion = sqlalchemy.select(
        units_parents_cte.c.organisational_unit_id,
        united_recursively_anchor.c.highest_parent,
        (united_recursively_anchor.c.level + 1).label("level"),
    ).where(
        units_parents_cte.c.parent == united_recursively_anchor.c.organisational_unit_id
    )

    united_recursively = united_recursively_anchor.union_all(
        united_recursively_recursion
    )

    return sqlalchemy.select(united_recursively).order_by(
        united_recursively.c.level,
        united_recursively.c.highest_parent,
        united_recursively.c.organisational_unit_id,
    )


def select_units_with_faculties_named() -> sqlalchemy.Select:
    """
    Just like `select_units_with_all_children`, but with name and type attached.
    Starts with all level 1 units.
    """
    faculties = select_units_with_all_children(
        units_parents_filtered_all_level_1()
    ).cte()

    unit_itself = aliased(OrganisationalUnit, name="ou_unit_itself")
    unit_parent = aliased(OrganisationalUnit, name="ou_unit_parent")

    return (
        sqlalchemy.select(
            faculties.c.organisational_unit_id,
            unit_itself.name_ru,
            unit_itself.type_id,
            faculties.c.level,
            faculties.c.highest_parent.label("highest_parent_organisational_unit_id"),
            unit_parent.name_ru.label("highest_parent_name_ru"),
            unit_parent.type_id.label("highest_parent_type_id"),
        )
        .select_from(faculties)
        .outerjoin(
            unit_itself,
            faculties.c.organisational_unit_id == unit_itself.id,
        )
        .outerjoin(
            unit_parent,
            faculties.c.highest_parent == unit_parent.id,
        )
    )


def select_persons_staff_with_units_and_faculties_named() -> sqlalchemy.Select:
    """
    Persons joined with `select_units_with_faculties_named` as staff.
    """
    units = select_units_with_faculties_named().cte()
    return (
        sqlalchemy.select(
            Person.id.label("person_id"),
            Person.first_name,
            Person.last_name,
            units,
        )
        .select_from(Person)
        .outerjoin(Person.staff_organisation_associations)
        .outerjoin(
            units,
            units.c.organisational_unit_id
            == PersonOrganisationalUnitStaffAssociation.organisational_unit_id,
        )
        .order_by(
            units.c.highest_parent_name_ru,
            units.c.highest_parent_organisational_unit_id,
        )
    )


def select_faculty_persons_count_named() -> sqlalchemy.Select:
    """
    Level 1 units with number of persons associated as staff with them and their children recursively.
    """
    persons = select_persons_staff_with_units_and_faculties_named().cte()
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
