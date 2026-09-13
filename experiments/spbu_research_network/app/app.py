import os
import dash
from dash import html, dcc, page_container, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd

from utils import logger
from etl import ensure_data, db_session


app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    assets_folder="assets",
)

server = app.server


# ============================================================
# SEARCH: список авторов для navbar
# ============================================================

def _load_search_options():
    """Список авторов для поиска (топ-200 по публикациям)."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT
                    au.id AS author_id,
                    au.name,
                    COUNT(DISTINCT a.publication_id) AS publications
                FROM authorship a
                JOIN authors au ON au.id = a.author_id
                GROUP BY au.id, au.name
                ORDER BY publications DESC
                LIMIT 200
                """,
                conn,
            )
    except Exception as e:
        logger.warning(f"Не удалось загрузить авторов для поиска: {e}")
        return []

    options = []
    for _, row in df.iterrows():
        short_id = row["author_id"].rstrip("/").split("/")[-1]
        options.append({
            "label": f"{row['name']} ({int(row['publications'])})",
            "value": short_id,
        })

    return options


# ============================================================
# NAVIGATION
# ============================================================

NAV_ITEMS = [
    {"label": "Обзор",         "href": "/"},
    {"label": "Исследователи", "href": "/researchers"},
    {"label": "Сеть",          "href": "/network"},
    {"label": "Темы",          "href": "/topics"},
    {"label": "Аналитика",     "href": "/analytics"},
    {"label": "Сравнение",     "href": "/compare"},
]


navbar = html.Nav(
    className="app-navbar",
    children=[
        html.Div(
            className="navbar-inner",
            children=[

                # Logo
                html.A(
                    "SPBU Research Network",
                    href="/",
                    className="navbar-brand-custom",
                ),

                # Navigation
                html.Div(
                    className="navbar-links",
                    children=[
                        dcc.Link(
                            item["label"],
                            href=item["href"],
                            className="nav-link-custom",
                        )
                        for item in NAV_ITEMS
                    ],
                ),

                # Search
                html.Div(
                    className="navbar-search-wrapper",
                    children=[
                        dcc.Dropdown(
                            id="navbar-search",
                            options=_load_search_options(),
                            value=None,
                            placeholder="⌕  Найти автора",
                            searchable=True,
                            clearable=True,
                            className="navbar-search-dropdown",
                        ),
                    ],
                ),
            ],
        )
    ],
)


# ============================================================
# APP LAYOUT
# ============================================================

app.layout = html.Div(
    className="app",
    children=[

        # ✅ Location для навигации из поиска
        dcc.Location(id="search-nav", refresh=True),

        navbar,

        html.Main(
            className="main-container",
            children=[page_container],
        ),
    ],
)


# ============================================================
# CALLBACK: поиск → переход на профиль
# ============================================================

@callback(
    Output("search-nav", "pathname"),
    Input("navbar-search", "value"),
    prevent_initial_call=True,
)
def navigate_to_author(author_id):
    if not author_id:
        return dash.no_update
    return f"/author/{author_id}"


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    debug = os.environ.get("DASH_DEBUG", "0").lower() in ("1", "true", "yes")

    if os.environ.get("AUTO_ETL", "1").lower() not in ("0", "false", "no"):
        if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            try:
                ensure_data()
            except Exception as e:
                logger.error(f"Автозагрузка данных не удалась: {e}")

    logger.info(
        "Зарегистрированные страницы: %s",
        sorted(dash.page_registry.keys()),
    )

    app.run(host="0.0.0.0", port=8050, debug=debug)