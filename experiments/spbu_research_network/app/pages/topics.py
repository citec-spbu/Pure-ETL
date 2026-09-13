# pages/topics.py

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from urllib.parse import quote

from utils import logger
from etl import db_session


dash.register_page(
    __name__,
    path="/topics",
    name="Темы",
)


TOPICS_LIMIT = 100


# ============================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================

def _load_topics_list():
    """Список всех topics с количеством публикаций."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT topics FROM publications
                WHERE topics IS NOT NULL AND topics != ''
                """,
                conn,
            )
    except Exception as e:
        logger.warning(f"Не удалось загрузить topics: {e}")
        return []

    counter = {}
    for row in df["topics"].dropna():
        for topic in row.split(";"):
            topic = topic.strip()
            if topic:
                counter[topic] = counter.get(topic, 0) + 1

    return sorted(counter.items(), key=lambda x: x[1], reverse=True)


def _load_topics_options():
    """Топ-N topics для dropdown."""
    topics = _load_topics_list()[:TOPICS_LIMIT]
    return [
        {"label": f"{t} ({c})", "value": t}
        for t, c in topics
    ]


def _load_topic_activity(topic):
    """Динамика публикаций по годам для темы."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT publication_year AS year, COUNT(*) AS n
                FROM publications
                WHERE topics LIKE ?
                  AND publication_year IS NOT NULL
                GROUP BY publication_year
                ORDER BY publication_year
                """,
                conn,
                params=[f"%{topic}%"],
            )
        return df
    except Exception as e:
        logger.warning(f"Не удалось загрузить активность темы: {e}")
        return pd.DataFrame(columns=["year", "n"])


def _load_topic_authors(topic):
    """ВСЕ авторы темы, отсортированные по публикациям."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT
                    au.id AS author_id,
                    au.name,
                    COUNT(DISTINCT a.publication_id) AS publications,
                    COALESCE(SUM(p.cited_by_count), 0) AS citations
                FROM publications p
                JOIN authorship a ON a.publication_id = p.id
                JOIN authors au ON au.id = a.author_id
                WHERE p.topics LIKE ?
                GROUP BY au.id, au.name
                ORDER BY publications DESC
                """,
                conn,
                params=[f"%{topic}%"],
            )
        return df.to_dict("records")
    except Exception as e:
        logger.warning(f"Не удалось загрузить авторов темы: {e}")
        return []


def _load_topic_stats(topic):
    """Общая статистика по теме."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT
                    COUNT(DISTINCT p.id) AS publications,
                    COALESCE(SUM(p.cited_by_count), 0) AS citations,
                    COUNT(DISTINCT a.author_id) AS authors
                FROM publications p
                JOIN authorship a ON a.publication_id = p.id
                WHERE p.topics LIKE ?
                """,
                conn,
                params=[f"%{topic}%"],
            )
        return df.iloc[0].to_dict()
    except Exception as e:
        logger.warning(f"Не удалось загрузить статистику темы: {e}")
        return {"publications": 0, "citations": 0, "authors": 0}


# ============================================================
# КОМПОНЕНТЫ
# ============================================================

def _empty_details():
    return html.Div(
        className="empty-state",
        children=[
            html.Div("📊", className="empty-state-icon"),
            html.Div(
                "Выберите направление",
                className="empty-state-title",
            ),
            html.Div(
                "Кликните на тему слева или найдите через поиск",
                className="empty-state-subtitle",
            ),
        ],
    )


def _metric(label, value):
    return html.Div(
        className="topic-metric",
        children=[
            html.Div(f"{value:,}", className="topic-metric-value"),
            html.Div(label, className="topic-metric-label"),
        ],
    )


