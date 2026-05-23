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
from app.models import ResearchOutput


def find_research_output_persons_element(aio_id="find-research-output-persons"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Найти persons, связанные с конкретным research output."),
                    html.Abbr(
                        "?",
                        title="Результат не будет выведен пока не будет введен синтаксически корректный uuid.",
                        className="help-icon",
                    ),
                ],
            ),
            html.P("Введите uuid research output:"),
            SearchAIO(
                aio_id=aio_id,
                placeholder="Research output id...",
                csv_filename="research-output-persons",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "person_id",
                        "first_name",
                        "last_name",
                        "person_role_type_id",
                        "research_output_id",
                        "title",
                        "pure_id",
                        "type_id",
                        "language_type_id",
                        "category_type_id",
                    ]
                ],
                search_function="find_research_output_persons_query",
            ),
        ]
    )


@aio_register_search
def find_research_output_persons_query(
    state: AppState,
    pattern: str,
    page_number: int,
    page_size: int,
    toggles: dict[str, bool],
) -> pl.DataFrame:
    with state.engine.connect() as conn:
        try:
            statement = queries.select_persons_with_research_outputs().where(ResearchOutput.id == UUID(pattern)).cte()
        except ValueError:
            raise SearchException() from None
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.person_id, sqlalchemy.String),
                statement.c.first_name,
                statement.c.last_name,
                statement.c.person_role_type_id,
                sqlalchemy.cast(statement.c.research_output_id, sqlalchemy.String),
                statement.c.title,
                statement.c.pure_id,
                statement.c.type_id,
                statement.c.language_type_id,
                statement.c.category_type_id,
            )
            .select_from(statement)
            .order_by(statement.c.person_id)
            .offset((page_number - 1) * page_size)
            .limit(page_size),
            conn,
        )
        return df
