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
from app.models import OrganisationalUnit, ResearchOutput


def find_research_output_organisational_units_element(
    aio_id="find-research-output-organisational-units",
):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Найти organisational units, связанные с конкретным research output."),
                    html.Abbr(
                        "?",
                        title="Результат не будет выведен пока не будет введен ситаксически корректный uuid.\n"
                        "Выводит units с которыми есть прямые связи. Не учитывает связи между units.",
                        className="help-icon",
                    ),
                ],
            ),
            html.P("Введите uuid research output:"),
            SearchAIO(
                aio_id=aio_id,
                placeholder="Research output id...",
                csv_filename="research-output-organisational-units",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "research_output_id",
                        "research_output_title",
                        "research_output_pure_id",
                        "research_output_type_id",
                        "research_output_language_type_id",
                        "research_output_category_type_id",
                        "organisational_unit_id",
                        "organisational_unit_name_ru",
                        "organisational_unit_type_id",
                    ]
                ],
                search_function="find_research_output_organisational_units_query",
            ),
        ]
    )


@aio_register_search
def find_research_output_organisational_units_query(
    state: AppState, pattern: str, toggles: dict[str, bool]
) -> pl.DataFrame:
    with state.engine.connect() as conn:
        try:
            statement = (
                queries.select_research_outputs_for_units(
                    units=sqlalchemy.select(
                        OrganisationalUnit.id.label("organisational_unit_id"),
                        OrganisationalUnit.name_ru.label("organisational_unit_name_ru"),
                        OrganisationalUnit.type_id.label("organisational_unit_type_id"),
                    )
                    .select_from(OrganisationalUnit)
                    .cte()
                )
                .where(ResearchOutput.id == UUID(pattern))
                .cte()
            )
        except ValueError:
            raise SearchException() from None
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.research_output_id, sqlalchemy.String),
                statement.c.research_output_title,
                statement.c.research_output_pure_id,
                statement.c.research_output_type_id,
                statement.c.research_output_language_type_id,
                statement.c.research_output_category_type_id,
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String),
                statement.c.organisational_unit_name_ru,
                statement.c.organisational_unit_type_id,
            ).select_from(statement),
            conn,
        )
        return df
