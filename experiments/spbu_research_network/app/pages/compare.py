# pages/compare.py

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils import logger
from etl import db_session


dash.register_page(
    __name__,
    path="/compare",
    name="Сравнение",
)


# ============================================================
# НОРМАЛИЗАЦИЯ ID
# ============================================================

def _normalize_id(author_id):
    if not author_id:
        return ""
    if author_id.startswith("http"):
        return author_id
    return f"https://openalex.org/{author_id}"


def _short_id(author_id):
    if not author_id:
        return ""
    return author_id.rstrip("/").split("/")[-1]


# ============================================================
# ЗАГРУЗКА СПИСКА АВТОРОВ ДЛЯ DROPDOWN
# ============================================================

def _load_authors_options():
    """Список авторов для выпадающих списков (топ-200 по публикациям)."""

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
        logger.warning(f"Не удалось загрузить авторов: {e}")
        return []

    options = []
    for _, row in df.iterrows():
        short = _short_id(row["author_id"])
        options.append({
            "label": f"{row['name']} ({int(row['publications'])})",
            "value": short,
        })

    return options


# ============================================================
# МЕТРИКИ АВТОРА
# ============================================================

def _load_author_metrics(author_id):
    """Все метрики для одного автора."""

    if not author_id:
        return None

    full_id = _normalize_id(author_id)

    try:
        with db_session() as conn:

            df_name = pd.read_sql(
                "SELECT name FROM authors WHERE id = ?",
                conn,
                params=[full_id],
            )

            if df_name.empty:
                return None

            name = df_name.iloc[0]["name"]

            df_stats = pd.read_sql(
                """
                SELECT
                    COUNT(DISTINCT a.publication_id) AS publications,
                    COALESCE(SUM(p.cited_by_count), 0) AS citations
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                WHERE a.author_id = ?
                """,
                conn,
                params=[full_id],
            )

            publications = int(df_stats.iloc[0]["publications"])
            citations = int(df_stats.iloc[0]["citations"])

            df_co = pd.read_sql(
                """
                SELECT COUNT(DISTINCT a2.author_id) AS n
                FROM authorship a1
                JOIN authorship a2 ON a1.publication_id = a2.publication_id
                WHERE a1.author_id = ? AND a2.author_id != ?
                """,
                conn,
                params=[full_id, full_id],
            )

            coauthors = int(df_co.iloc[0]["n"])

            df_topics = pd.read_sql(
                """
                SELECT p.topics
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                WHERE a.author_id = ?
                  AND p.topics IS NOT NULL
                  AND p.topics != ''
                """,
                conn,
                params=[full_id],
            )

            df_years = pd.read_sql(
                """
                SELECT p.publication_year AS year, COUNT(*) AS n
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                WHERE a.author_id = ?
                  AND p.publication_year IS NOT NULL
                GROUP BY p.publication_year
                ORDER BY p.publication_year
                """,
                conn,
                params=[full_id],
            )

        topics = []
        for row in df_topics["topics"].dropna():
            for t in row.split(";"):
                t = t.strip()
                if t and t not in topics:
                    topics.append(t)

        return {
            "id": full_id,
            "short_id": _short_id(full_id),
            "name": name,
            "publications": publications,
            "citations": citations,
            "coauthors": coauthors,
            "topics": topics,
            "years": df_years,
        }

    except Exception as e:
        logger.warning(f"Не удалось загрузить метрики {author_id}: {e}")
        return None


# ============================================================
# КОМПОНЕНТЫ
# ============================================================

def _metric_row(label, v1, v2):
    """Строка сравнения метрики."""

    try:
        diff = v2 - v1
    except Exception:
        diff = 0

    diff_sign = "+" if diff > 0 else ""
    diff_class = (
        "compare-diff-positive" if diff > 0
        else ("compare-diff-negative" if diff < 0 else "")
    )

    return html.Div(
        className="compare-metric-row",
        children=[
            html.Div(label, className="compare-metric-label"),
            html.Div(f"{v1:,}", className="compare-metric-value"),
            html.Div(f"{v2:,}", className="compare-metric-value"),
            html.Div(
                f"{diff_sign}{diff:,}",
                className=f"compare-metric-diff {diff_class}",
            ),
        ],
    )


