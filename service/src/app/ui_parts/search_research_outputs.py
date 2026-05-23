import polars as pl
import sqlalchemy
from dash import html

import app.ui_parts
from app import queries
from app.aio_components.search_aio import SearchAIO, aio_register_search
from app.client_types import AppState


def search_research_outputs_element(aio_id="search-research-outputs-field"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H3(children="Поиск по результатам исследований"),
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
                csv_filename="research-outputs",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "research_output_id",
                        "title",
                        "pure_id",
                        "language_type_id",
                        "category_type_id",
                    ]
                ],
                toggles=[
                    "substring",
                    "case_insensitive",
                    "id",
                    "title",
                    "pure_id",
                ],
                toggles_defaults=["substring", "case_insensitive"],
                search_function="search_research_outputs_query",
            ),
        ]
    )


@aio_register_search
def search_research_outputs_query(
    state: AppState,
    pattern: str,
    page_number: int,
    page_size: int,
    toggles: dict[str, bool],
) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.search.search_research_outputs(
            f"%{pattern}%" if toggles.get("substring") else str(pattern),
            case_insensitive=toggles.get("case_insensitive") or False,
            research_output_id=toggles.get("id") or False,
            title=toggles.get("title") or False,
            pure_id=toggles.get("pure_id") or False,
        ).subquery()
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.research_output_id, sqlalchemy.String),
                statement.c.title,
                statement.c.pure_id,
                statement.c.type_id,
                statement.c.language_type_id,
                statement.c.category_type_id,
            )
            .select_from(statement)
            .order_by(statement.c.research_output_id)
            .offset((page_number - 1) * page_size)
            .limit(page_size),
            conn,
        )
        return df
