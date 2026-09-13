# pages/home.py

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import plotly.graph_objects as go
import pandas as pd
import networkx as nx
import math

from utils import logger, MAIN_AUTHORS
from etl import db_session


dash.register_page(
    __name__,
    path="/",
    name="Обзор",
)


MINI_GRAPH_LIMIT = 60


# ============================================================
# СТИЛИ ГРАФА
# ============================================================

MINI_STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "width": "data(node_size)",
            "height": "data(node_size)",
            "background-color": "data(color)",
            "label": "data(label)",
            "font-size": "9px",
            "font-weight": "500",
            "text-valign": "center",
            "text-halign": "center",
            "color": "#FFFFFF",
            "text-outline-width": 1,
            "text-outline-color": "#555B63",
            "border-width": 2,
            "border-color": "#FFFFFF",
        },
    },
    {
        "selector": "node:selected",
        "style": {
            "border-width": 4,
            "border-color": "#20242A",
            "overlay-opacity": 0,
        },
    },
    {
        "selector": "edge",
        "style": {
            "width": "mapData(weight, 1, 10, 0.5, 2.5)",
            "line-color": "#C8CED6",
            "curve-style": "bezier",
            "opacity": 0.4,
        },
    },
]


COLOR_PALETTE = [
    "#6B7280",
    "#8B95A1",
    "#748091",
    "#929BA6",
    "#66717E",
    "#7C8794",
    "#9AA2AC",
]


# ============================================================
# РАСТАЛКИВАНИЕ УЗЛОВ
# ============================================================

def _push_apart(positions, min_dist=70, max_iter=50):
    """Расталкивает узлы, чтобы подписи не накладывались."""

    nodes = list(positions.keys())

    for _ in range(max_iter):
        moved = 0.0

        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx = positions[b]["x"] - positions[a]["x"]
                dy = positions[b]["y"] - positions[a]["y"]
                dist = math.hypot(dx, dy)

                if 0 < dist < min_dist:
                    push = (min_dist - dist) / 2
                    ux = dx / dist
                    uy = dy / dist

                    positions[a]["x"] -= ux * push
                    positions[a]["y"] -= uy * push
                    positions[b]["x"] += ux * push
                    positions[b]["y"] += uy * push

                    moved += push

        if moved < 0.5:
            break


# ============================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================

def _load_overview_stats():
    try:
        with db_session() as conn:
            df_authors = pd.read_sql(
                "SELECT COUNT(DISTINCT author_id) AS n FROM authorship", conn,
            )
            df_pubs = pd.read_sql("SELECT COUNT(*) AS n FROM publications", conn)
            df_cites = pd.read_sql(
                "SELECT COALESCE(SUM(cited_by_count), 0) AS n FROM publications", conn,
            )
            df_links = pd.read_sql(
                """
                SELECT COUNT(*) AS n FROM (
                    SELECT a1.author_id AS a, a2.author_id AS b
                    FROM authorship a1
                    JOIN authorship a2 ON a1.publication_id = a2.publication_id
                    WHERE a1.author_id < a2.author_id
                    GROUP BY a1.author_id, a2.author_id
                )
                """,
                conn,
            )
        return {
            "authors": int(df_authors.iloc[0]["n"]),
            "publications": int(df_pubs.iloc[0]["n"]),
            "citations": int(df_cites.iloc[0]["n"]),
            "links": int(df_links.iloc[0]["n"]),
        }
    except Exception as e:
        logger.warning(f"Не удалось загрузить обзор: {e}")
        return {"authors": 0, "publications": 0, "citations": 0, "links": 0}