def _author_card(author, color):
    """Карточка автора сверху."""

    if not author:
        return html.Div(
            className="compare-author-card compare-author-empty",
            children="Автор не выбран",
        )

    return html.Div(
        className="compare-author-card",
        children=[
            html.Div(
                className="compare-author-name",
                children=[
                    html.Span("👤", className="compare-author-icon"),
                    html.Span(author["name"]),
                ],
            ),
            html.Div(
                className="compare-author-stats",
                children=[
                    html.Span(
                        f"{author['publications']} публ.",
                        className="compare-author-stat",
                    ),
                    html.Span(
                        f"{author['citations']} цит.",
                        className="compare-author-stat",
                    ),
                    html.Span(
                        f"{author['coauthors']} соавт.",
                        className="compare-author-stat",
                    ),
                ],
            ),
            html.Div(
                className="compare-author-actions",
                children=[
                    dbc.Button(
                        "Профиль",
                        href=f"/author/{author['short_id']}",
                        color="primary",
                        size="sm",
                        className="compare-author-btn",
                    ),
                    dbc.Button(
                        "В сети",
                        href=f"/network?author={author['short_id']}",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="compare-author-btn",
                    ),
                ],
            ),
        ],
    )


def _topics_block(a1, a2):
    """Общие и уникальные темы двух авторов."""

    if not a1 or not a2:
        return html.Div()

    t1 = set(a1["topics"])
    t2 = set(a2["topics"])

    common = sorted(t1 & t2)
    only1 = sorted(t1 - t2)[:8]
    only2 = sorted(t2 - t1)[:8]

    def _tags(items, cls=""):
        if not items:
            return html.Div("—", className="filter-help")
        return html.Div(
            [html.Span(t, className=f"topic-tag {cls}".strip()) for t in items],
            className="compare-topics-tags",
        )

    return html.Div(
        className="compare-topics-grid",
        children=[
            html.Div(
                className="compare-topics-col",
                children=[
                    html.Div(
                        "Общие темы",
                        className="compare-topics-title",
                    ),
                    _tags(common, "topic-tag-common"),
                ],
            ),
            html.Div(
                className="compare-topics-col",
                children=[
                    html.Div(
                        f"Только у {a1['name'].split()[0]}",
                        className="compare-topics-title",
                    ),
                    _tags(only1),
                ],
            ),
            html.Div(
                className="compare-topics-col",
                children=[
                    html.Div(
                        f"Только у {a2['name'].split()[0]}",
                        className="compare-topics-title",
                    ),
                    _tags(only2),
                ],
            ),
        ],
    )


def _activity_chart(a1, a2):
    """График динамики публикаций двух авторов."""

    fig = go.Figure()

    if a1 is not None and not a1["years"].empty:
        fig.add_trace(
            go.Scatter(
                x=a1["years"]["year"],
                y=a1["years"]["n"],
                mode="lines+markers",
                name=a1["name"],
                line=dict(color="#3B82F6", width=2),
                marker=dict(size=6),
            )
        )

    if a2 is not None and not a2["years"].empty:
        fig.add_trace(
            go.Scatter(
                x=a2["years"]["year"],
                y=a2["years"]["n"],
                mode="lines+markers",
                name=a2["name"],
                line=dict(color="#E74C3C", width=2),
                marker=dict(size=6),
            )
        )

    fig.update_layout(
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#eef0f3", title=None),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=12, color="#555b64"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=320,
    )

    return fig


