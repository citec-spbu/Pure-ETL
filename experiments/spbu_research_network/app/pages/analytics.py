# pages/analytics.py

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from utils import logger
from etl import db_session


dash.register_page(
    __name__,
    path="/analytics",
    name="Аналитика",
)


TOPICS_LIMIT = 20
AUTHORS_LIMIT = 10


# ============================================================
# ЗАГРУЗКА СПИСКОВ ДЛЯ ФИЛЬТРОВ
# ============================================================

def _load_years_range():
    """Диапазон лет из БД."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT MIN(publication_year) AS y_min,
                       MAX(publication_year) AS y_max
                FROM publications
                WHERE publication_year IS NOT NULL
                """,
                conn,
            )
        y_min = int(df.iloc[0]["y_min"] or 2000)
        y_max = int(df.iloc[0]["y_max"] or 2026)
        return y_min, y_max
    except Exception as e:
        logger.warning(f"Не удалось загрузить годы: {e}")
        return 2000, 2026


def _load_topics_options():
    """Топ-N topics для фильтра."""

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
        for t in row.split(";"):
            t = t.strip()
            if t:
                counter[t] = counter.get(t, 0) + 1

    top = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in top[:TOPICS_LIMIT]]


# ============================================================
# ЗАГРУЗКА ДАННЫХ ПО ФИЛЬТРАМ
# ============================================================

def _build_where(year_from, year_to, topic):
    """Собирает WHERE-условие и параметры."""

    where = "WHERE p.publication_year IS NOT NULL"
    params = []

    if year_from is not None:
        where += " AND p.publication_year >= ?"
        params.append(year_from)

    if year_to is not None:
        where += " AND p.publication_year <= ?"
        params.append(year_to)

    if topic:
        where += " AND p.topics LIKE ?"
        params.append(f"%{topic}%")

    return where, params


def _load_activity(year_from, year_to, topic):
    """Публикации по годам (БЕЗ цитирований)."""

    where, params = _build_where(year_from, year_to, topic)

    try:
        with db_session() as conn:
            df = pd.read_sql(
                f"""
                SELECT
                    p.publication_year AS year,
                    COUNT(DISTINCT p.id) AS publications
                FROM publications p
                {where}
                GROUP BY p.publication_year
                ORDER BY p.publication_year
                """,
                conn,
                params=params,
            )
        return df
    except Exception as e:
        logger.warning(f"Не удалось загрузить активность: {e}")
        return pd.DataFrame(columns=["year", "publications"])