def _load_mini_graph():
    """Топ-N авторов + связи + preset layout с расталкиванием."""

    try:
        with db_session() as conn:
            df_auth = pd.read_sql(
                "SELECT author_id, publication_id FROM authorship", conn,
            )
            df_authors = pd.read_sql(
                "SELECT id, name FROM authors", conn,
            )
    except Exception as e:
        logger.warning(f"Не удалось загрузить мини-граф: {e}")
        return []

    if df_auth.empty or df_authors.empty:
        return []

    author_names = dict(zip(df_authors["id"], df_authors["name"]))

    pub_counts = (
        df_auth.groupby("author_id")
        .size()
        .reset_index(name="n")
    )

    top_authors = pub_counts.nlargest(MINI_GRAPH_LIMIT, "n")["author_id"].tolist()

    df_top = df_auth[df_auth["author_id"].isin(top_authors)]

    edges = (
        df_top.merge(df_top, on="publication_id")
        .query("author_id_x < author_id_y")
        .groupby(["author_id_x", "author_id_y"])
        .size()
        .reset_index(name="weight")
    )

    # --- NetworkX layout ---
    G = nx.Graph()
    for a in top_authors:
        G.add_node(a)
    for _, row in edges.iterrows():
        G.add_edge(row["author_id_x"], row["author_id_y"], weight=int(row["weight"]))

    pos = nx.spring_layout(
        G,
        seed=42,
        k=3.0 / math.sqrt(max(len(G), 1)),
        iterations=80,
    )

    # --- Нормализация в ~[-500, 500] ---
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = (max_x - min_x) or 1
    h = (max_y - min_y) or 1

    positions = {}
    for node, (x, y) in pos.items():
        positions[node] = {
            "x": ((x - min_x) / w - 0.5) * 1000,
            "y": ((y - min_y) / h - 0.5) * 1000,
        }

    # ✅ Расталкиваем узлы
    _push_apart(positions, min_dist=70, max_iter=50)

    # --- Elements ---
    elements = []
    color_index = 0

    for a in top_authors:
        name = author_names.get(a, a)
        is_main = name in MAIN_AUTHORS

        if is_main:
            color = "#E74C3C"
        else:
            color = COLOR_PALETTE[color_index % len(COLOR_PALETTE)]
            color_index += 1

        n_pubs = int(pub_counts.loc[pub_counts["author_id"] == a, "n"].iloc[0])
        node_size = 14 + min(n_pubs, 20)

        parts = name.split()
        label = parts[-1] if len(parts) > 1 else name

        elements.append({
            "data": {
                "id": a,
                "label": label,
                "full_name": name,
                "author_id": a,
                "publications": n_pubs,
                "node_size": node_size,
                "color": color,
            },
            "position": positions[a],
        })

    for _, row in edges.iterrows():
        elements.append({
            "data": {
                "source": row["author_id_x"],
                "target": row["author_id_y"],
                "weight": int(row["weight"]),
            }
        })

    return elements


def _load_topics():
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
        logger.warning(f"Не удалось загрузить темы: {e}")
        return []

    counter = {}
    for row in df["topics"].dropna():
        for topic in row.split(";"):
            topic = topic.strip()
            if topic:
                counter[topic] = counter.get(topic, 0) + 1

    return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:8]