def _empty_state():
    return html.Div(
        className="empty-state",
        children=[
            html.Div("⚖️", className="empty-state-icon"),
            html.Div(
                "Выберите двух авторов",
                className="empty-state-title",
            ),
            html.Div(
                "Используйте выпадающие списки выше, чтобы сравнить исследователей",
                className="empty-state-subtitle",
            ),
        ],
    )


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="page",
    children=[

        # ✅ Свой Location для этой страницы
        dcc.Location(id="compare-url", refresh=False),

        # ---------- Заголовок ----------
        html.Div(
            className="page-header",
            children=[
                html.H1("Сравнение авторов", className="page-title"),
                html.Div(
                    "Сравните показатели, темы и динамику публикаций двух исследователей",
                    className="page-subtitle",
                ),
            ],
        ),

        # ---------- Выбор авторов ----------
        html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-body",
                    children=[
                        html.Div(
                            className="compare-selectors",
                            children=[
                                html.Div(
                                    className="compare-selector",
                                    children=[
                                        html.Label(
                                            "Первый автор",
                                            className="filter-label",
                                        ),
                                        dcc.Dropdown(
                                            id="compare-author-1",
                                            options=_load_authors_options(),
                                            value=None,
                                            placeholder="Выберите автора...",
                                            clearable=True,
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="compare-selector",
                                    children=[
                                        html.Label(
                                            "Второй автор",
                                            className="filter-label",
                                        ),
                                        dcc.Dropdown(
                                            id="compare-author-2",
                                            options=_load_authors_options(),
                                            value=None,
                                            placeholder="Выберите автора...",
                                            clearable=True,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        # ---------- Контент ----------
        html.Div(id="compare-content", children=_empty_state()),
    ],
)


# ============================================================
# CALLBACK
# ============================================================

@callback(
    Output("compare-content", "children"),
    Input("compare-author-1", "value"),
    Input("compare-author-2", "value"),
)
def render_compare(a1_id, a2_id):

    if not a1_id and not a2_id:
        return _empty_state()

    a1 = _load_author_metrics(a1_id) if a1_id else None
    a2 = _load_author_metrics(a2_id) if a2_id else None

    # ---- Карточки ----
    cards = html.Div(
        className="compare-cards",
        children=[
            _author_card(a1, "#3B82F6"),
            _author_card(a2, "#E74C3C"),
        ],
    )

    # ---- Таблица метрик ----
    if a1 and a2:
        metrics_table = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header",
                    children=html.H3(
                        "Сравнительные показатели",
                        className="panel-title",
                    ),
                ),
                html.Div(
                    className="panel-body",
                    children=[
                        html.Div(
                            className="compare-metric-row compare-metric-header",
                            children=[
                                html.Div("Метрика", className="compare-metric-label"),
                                html.Div("Автор 1", className="compare-metric-value"),
                                html.Div("Автор 2", className="compare-metric-value"),
                                html.Div("Разница", className="compare-metric-diff"),
                            ],
                        ),
                        _metric_row(
                            "Публикации",
                            a1["publications"],
                            a2["publications"],
                        ),
                        _metric_row(
                            "Цитирования",
                            a1["citations"],
                            a2["citations"],
                        ),
                        _metric_row(
                            "Соавторы",
                            a1["coauthors"],
                            a2["coauthors"],
                        ),
                    ],
                ),
            ],
        )

        # ---- Темы ----
        topics_panel = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header",
                    children=html.H3(
                        "Научные темы",
                        className="panel-title",
                    ),
                ),
                html.Div(
                    className="panel-body",
                    children=_topics_block(a1, a2),
                ),
            ],
        )

        # ---- Динамика ----
        activity_panel = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header",
                    children=html.H3(
                        "Динамика публикаций",
                        className="panel-title",
                    ),
                ),
                html.Div(
                    className="panel-body",
                    children=dcc.Graph(
                        figure=_activity_chart(a1, a2),
                        config={"displayModeBar": False},
                    ),
                ),
            ],
        )

        return html.Div(
            [
                cards,
                metrics_table,
                html.Div(
                    className="compare-grid",
                    children=[
                        topics_panel,
                        activity_panel,
                    ],
                ),
            ]
        )

    # ---- Только один автор ----
    return html.Div(
        [
            cards,
            html.Div(
                "Выберите второго автора для полного сравнения",
                className="filter-help",
                style={"textAlign": "center", "padding": "20px"},
            ),
        ]
    )