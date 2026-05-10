import polars as pl
import sqlalchemy
from dash import html

from app import queries
from app.aio_components.search_aio import SearchAIO, aio_register_search
from app.client_types import AppState


def search_persons_element(aio_id="search-persons-field"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Поиск по persons"),
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
def search_persons_query(state: AppState, pattern: str, toggles: dict[str, bool]) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.query_persons(
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
            .limit(100),
            conn,
        )
        return df