def _author_row(author, idx):
    short_id = author["author_id"].rstrip("/").split("/")[-1]

    return html.A(
        href=f"/author/{short_id}",
        className="topic-author-row",
        children=[
            html.Div(
                className="topic-author-rank",
                children=str(idx),
            ),
            html.Div(
                className="topic-author-name",
                children=author["name"],
            ),
            html.Div(
                className="topic-author-stats",
                children=[
                    html.Span(
                        f"{int(author['publications'])} публ.",
                        className="topic-author-stat",
                    ),
                    html.Span(
                        f"{int(author['citations'])} цит.",
                        className="topic-author-stat",
                    ),
                ],
            ),
        ],
    )


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="page",
    children=[

        dcc.Location(id="topics-url", refresh=False),

        # ---------- Заголовок ----------
        html.Div(
            className="page-header",
            children=[
                html.H1("Научные направления", className="page-title"),
                html.Div(
                    "Темы публикаций авторов СПбГУ",
                    className="page-subtitle",
                ),
            ],
        ),

        # ---------- Основной layout ----------
        html.Div(
            className="topics-layout",
            children=[

                # Левая панель
                html.Div(
                    className="panel topics-panel",
                    children=[
                        html.Div(
                            className="panel-header",
                            children=html.H3(
                                "Все направления",
                                className="panel-title",
                            ),
                        ),
                        html.Div(
                            className="panel-body topics-panel-body",
                            children=[
                                dcc.Dropdown(
                                    id="topics-search",
                                    options=_load_topics_options(),
                                    value=None,
                                    placeholder="🔍  Поиск темы...",
                                    searchable=True,
                                    clearable=True,
                                    className="topics-search-dropdown",
                                ),
                                html.Div(
                                    id="topics-list-container",
                                    children=html.Div(
                                        "Выберите тему через поиск",
                                        className="filter-help",
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),

                # Правая панель
                html.Div(
                    id="topic-details",
                    className="topic-details",
                    children=_empty_details(),
                ),
            ],
        ),

        dcc.Store(id="selected-topic", data=None),
    ],
)


# ============================================================
# CALLBACK: поиск темы → выбор
# ============================================================

@callback(
    Output("selected-topic", "data"),
    Input("topics-search", "value"),
    prevent_initial_call=True,
)
def select_topic_from_search(topic):
    """Выбор темы через dropdown."""
    return topic or None


# ============================================================
# CALLBACK: рендер деталей темы
# ============================================================

@callback(
    Output("topic-details", "children"),
    Input("selected-topic", "data"),
)
def render_topic_details(topic):

    if not topic:
        return _empty_details()

    stats = _load_topic_stats(topic)
    activity = _load_topic_activity(topic)
    authors = _load_topic_authors(topic)

    # ---- Заголовок ----
    header = html.Div(
        className="topic-details-header",
        children=[
            html.H2(topic, className="topic-details-title"),
            html.Div(
                "Направление научных публикаций",
                className="topic-details-subtitle",
            ),
        ],
    )

    # ---- Метрики ----
    metrics = html.Div(
        className="topic-metrics",
        children=[
            _metric("публикаций", int(stats.get("publications", 0))),
            _metric("цитирований", int(stats.get("citations", 0))),
            _metric("авторов", int(stats.get("authors", 0))),
        ],
    )

    # ---- График ----
    fig = go.Figure()
    if not activity.empty:
        fig.add_trace(
            go.Scatter(
                x=activity["year"],
                y=activity["n"],
                mode="lines+markers",
                line=dict(color="#33383f", width=2),
                marker=dict(size=6),
                fill="tozeroy",
                fillcolor="rgba(51,56,63,0.06)",
                hovertemplate="%{x}: %{y} публикаций<extra></extra>",
            )
        )

    fig.update_layout(
        margin=dict(l=40, r=20, t=10, b=40),
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#eef0f3", title=None),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=12, color="#555b64"),
        height=260,
    )

    activity_block = html.Div(
        className="panel",
        children=[
            html.Div(
                className="panel-header",
                children=html.H3(
                    "Активность по годам",
                    className="panel-title",
                ),
            ),
            html.Div(
                className="panel-body",
                children=dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                ),
            ),
        ],
    )

    # ---- Авторы темы (ВСЕ, со скроллом) ----
    if authors:
        authors_rows = [_author_row(a, i + 1) for i, a in enumerate(authors)]
        authors_ui = html.Div(
            className="topic-authors-list",
            children=authors_rows,
        )
    else:
        authors_ui = html.Div("Авторы не найдены", className="filter-help")

    authors_block = html.Div(
        className="panel",
        children=[
            html.Div(
                className="panel-header",
                children=html.H3(
                    f"Авторы темы ({len(authors)})",
                    className="panel-title",
                ),
            ),
            html.Div(
                className="panel-body",
                children=authors_ui,
            ),
        ],
    )

    # ---- Кнопка "Показать в сети" ----
    encoded_topic = quote(topic, safe="")
    network_btn = dbc.Button(
        "🔗 Показать авторов в сети",
        href=f"/network?topic={encoded_topic}",
        color="primary",
        outline=True,
        className="topic-network-btn",
    )

    return html.Div([
        header,
        metrics,
        activity_block,
        authors_block,
        network_btn,
    ])