def _load_activity():
    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT publication_year AS year, COUNT(*) AS n
                FROM publications
                WHERE publication_year IS NOT NULL
                GROUP BY publication_year
                ORDER BY publication_year
                """,
                conn,
            )
        return df
    except Exception as e:
        logger.warning(f"Не удалось загрузить динамику: {e}")
        return pd.DataFrame(columns=["year", "n"])


# ============================================================
# КОМПОНЕНТЫ
# ============================================================

def _stat_card(label, value, icon="•"):
    return html.Div(
        className="stat-card",
        children=[
            html.Div(icon, className="stat-card-icon"),
            html.Div(
                className="stat-card-body",
                children=[
                    html.Div(f"{value:,}", className="stat-card-value"),
                    html.Div(label, className="stat-card-label"),
                ],
            ),
        ],
    )


def _topics_list(items):
    if not items:
        return html.Div("Нет данных", className="filter-help")

    max_count = max(c for _, c in items) or 1

    return html.Div(
        [
            html.Div(
                className="topic-row",
                children=[
                    html.Div(
                        className="topic-row-name",
                        children=topic,
                    ),
                    html.Div(
                        className="topic-row-bar",
                        children=html.Div(
                            className="topic-row-bar-fill",
                            style={"width": f"{count / max_count * 100}%"},
                        ),
                    ),
                    html.Div(
                        className="topic-row-count",
                        children=str(count),
                    ),
                ],
            )
            for topic, count in items
        ]
    )


def _activity_chart(df):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["year"],
            y=df["n"],
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
        xaxis=dict(showgrid=False, title=None, dtick=5),
        yaxis=dict(showgrid=True, gridcolor="#eef0f3", title=None, tickformat="d"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=12, color="#555b64"),
        height=320,
    )
    return fig


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="page",
    children=[

        dcc.Location(id="home-url", refresh=True),

        html.Div(
            className="page-header",
            children=[
                html.H1("Исследовательская сеть СПбГУ", className="page-title"),
                html.Div(
                    "Данные из OpenAlex на основе публикаций авторов СПбГУ",
                    className="page-subtitle",
                ),
            ],
        ),

        # ---------- Карточки ----------
        html.Div(id="overview-stats", className="stats-grid"),

        # ---------- Граф + топ направлений ----------
        html.Div(
            className="overview-grid",
            children=[

                html.Div(
                    className="panel",
                    children=[
                        html.Div(
                            className="panel-header",
                            children=html.H3(
                                "Карта исследовательской сети",
                                className="panel-title",
                            ),
                        ),
                        html.Div(
                            className="panel-body overview-graph-body",
                            children=[
                                cyto.Cytoscape(
                                    id="overview-mini-graph",
                                    elements=_load_mini_graph(),
                                    stylesheet=MINI_STYLESHEET,
                                    layout={
                                        "name": "preset",
                                        "fit": True,
                                        "padding": 40,
                                    },
                                    style={"width": "100%", "height": "420px"},
                                    minZoom=0.3,
                                    maxZoom=3,
                                    zoomingEnabled=True,
                                    userZoomingEnabled=True,
                                    panningEnabled=True,
                                    userPanningEnabled=True,
                                ),
                            ],
                        ),

                        # Пояснение как читать карту
                        html.Div(
                            className="graph-legend-box",
                            children=[
                                html.Div(
                                    "Как читать карту",
                                    className="graph-legend-title",
                                ),
                                html.Div(
                                    className="graph-legend-items",
                                    children=[
                                        html.Div(
                                            className="graph-legend-item",
                                            children=[
                                                html.Span(
                                                    className="legend-dot legend-dot-main"
                                                ),
                                                "Основные авторы СПбГУ",
                                            ],
                                        ),
                                        html.Div(
                                            className="graph-legend-item",
                                            children=[
                                                html.Span(
                                                    className="legend-dot legend-dot-other"
                                                ),
                                                "Соавторы",
                                            ],
                                        ),
                                        html.Div(
                                            className="graph-legend-item",
                                            children=[
                                                html.Span("⭕", className="legend-symbol"),
                                                "Размер узла — количество публикаций",
                                            ],
                                        ),
                                        html.Div(
                                            className="graph-legend-item",
                                            children=[
                                                html.Span("━", className="legend-symbol"),
                                                "Толщина связи — совместные работы",
                                            ],
                                        ),
                                        html.Div(
                                            className="graph-legend-item",
                                            children=[
                                                html.Span("🖱️", className="legend-symbol"),
                                                "Колёсико — зум, клик — профиль",
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        html.Div(
                            className="graph-footer",
                            children=[
                                html.Span("Показаны 60 самых активных авторов"),
                                html.A(
                                    "Открыть полную карту →",
                                    href="/network",
                                    className="link-arrow",
                                ),
                            ],
                        ),
                    ],
                ),

                # Топ направлений
                html.Div(
                    className="panel",
                    children=[
                        html.Div(
                            className="panel-header",
                            children=html.H3(
                                "Топ направлений по числу публикаций",
                                className="panel-title",
                            ),
                        ),
                        html.Div(
                            id="overview-topics",
                            className="panel-body",
                        ),
                    ],
                ),
            ],
        ),

        # ---------- Динамика ----------
        html.Div(
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
                    children=[
                        dcc.Graph(
                            id="overview-activity",
                            config={"displayModeBar": False},
                            style={"height": "320px"},
                        ),
                    ],
                ),
            ],
        ),
    ],
)


# ============================================================
# CALLBACKS
# ============================================================

@callback(
    Output("overview-stats", "children"),
    Input("home-url", "pathname"),
)
def render_stats(pathname):
    stats = _load_overview_stats()
    return [
        _stat_card("Исследователей", stats["authors"], "👥"),
        _stat_card("Публикаций",     stats["publications"], "📄"),
        _stat_card("Связей",         stats["links"], "🔗"),
        _stat_card("Цитирований",    stats["citations"], "📈"),
    ]


@callback(
    Output("overview-topics", "children"),
    Input("home-url", "pathname"),
)
def render_topics(pathname):
    return _topics_list(_load_topics())


@callback(
    Output("overview-activity", "figure"),
    Input("home-url", "pathname"),
)
def render_activity(pathname):
    df = _load_activity()
    return _activity_chart(df)


# ============================================================
# КЛИК ПО УЗЛУ → ПЕРЕХОД В ПРОФИЛЬ
# ============================================================

@callback(
    Output("home-url", "pathname", allow_duplicate=True),
    Input("overview-mini-graph", "tapNodeData"),
    prevent_initial_call=True,
)
def navigate_to_author(tap_data):

    if not tap_data:
        return dash.no_update

    author_id = tap_data.get("author_id")
    if not author_id:
        return dash.no_update

    short_id = author_id.rstrip("/").split("/")[-1]

    return f"/author/{short_id}"