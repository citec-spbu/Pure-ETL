from uuid import UUID

import polars as pl
import sqlalchemy
from dash import html

from app import queries
from app.aio_components.search_aio import (
    SearchAIO,
    SearchException,
    aio_register_search,
)
from app.client_types import AppState


def find_organisational_unit_research_outputs_element(
    aio_id="find-organisational-unit-research-outputs",
):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(
                        children="Найти research outputs, связанные с конкретным organisational unit или его "
                        "подразделениями"
                    ),
                    html.Abbr(
                        "?",
                        title="Результат не будет выведен пока не будет введен синтаксически корректный uuid.\n"
                        "Смотрит связь рекурсивно - research output будет связан с organisational unit, если есть "
                        "связь с этим unit или с любым из его потомков.",
                        className="help-icon",
                    ),
                ],
            ),
            html.P("Введите uuid organisational unit:"),
            SearchAIO(
                aio_id=aio_id,
                placeholder="Organisational unit id...",
                csv_filename="organisational-unit-research-outputs",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "research_output_id",
                        "research_output_title",
                        "research_output_pure_id",
                        "research_output_type_id",
                        "research_output_language_type_id",
                        "research_output_category_type_id",
                        "linked_through_organisational_unit_id",
                        "linked_through_name_ru",
                        "linked_through_type_id",
                        "highest_parent_organisational_unit_id",
                        "highest_parent_name_ru",
                        "highest_parent_type_id",
                    ]
                ],
                search_function="find_organisational_unit_research_outputs_query",
            ),
        ]
    )


@aio_register_search
def find_organisational_unit_research_outputs_query(
    state: AppState,
    pattern: str,
    page_number: int,
    page_size: int,
    toggles: dict[str, bool],
) -> pl.DataFrame:
    with state.engine.connect() as conn:
        try:
            statement = queries.select_research_outputs_for_units(
                units=queries.organisational_units.select_units_with_all_children_named(
                    queries.organisational_units.select_units_with_all_children_filter(
                        filter_units_by_id=[UUID(pattern)]
                    ).cte()
                ).cte()
            ).cte()
        except ValueError:
            raise SearchException() from None
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String),
                statement.c.name_ru,
                sqlalchemy.cast(statement.c.research_output_id, sqlalchemy.String),
                statement.c.research_output_title,
                statement.c.research_output_pure_id,
                statement.c.research_output_type_id,
                statement.c.research_output_language_type_id,
                statement.c.research_output_category_type_id,
                sqlalchemy.cast(statement.c.highest_parent_organisational_unit_id, sqlalchemy.String),
                statement.c.highest_parent_name_ru,
                statement.c.highest_parent_type_id,
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String).label(
                    "linked_through_organisational_unit_id"
                ),
                statement.c.name_ru.label("linked_through_name_ru"),
                statement.c.type_id.label("linked_through_type_id"),
                statement.c.recursion_level.label("linked_through_recursion_level"),
            )
            .select_from(statement)
            .order_by(
                statement.c.highest_parent_organisational_unit_id,
                statement.c.organisational_unit_id,
                statement.c.research_output_id,
            )
            .offset((page_number - 1) * page_size)
            .limit(page_size),
            conn,
        )
        return df