def _load_top_topics(year_from, year_to):
    """Топ направлений за период."""

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT topics FROM publications
                WHERE publication_year IS NOT NULL
                  AND publication_year >= ?
                  AND publication_year <= ?
                  AND topics IS NOT NULL
                  AND topics != ''
                """,
                conn,
                params=[year_from, year_to],
            )
    except Exception as e:
        logger.warning(f"Не удалось загрузить топ тем: {e}")
        return []

    counter = {}
    for row in df["topics"].dropna():
        for t in row.split(";"):
            t = t.strip()
            if t:
                counter[t] = counter.get(t, 0) + 1

    return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:8]


def _load_top_authors(year_from, year_to, topic):
    """Топ исследователей за период."""

    where, params = _build_where(year_from, year_to, topic)

    try:
        with db_session() as conn:
            df = pd.read_sql(
                f"""
                SELECT
                    au.id AS author_id,
                    au.name,
                    COUNT(DISTINCT p.id) AS publications,
                    COALESCE(SUM(p.cited_by_count), 0) AS citations
                FROM publications p
                JOIN authorship a ON a.publication_id = p.id
                JOIN authors au ON au.id = a.author_id
                {where}
                GROUP BY au.id, au.name
                ORDER BY publications DESC
                LIMIT ?
                """,
                conn,
                params=params + [AUTHORS_LIMIT],
            )
        return df.to_dict("records")
    except Exception as e:
        logger.warning(f"Не удалось загрузить топ авторов: {e}")
        return []


def _load_growth_topics():
    """
    Растущие/падающие направления.

    Логика:
    - recent = последние 3 года (y_max-2..y_max)
    - prev   = предыдущие 3 года (y_max-5..y_max-3)
    - change = (recent - prev) / max(prev, 1) * 100
    - отбрасываем темы с <3 публикациями в обоих периодах
    """

    try:
        with db_session() as conn:

            df_range = pd.read_sql(
                """
                SELECT MAX(publication_year) AS y_max
                FROM publications
                WHERE publication_year IS NOT NULL
                """,
                conn,
            )
            y_max = int(df_range.iloc[0]["y_max"] or 2026)

            recent_from = y_max - 2
            recent_to = y_max
            prev_from = y_max - 5
            prev_to = y_max - 3

            df = pd.read_sql(
                """
                SELECT publication_year AS year, topics
                FROM publications
                WHERE publication_year IS NOT NULL
                  AND publication_year >= ?
                  AND topics IS NOT NULL
                  AND topics != ''
                """,
                conn,
                params=[prev_from],
            )

    except Exception as e:
        logger.warning(f"Не удалось загрузить динамику тем: {e}")
        return [], None, None, None, None

    recent = {}
    prev = {}

    for _, row in df.iterrows():
        year = row["year"]
        bucket = recent if year >= recent_from else prev
        for t in row["topics"].split(";"):
            t = t.strip()
            if t:
                bucket[t] = bucket.get(t, 0) + 1

    growth = []

    for topic, count_recent in recent.items():
        count_prev = prev.get(topic, 0)

        # Фильтр шума
        if count_recent < 3 and count_prev < 3:
            continue

        if count_prev == 0:
            change = 100.0 if count_recent > 0 else 0.0
        else:
            change = (count_recent - count_prev) / count_prev * 100

        growth.append((topic, count_recent, count_prev, change))

    growth.sort(key=lambda x: x[3], reverse=True)

    # Топ-5 растущих + топ-5 падающих
    top_growing = [g for g in growth if g[3] > 0][:5]
    top_falling = [g for g in growth if g[3] < 0][-5:]
    top_falling.reverse()

    result = top_growing + top_falling

    return result, recent_from, recent_to, prev_from, prev_to


# ============================================================
# КОМПОНЕНТЫ
# ============================================================

def _activity_chart(df):
    """График публикаций по годам (только публикации)."""

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["year"],
            y=df["publications"],
            marker_color="#33383F",
            hovertemplate="%{x}: %{y} публикаций<extra></extra>",
        )
    )

    fig.update_layout(
        margin=dict(l=20, r=20, t=10, b=40),
        xaxis=dict(
            showgrid=False,
            title=None,
            tickmode="linear",
            dtick=5,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#eef0f3",
            title=None,
            tickformat="d",       # целые числа
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=12, color="#555b64"),
        showlegend=False,
        height=340,
    )

    return fig


def _topics_list(items):
    """Топ направлений — с прогресс-барами."""

    if not items:
        return html.Div("Нет данных", className="filter-help")

    max_count = max(c for _, c in items) or 1

    return html.Div(
        [
            html.Div(
                className="analytics-topic-row",
                children=[
                    html.Div(
                        className="analytics-topic-name",
                        children=topic,
                    ),
                    html.Div(
                        className="analytics-topic-bar",
                        children=html.Div(
                            className="analytics-topic-bar-fill",
                            style={"width": f"{count / max_count * 100}%"},
                        ),
                    ),
                    html.Div(
                        className="analytics-topic-count",
                        children=str(count),
                    ),
                ],
            )
            for topic, count in items
        ]
    )


def _authors_list(authors):
    """Топ авторов."""

    if not authors:
        return html.Div("Нет данных", className="filter-help")

    return html.Div(
        [
            html.A(
                href=f"/author/{a['author_id'].rstrip('/').split('/')[-1]}",
                className="analytics-author-row",
                children=[
                    html.Div(
                        className="analytics-author-rank",
                        children=str(i + 1),
                    ),
                    html.Div(
                        className="analytics-author-name",
                        children=a["name"],
                    ),
                    html.Div(
                        className="analytics-author-stats",
                        children=[
                            html.Span(
                                f"{int(a['publications'])} публ.",
                                className="analytics-author-stat",
                            ),
                            html.Span(
                                f"{int(a['citations'])} цит.",
                                className="analytics-author-stat",
                            ),
                        ],
                    ),
                ],
            )
            for i, a in enumerate(authors)
        ]
    )


def _growth_list(items, recent_from, recent_to, prev_from, prev_to):
    """Растущие/падающие с абсолютными значениями."""

    if not items:
        return html.Div("Нет данных", className="filter-help")

    rows = []

    for topic, count_recent, count_prev, change in items:

        if change > 0:
            icon = "📈"
            cls = "analytics-growth-positive"
            sign = "+"
        elif change < 0:
            icon = "📉"
            cls = "analytics-growth-negative"
            sign = ""
        else:
            icon = "➖"
            cls = ""
            sign = ""

        rows.append(
            html.Div(
                className="analytics-growth-row",
                children=[
                    html.Span(icon, className="analytics-growth-icon"),
                    html.Div(
                        className="analytics-growth-main",
                        children=[
                            html.Div(
                                topic,
                                className="analytics-growth-name",
                            ),
                            html.Div(
                                f"{count_prev} → {count_recent} публ.",
                                className="analytics-growth-detail",
                            ),
                        ],
                    ),
                    html.Span(
                        f"{sign}{change:.0f}%",
                        className=f"analytics-growth-diff {cls}",
                    ),
                ],
            )
        )

    return html.Div(
        [
            html.Div(
                f"Сравнение {recent_from}–{recent_to} с {prev_from}–{prev_to}",
                className="analytics-growth-subtitle",
            ),
            html.Div(rows),
        ]
    )


# ============================================================
# LAYOUT
# ============================================================

_y_min, _y_max = _load_years_range()


layout = html.Div(
    className="page",
    children=[

        dcc.Location(id="analytics-url", refresh=False),

        html.Div(
            className="page-header",
            children=[
                html.H1("Аналитика", className="page-title"),
                html.Div(
                    "Общая динамика публикаций и научных направлений СПбГУ",
                    className="page-subtitle",
                ),
            ],
        ),

        # ---------- Фильтры ----------
        html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-body",
                    children=[
                        html.Div(
                            className="analytics-filters",
                            children=[
                                html.Div(
                                    className="analytics-filter",
                                    children=[
                                        html.Label("Период", className="filter-label"),
                                        dcc.RangeSlider(
                                            id="analytics-years",
                                            min=_y_min,
                                            max=_y_max,
                                            value=[_y_min, _y_max],
                                            step=1,
                                            marks={
                                                _y_min: str(_y_min),
                                                _y_max: str(_y_max),
                                            },
                                            tooltip={"placement": "bottom", "always_visible": False},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="analytics-filter",
                                    children=[
                                        html.Label(
                                            "Научное направление",
                                            className="filter-label",
                                        ),
                                        dcc.Dropdown(
                                            id="analytics-topic",
                                            options=[
                                                {"label": "Все направления", "value": ""}
                                            ] + [
                                                {"label": t, "value": t}
                                                for t in _load_topics_options()
                                            ],
                                            value="",
                                            clearable=False,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),

        html.Div(id="analytics-content"),
    ],
)


# ============================================================
# CALLBACK
# ============================================================

@callback(
    Output("analytics-content", "children"),
    Input("analytics-url", "pathname"),
    Input("analytics-years", "value"),
    Input("analytics-topic", "value"),
)
def render_analytics(pathname, years, topic):

    year_from, year_to = years if years else (_y_min, _y_max)
    topic = topic or ""

    activity = _load_activity(year_from, year_to, topic)
    topics = _load_top_topics(year_from, year_to)
    authors = _load_top_authors(year_from, year_to, topic)
    growth_result = _load_growth_topics()

    growth, recent_from, recent_to, prev_from, prev_to = growth_result

    # ---- Основной график ----
    if activity.empty:
        activity_block = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header",
                    children=html.H3(
                        "Публикационная активность по годам",
                        className="panel-title",
                    ),
                ),
                html.Div(
                    className="panel-body",
                    children=html.Div(
                        "Нет данных за выбранный период",
                        className="filter-help",
                    ),
                ),
            ],
        )
    else:
        activity_block = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header",
                    children=html.H3(
                        "Публикационная активность по годам",
                        className="panel-title",
                    ),
                ),
                html.Div(
                    className="panel-body",
                    children=dcc.Graph(
                        figure=_activity_chart(activity),
                        config={"displayModeBar": False},
                    ),
                ),
            ],
        )

    # ---- Топ направлений ----
    topics_block = html.Div(
        className="panel",
        children=[
            html.Div(
                className="panel-header",
                children=html.H3(
                    f"Топ направлений · {year_from}–{year_to}",
                    className="panel-title",
                ),
            ),
            html.Div(
                className="panel-body",
                children=_topics_list(topics),
            ),
        ],
    )

    # ---- Топ авторов ----
    if topic:
        authors_title = f"Топ исследователей · {topic}"
    else:
        authors_title = "Топ исследователей · все направления"

    authors_block = html.Div(
        className="panel",
        children=[
            html.Div(
                className="panel-header",
                children=html.H3(
                    authors_title,
                    className="panel-title",
                ),
            ),
            html.Div(
                className="panel-body",
                children=_authors_list(authors),
            ),
        ],
    )

    # ---- Растущие/падающие ----
    growth_block = html.Div(
        className="panel",
        children=[
            html.Div(
                className="panel-header",
                children=html.H3(
                    "Растущие и падающие направления",
                    className="panel-title",
                ),
            ),
            html.Div(
                className="panel-body",
                children=_growth_list(
                    growth,
                    recent_from,
                    recent_to,
                    prev_from,
                    prev_to,
                ),
            ),
        ],
    )

    return html.Div(
        [
            activity_block,
            html.Div(
                className="analytics-grid-2",
                children=[
                    topics_block,
                    authors_block,
                ],
            ),
            growth_block,
        ]
    )