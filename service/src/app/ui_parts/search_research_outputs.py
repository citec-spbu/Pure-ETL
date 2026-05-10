import polars as pl
import sqlalchemy
from dash import html

from app import queries
from app.aio_components.search_aio import SearchAIO, aio_register_search
from app.client_types import AppState


def search_research_outputs_element(aio_id="search-research-outputs-field"):
    return html.Div(
        children=[
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H2(children="Поиск по research outputs"),
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
def search_research_outputs_query(state: AppState, pattern: str, toggles: dict[str, bool]) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.query_research_outputs(
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
            .limit(100),
            conn,
        )
        return df
