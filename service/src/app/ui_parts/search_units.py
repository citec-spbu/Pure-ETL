import polars as pl
import sqlalchemy
from dash import html

import app.ui_parts
from app import queries
from app.aio_components.search_aio import SearchAIO, aio_register_search
from app.client_types import AppState


def search_units_element(aio_id="search-units-field", additional_controls=None):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H3(children="Поиск по организационным единицам"),
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
                csv_filename="organisational-units",
                column_defs=[
                    {"field": i, "colId": i}
                    for i in [
                        "organisational_unit_id",
                        "name_ru",
                        "name_en",
                        "pure_id",
                        "type_id",
                    ]
                ],
                toggles=[
                    "substring",
                    "case_insensitive",
                    "id",
                    "name_ru",
                    "name_en",
                    "pure_id",
                    "type_id",
                ],
                toggles_defaults=["substring", "case_insensitive"],
                search_function="search_units_query",
                additional_controls=additional_controls,
            ),
        ]
    )


@aio_register_search
def search_units_query(
    state: AppState,
    pattern: str,
    page_number: int,
    page_size: int,
    toggles: dict[str, bool],
) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.search.search_units(
            f"%{pattern}%" if toggles.get("substring") else str(pattern),
            case_insensitive=toggles.get("case_insensitive") or False,
            organisational_unit_id=toggles.get("id") or False,
            name_ru=toggles.get("name_ru") or False,
            name_en=toggles.get("name_en") or False,
            pure_id=toggles.get("pure_id") or False,
            type_id=toggles.get("type_id") or False,
        ).subquery()
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String),
                statement.c.name_ru,
                statement.c.name_en,
                statement.c.pure_id,
                statement.c.type_id,
            )
            .select_from(statement)
            .order_by(statement.c.organisational_unit_id)
            .offset((page_number - 1) * page_size)
            .limit(page_size),
            conn,
        )
        return df
