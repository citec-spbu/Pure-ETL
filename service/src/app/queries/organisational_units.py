from collections.abc import Callable
from uuid import UUID

import sqlalchemy
from sqlalchemy import CTE, func
from sqlalchemy.orm import aliased

from app.models import (
    OrganisationalUnit,
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


def units_parents() -> sqlalchemy.Select[tuple[UUID, UUID]]:
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


def select_units_with_all_children_filter(
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

    return _select_units_with_all_children(units_parents_cte, units_parents_filtered_cte)


def select_units_with_all_children(
    highest_parents: sqlalchemy.CTE,
) -> sqlalchemy.Select:
    """
    Recursively collects all children remembering the first parent.

    Columns expected:
    - `organisational_unit_id` - `uuid`

    Columns returned:
    - `organisational_unit_id` - `uuid`
    - `highest_parent_organisational_unit_id` - `uuid`
    - `recursion_level` - integer

    Example usage:
    ```
    df = polars.read_database(query_units_with_all_children(), conn)
    ```
    """
    units_parents_cte = units_parents().cte()

    units_parents_filtered_cte = (
        sqlalchemy.select(units_parents_cte)
        .select_from(units_parents_cte)
        .join(highest_parents, units_parents_cte.c.organisational_unit_id == highest_parents.c.organisational_unit_id)
        .cte()
    )

    return _select_units_with_all_children(units_parents_cte, units_parents_filtered_cte)


def _select_units_with_all_children(
    units_parents_cte: sqlalchemy.CTE,
    units_parents_filtered_cte: sqlalchemy.CTE,
) -> sqlalchemy.Select:
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
        units = select_units_with_all_children_filter().cte()

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
