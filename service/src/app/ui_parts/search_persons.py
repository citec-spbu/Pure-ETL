import polars as pl
import sqlalchemy
from dash import html

import app.ui_parts
from app import queries
from app.aio_components.search_aio import SearchAIO, aio_register_search
from app.client_types import AppState


def search_persons_element(aio_id="search-persons-field"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H3(children="Поиск по персонам"),
                    html.Abbr(
                        "?",
                        title=app.ui_parts.search_help,
                        className="help-icon",
                    ),
                ],
            ),
            SearchAIO(
                aio_id=aio_id,
                placeholder="Введите паттерн...",
                csv_filename="persons",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "person_id",
                        "first_name",
                        "last_name",
                        "pure_id",
                        "orcid",
                    ]
                ],
                toggles=[
                    "substring",
                    "case_insensitive",
                    "id",
                    "first_name",
                    "last_name",
                    "pure_id",
                    "orcid",
                ],
                toggles_defaults=["substring", "case_insensitive"],
                search_function="search_persons_query",
            ),
        ]
    )


@aio_register_search
def search_persons_query(
    state: AppState,
    pattern: str,
    page_number: int,
    page_size: int,
    toggles: dict[str, bool],
) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.search.search_persons(
            f"%{pattern}%" if toggles.get("substring") else str(pattern),
            case_insensitive=toggles.get("case_insensitive") or False,
            person_id=toggles.get("id") or False,
            first_name=toggles.get("first_name") or False,
            last_name=toggles.get("last_name") or False,
            pure_id=toggles.get("pure_id") or False,
            orcid=toggles.get("orcid") or False,
        ).subquery()
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.person_id, sqlalchemy.String),
                statement.c.first_name,
                statement.c.last_name,
                statement.c.pure_id,
                statement.c.orcid,
            )
            .select_from(statement)
            .order_by(statement.c.person_id)
            .offset((page_number - 1) * page_size)
            .limit(page_size),
            conn,
        )
        return df
