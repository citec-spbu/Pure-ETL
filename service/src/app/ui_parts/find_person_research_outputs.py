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
from app.models import Person


def find_person_research_outputs_element(aio_id="find-person-research-outputs"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Найти research outputs, связанные с конкретным person."),
                    html.Abbr(
                        "?",
                        title="Результат не будет выведен пока не будет введен синтаксически корректный uuid.",
                        className="help-icon",
                    ),
                ],
            ),
            html.P("Введите uuid person:"),
            SearchAIO(
                aio_id=aio_id,
                placeholder="Person id...",
                csv_filename="person-research-outputs",
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
                search_function="find_person_research_outputs_query",
            ),
        ]
    )


@aio_register_search
def find_person_research_outputs_query(state: AppState, pattern: str, toggles: dict[str, bool]) -> pl.DataFrame:
    with state.engine.connect() as conn:
        try:
            statement = queries.select_persons_with_research_outputs().where(Person.id == UUID(pattern)).cte()
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
            ).select_from(statement),
            conn,
        )
        return df
