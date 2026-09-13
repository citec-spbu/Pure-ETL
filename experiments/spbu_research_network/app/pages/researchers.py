# pages/researchers.py

import math
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import pandas as pd

from utils import logger
from etl import db_session


dash.register_page(
    __name__,
    path="/researchers",
    name="Исследователи",
)


# ============================================================
# КОНСТАНТЫ
# ============================================================

PAGE_SIZE = 20
TOP_TOPICS_LIMIT = 20


# ============================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================

def _load_topics():
    """Возвращает топ-N topics для фильтра."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT topics FROM publications
                WHERE topics IS NOT NULL AND topics != ''
                """,
                conn,
            )

        counter = {}
        for row in df["topics"].dropna():
            for topic in row.split(";"):
                topic = topic.strip()
                if topic:
                    counter[topic] = counter.get(topic, 0) + 1

        top = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        return [t for t, _ in top[:TOP_TOPICS_LIMIT]]

    except Exception as e:
        logger.warning(f"Не удалось загрузить topics: {e}")
        return []


def _load_all_authors_options():
    """Список всех авторов для автокомплита (топ-500 по публикациям)."""

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
                LIMIT 500
                """,
                conn,
            )
    except Exception as e:
        logger.warning(f"Не удалось загрузить авторов для поиска: {e}")
        return []

    options = []
    for _, row in df.iterrows():
        options.append({
            "label": row["name"],
            "value": row["name"],   # ищем по имени
        })

    return options


def _load_authors(search="", topic="", sort_by="publications", page=0):
    """
    Возвращает (список авторов, общее количество).
    """

    try:
        with db_session() as conn:

            query = """
                SELECT
                    a.author_id,
                    au.name,
                    COUNT(DISTINCT a.publication_id) AS publications,
                    COALESCE(SUM(p.cited_by_count), 0) AS citations
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                JOIN authors au ON au.id = a.author_id
                WHERE 1=1
            """
            params = []

            if search:
                query += " AND LOWER(au.name) LIKE ?"
                params.append(f"%{search.lower()}%")

            if topic:
                query += """
                    AND a.author_id IN (
                        SELECT a2.author_id
                        FROM authorship a2
                        JOIN publications p2 ON p2.id = a2.publication_id
                        WHERE p2.topics LIKE ?
                    )
                """
                params.append(f"%{topic}%")

            query += " GROUP BY a.author_id, au.name"

            if sort_by == "citations":
                query += " ORDER BY citations DESC"
            elif sort_by == "name":
                query += " ORDER BY au.name ASC"
            else:
                query += " ORDER BY publications DESC"

            df = pd.read_sql(query, conn, params=params)

        if df.empty:
            return [], 0

        total = len(df)

        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        df_page = df.iloc[start:end]

        author_ids = df_page["author_id"].tolist()
        topics_map = _load_author_topics(author_ids)

        authors = []
        for _, row in df_page.iterrows():
            authors.append({
                "id": row["author_id"],
                "name": row["name"],
                "publications": int(row["publications"]),
                "citations": int(row["citations"]),
                "topics": topics_map.get(row["author_id"], []),
            })

        return authors, total

    except Exception as e:
        logger.warning(f"Не удалось загрузить авторов: {e}")
        return [], 0


def _load_author_topics(author_ids):
    """Возвращает {author_id: [topic1, topic2, ...]} для списка авторов."""

    if not author_ids:
        return {}

    try:
        with db_session() as conn:
            placeholders = ",".join("?" * len(author_ids))
            df = pd.read_sql(
                f"""
                SELECT a.author_id, p.topics
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                WHERE a.author_id IN ({placeholders})
                  AND p.topics IS NOT NULL
                  AND p.topics != ''
                """,
                conn,
                params=author_ids,
            )

        result = {}
        for author_id, topics_str in zip(df["author_id"], df["topics"]):
            if author_id not in result:
                result[author_id] = []
            for topic in topics_str.split(";"):
                topic = topic.strip()
                if topic and topic not in result[author_id]:
                    result[author_id].append(topic)

        for k in result:
            result[k] = result[k][:3]

        return result

    except Exception as e:
        logger.warning(f"Не удалось загрузить topics авторов: {e}")
        return {}


# ============================================================
# КОМПОНЕНТЫ
# ============================================================

def _author_card(author):

    topics = author.get("topics", [])
    topics_ui = html.Div(
        [html.Span(t, className="topic-tag") for t in topics]
    ) if topics else html.Div("Темы не указаны", className="filter-help")

    short_id = author["id"].rstrip("/").split("/")[-1]

    return html.Div(
        className="author-card",
        children=[
            html.Div(
                className="author-card-name",
                children=[
                    html.Span("👤", className="author-card-icon"),
                    html.Span(author["name"]),
                ],
            ),

            html.Div(
                className="author-card-metrics",
                children=[
                    html.Div(
                        className="author-card-metric",
                        children=[
                            html.Div(
                                f"{author['publications']:,}",
                                className="author-card-metric-value",
                            ),
                            html.Div(
                                "публикаций",
                                className="author-card-metric-label",
                            ),
                        ],
                    ),
                    html.Div(
                        className="author-card-metric",
                        children=[
                            html.Div(
                                f"{author['citations']:,}",
                                className="author-card-metric-value",
                            ),
                            html.Div(
                                "цитирований",
                                className="author-card-metric-label",
                            ),
                        ],
                    ),
                ],
            ),

            html.Div(
                className="author-card-topics",
                children=topics_ui,
            ),

            html.Div(
                className="author-card-actions",
                children=[
                    dbc.Button(
                        "Профиль",
                        href=f"/author/{short_id}",
                        color="primary",
                        size="sm",
                        className="author-card-btn",
                    ),
                    dbc.Button(
                        "В сети",
                        href=f"/network?author={short_id}",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="author-card-btn",
                    ),
                ],
            ),
        ],
    )


def _empty_state():
    return html.Div(
        className="empty-state",
        children=[
            html.Div("🔍", className="empty-state-icon"),
            html.Div("Ничего не найдено", className="empty-state-title"),
            html.Div(
                "Попробуйте изменить поиск или фильтры",
                className="empty-state-subtitle",
            ),
        ],
    )


def _pagination(page, total, page_size):

    total_pages = max(1, math.ceil(total / page_size))

    return html.Div(
        className="pagination",
        children=[
            dbc.Button(
                "← Назад",
                id="page-prev",
                disabled=(page <= 0),
                size="sm",
                color="light",
                className="pagination-btn",
            ),
            html.Div(
                f"Страница {page + 1} из {total_pages}",
                className="pagination-info",
            ),
            dbc.Button(
                "Вперёд →",
                id="page-next",
                disabled=(page >= total_pages - 1),
                size="sm",
                color="light",
                className="pagination-btn",
            ),
        ],
    )


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="page",
    children=[

        # ✅ Свой Location
        dcc.Location(id="researchers-url", refresh=False),

        # ---------- Заголовок ----------
        html.Div(
            className="page-header",
            children=[
                html.H1("Исследователи", className="page-title"),
                html.Div(
                    "Поиск и изучение авторов СПбГУ",
                    className="page-subtitle",
                ),
            ],
        ),

        # ---------- Панель фильтров ----------
        html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-body",
                    children=[
                        html.Div(
                            className="researchers-toolbar",
                            children=[

                                # ✅ Поиск — Dropdown
                                dcc.Dropdown(
                                    id="researchers-search",
                                    options=_load_all_authors_options(),
                                    value=None,
                                    placeholder="🔍  Поиск по имени...",
                                    searchable=True,
                                    clearable=True,
                                    className="researchers-search-dropdown",
                                ),

                                # Фильтр по теме
                                dcc.Dropdown(
                                    id="researchers-topic",
                                    options=[
                                        {"label": "Все направления", "value": ""}
                                    ] + [
                                        {"label": t, "value": t}
                                        for t in _load_topics()
                                    ],
                                    value="",
                                    clearable=False,
                                    className="researchers-dropdown",
                                ),

                                # ✅ Сортировка — первый пункт "Сортировка"
                                dcc.Dropdown(
                                    id="researchers-sort",
                                    options=[
                                        {"label": "По числу публикаций", "value": "publications"},
                                        {"label": "По числу цитирований", "value": "citations"},
                                    ],
                                    value= None,
                                    placeholder="Сортировка",
                                    clearable=False,
                                    searchable=False,
                                    className="researchers-dropdown researchers-sort-dropdown",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        # ---------- Счётчик ----------
        html.Div(
            id="researchers-count",
            className="researchers-count",
        ),

        # ---------- Сетка карточек ----------
        html.Div(
            id="researchers-grid",
            className="researchers-grid",
        ),

        # ---------- Пагинация ----------
        html.Div(id="researchers-pagination"),

        # ---------- Хранилище текущей страницы ----------
        dcc.Store(id="researchers-page", data=0),
    ],
)


# ============================================================
# CALLBACK: пагинация
# ============================================================

@callback(
    Output("researchers-page", "data"),
    Input("page-prev", "n_clicks"),
    Input("page-next", "n_clicks"),
    State("researchers-page", "data"),
    prevent_initial_call=True,
)
def change_page(prev_clicks, next_clicks, current_page):
    from dash import ctx

    triggered = ctx.triggered_id

    if triggered == "page-prev" and current_page > 0:
        return current_page - 1
    if triggered == "page-next":
        return current_page + 1
    return current_page


# ============================================================
# CALLBACK: сброс страницы при смене фильтров
# ============================================================

@callback(
    Output("researchers-page", "data", allow_duplicate=True),
    Input("researchers-search", "value"),
    Input("researchers-topic", "value"),
    Input("researchers-sort", "value"),
    prevent_initial_call=True,
)
def reset_page(search, topic, sort_by):
    return 0


# ============================================================
# CALLBACK: рендер карточек
# ============================================================

@callback(
    Output("researchers-grid", "children"),
    Output("researchers-count", "children"),
    Output("researchers-pagination", "children"),
    Input("researchers-url", "pathname"),
    Input("researchers-search", "value"),
    Input("researchers-topic", "value"),
    Input("researchers-sort", "value"),
    Input("researchers-page", "data"),
)
def render_authors(pathname, search, topic, sort_by, page):

    search = (search or "").strip()
    topic = topic or ""
    sort_by = sort_by or "publications"
    page = page or 0

    authors, total = _load_authors(
        search=search,
        topic=topic,
        sort_by=sort_by,
        page=page,
    )

    if not authors:
        return (
            _empty_state(),
            "Ничего не найдено",
            "",
        )

    cards = [_author_card(a) for a in authors]

    start = page * PAGE_SIZE + 1
    end = min((page + 1) * PAGE_SIZE, total)
    count_text = f"Показано {start}–{end} из {total}"

    pagination = _pagination(page, total, PAGE_SIZE)

    return cards, count_text, pagination