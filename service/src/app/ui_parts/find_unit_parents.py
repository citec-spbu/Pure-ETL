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
from app.models import OrganisationalUnit


def find_unit_parents_element(aio_id="find-unit-parents"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Найти parents organisational unit"),
                    html.Abbr(
                        "?",
                        title="Результат не будет выведен пока не будет введен ситаксически корректный uuid.\n"
                        "Собирает связи рекурсивно - будут выведены все organisational units, для которых заданный "
                        "organisational unit - подразделение.",
                        className="help-icon",
                    ),
                ],
            ),
            html.P("Введите uuid organisational unit:"),
            SearchAIO(
                aio_id=aio_id,
                placeholder="Unit uuid...",
                csv_filename="organisational-unit-parents",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "organisational_unit_id",
                        "name_ru",
                        "parent_id",
                        "recursion_level",
                    ]
                ],
                search_function="search_unit_parents_query",
            ),
        ]
    )


@aio_register_search
def search_unit_parents_query(state: AppState, pattern: str, toggles: dict[str, bool]) -> pl.DataFrame:
    with state.engine.connect() as conn:
        try:
            statement = queries.find_unit_parents(UUID(pattern)).cte()
        except ValueError:
            raise SearchException() from None
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String),
                OrganisationalUnit.name_ru,
                sqlalchemy.cast(statement.c.parent_id, sqlalchemy.String),
                statement.c.recursion_level,
            )
            .select_from(statement)
            .join(
                OrganisationalUnit,
                statement.c.organisational_unit_id == OrganisationalUnit.id,
            ),
            conn,
        )
        return df
