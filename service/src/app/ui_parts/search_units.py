import polars as pl
import sqlalchemy
from dash import html

from app import queries
from app.aio_components.search_aio import SearchAIO, aio_register_search
from app.client_types import AppState


def search_units_element(aio_id="search-units-field"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Поиск по organisational units"),
                    html.Abbr(
                        "?",
                        title="Количество результатов ограничено 100.\n"
                        "Для поиска используется PostgreSQL pattern matching. Таким образом substring просто добавляет "
                        "% в начало и в конец паттерна.\n"
                        "Можно выбрать разные колонки по которым будет производиться поиск. По умолчанию никакая из "
                        "колонок не выбрана, поэтому результат пустой. При выборе нескольких колонок используется "
                        "операция ИЛИ между ними - match должен произойти в любой из них.",
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
            ),
        ]
    )


@aio_register_search
def search_units_query(state: AppState, pattern: str, toggles: dict[str, bool]) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.query_units(
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
            .limit(100),
            conn,
        )
        return df
