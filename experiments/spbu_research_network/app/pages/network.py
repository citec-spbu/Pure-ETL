# pages/network.py

import hashlib
import math
import pickle
import sqlite3
import threading
from pathlib import Path

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc
import pandas as pd
import networkx as nx

from functools import lru_cache

from utils import (
    MAIN_AUTHORS,
    DB_PATH,
    GRAPH_CACHE_FILE,
    logger,
    timeit,
)

from etl import db_session


# ============================================================
# PAGE REGISTRATION
# ============================================================

dash.register_page(
    __name__,
    path="/network",
    name="Сеть",
)


# ============================================================
# GRAPH STYLES
# ============================================================

COLOR_PALETTE = [
    "#6B7280",
    "#8B95A1",
    "#748091",
    "#929BA6",
    "#66717E",
    "#7C8794",
    "#9AA2AC",
]


STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "width": "data(node_size)",
            "height": "data(node_size)",
            "background-color": "data(color)",
            "label": "data(label)",
            "font-size": "10px",
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
            "width": "mapData(weight, 1, 10, 0.8, 4)",
            "line-color": "data(color)",
            "curve-style": "bezier",
            "opacity": 0.55,
        },
    },
]


# ============================================================
# LOAD DATA
# ============================================================

@lru_cache(maxsize=2)
@timeit
def load_data_from_db(key):

    with db_session() as conn:
        try:
            df_pubs = pd.read_sql("SELECT * FROM publications", conn)
            df_auth = pd.read_sql("SELECT * FROM authorship", conn)
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.warning(f"Не удалось прочитать таблицы БД: {e}")
            return (pd.DataFrame(), pd.DataFrame())

    logger.info(f"Загружено {len(df_pubs)} публикаций")
    return df_pubs, df_auth


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================

def _load_authors_options():
    """Топ-500 авторов для поиска."""
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
        short_id = row["author_id"].rstrip("/").split("/")[-1]
        options.append({
            "label": f"{row['name']} ({int(row['publications'])})",
            "value": short_id,
        })
    return options


def _load_topics_options():
    """Топ-20 тем для фильтра."""
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
    return [t for t, _ in top[:20]]


def _authors_with_topic(topic):
    """Авторы (полные URL), у которых есть публикация с этой темой."""
    if not topic:
        return None

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT DISTINCT a.author_id
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                WHERE p.topics LIKE ?
                """,
                conn,
                params=[f"%{topic}%"],
            )
        return set(df["author_id"].tolist())
    except Exception as e:
        logger.warning(f"Не удалось загрузить авторов по теме: {e}")
        return None


# ============================================================
# GRAPH CACHE
# ============================================================

CACHE_VERSION = 7

_GRAPH_CACHE_LOCK = threading.Lock()


def _db_state_key():
    try:
        mtime = Path(DB_PATH).resolve().stat().st_mtime_ns
    except OSError:
        mtime = 0

    return hashlib.md5(
        f"{CACHE_VERSION}:{mtime}".encode()
    ).hexdigest()


def _load_graph_from_disk(key):

    with _GRAPH_CACHE_LOCK:
        if not GRAPH_CACHE_FILE.exists():
            return None

        try:
            with open(GRAPH_CACHE_FILE, "rb") as f:
                saved_key, graph = pickle.load(f)

            if saved_key == key:
                logger.info("Граф загружен из кэша")
                return graph

        except Exception as e:
            logger.warning(f"Кэш графа повреждён: {e}")

    return None


def _save_graph_to_disk(key, graph):

    with _GRAPH_CACHE_LOCK:
        try:
            with open(GRAPH_CACHE_FILE, "wb") as f:
                pickle.dump((key, graph), f)
        except Exception as e:
            logger.warning(f"Не удалось сохранить кэш: {e}")


# ============================================================
# GRAPH BUILDING
# ============================================================

def _node_radius(graph, node):
    publications = graph.nodes[node].get("publications", 1)
    return (20 + min(publications, 30)) / 2


def _push_apart_overlaps(graph, positions, gap_factor=2.5, max_iter=60):

    nodes = list(graph.nodes())

    for _ in range(max_iter):
        total_move = 0.0

        for i, a in enumerate(nodes):
            radius_a = _node_radius(graph, a)

            for b in nodes[i + 1:]:
                radius_b = _node_radius(graph, b)
                min_distance = (radius_a + radius_b) * gap_factor

                dx = positions[b][0] - positions[a][0]
                dy = positions[b][1] - positions[a][1]
                distance = math.hypot(dx, dy)

                if 0 < distance < min_distance:
                    push = (min_distance - distance) / 2
                    ux = dx / distance
                    uy = dy / distance

                    positions[a][0] -= ux * push
                    positions[a][1] -= uy * push
                    positions[b][0] += ux * push
                    positions[b][1] += uy * push

                    total_move += push

        if total_move < 0.05:
            break


def _layout_by_components(graph):

    components = sorted(
        (
            graph.subgraph(component).copy()
            for component in nx.connected_components(graph)
        ),
        key=lambda x: x.number_of_nodes(),
        reverse=True,
    )

    if not components:
        return {}

    UNIT = 40.0
    boxes = []

    for component in components:

        n = component.number_of_nodes()

        if n == 1:
            local = {next(iter(component.nodes())): [0.0, 0.0]}
        else:
            positions = nx.spring_layout(
                component,
                seed=42,
                iterations=30,
                k=7.5 / n ** 0.5,
            )

            xs = [p[0] for p in positions.values()]
            ys = [p[1] for p in positions.values()]

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            width = (max_x - min_x) or 1.0
            height = (max_y - min_y) or 1.0

            side = math.sqrt(n)

            local = {
                node: [
                    ((x - min_x) / width) * side * UNIT,
                    ((y - min_y) / height) * side * UNIT,
                ]
                for node, (x, y) in positions.items()
            }

        _push_apart_overlaps(component, local)

        xs = [p[0] for p in local.values()]
        ys = [p[1] for p in local.values()]
        min_x, min_y = min(xs), min(ys)

        for node in local:
            local[node] = [local[node][0] - min_x, local[node][1] - min_y]

        xs = [p[0] for p in local.values()]
        ys = [p[1] for p in local.values()]

        boxes.append((
            (max(xs) - min(xs)) or UNIT,
            (max(ys) - min(ys)) or UNIT,
            local,
        ))

    GAP = 120.0
    total_area = sum(w * h for w, h, _ in boxes)
    row_target = math.sqrt(total_area) * 1.6

    positions = {}
    x, y, row_height = 0.0, 0.0, 0.0

    for width, height, local in boxes:

        if x > 0 and x + width > row_target:
            x = 0.0
            y += row_height + GAP
            row_height = 0.0

        for node, (px, py) in local.items():
            positions[node] = (x + px, y + py)

        x += width + GAP
        row_height = max(row_height, height)

    return positions


def _build_full_graph(key):

    df_pubs, df_auth = load_data_from_db(key)

    if df_pubs.empty:
        return nx.Graph()

    with db_session() as conn:
        df_authors = pd.read_sql("SELECT id, name FROM authors", conn)

    author_names = dict(zip(df_authors["id"], df_authors["name"]))
    graph = nx.Graph()

    for _, publication in df_pubs.iterrows():

        publication_id = publication["id"]
        cited_by = publication["cited_by_count"]

        authors = df_auth[
            df_auth["publication_id"] == publication_id
        ]["author_id"].tolist()

        authors = [a for a in authors if a in author_names]

        for author_id in authors:

            if author_id not in graph:
                graph.add_node(
                    author_id,
                    publications=0,
                    total_citations=0,
                    name=author_names[author_id],
                    is_main_author=(author_names[author_id] in MAIN_AUTHORS),
                )

            graph.nodes[author_id]["publications"] += 1
            graph.nodes[author_id]["total_citations"] += cited_by

        for i, author_a in enumerate(authors):
            for author_b in authors[i + 1:]:
                if graph.has_edge(author_a, author_b):
                    graph[author_a][author_b]["weight"] += 1
                else:
                    graph.add_edge(author_a, author_b, weight=1)

    if graph.number_of_nodes() == 0:
        return graph

    positions = _layout_by_components(graph)

    for node in graph.nodes():
        graph.nodes[node]["pos"] = {
            "x": float(positions[node][0]),
            "y": float(positions[node][1]),
        }

    return graph


@lru_cache(maxsize=2)
def _cached_full_graph(key):

    graph = _load_graph_from_disk(key)

    if graph is None:
        graph = _build_full_graph(key)
        _save_graph_to_disk(key, graph)

    return graph


@timeit
def build_graph(min_pubs=1, min_cites=0, topic=None):

    key = _db_state_key()
    graph = _cached_full_graph(key)

    if topic:
        allowed = _authors_with_topic(topic)
        if allowed is not None:
            nodes_to_keep = [
                node for node in graph.nodes() if node in allowed
            ]
            graph = graph.subgraph(nodes_to_keep).copy()

    if min_pubs > 1 or min_cites > 0:
        nodes_to_keep = [
            node
            for node, data in graph.nodes(data=True)
            if (
                data.get("publications", 0) >= min_pubs
                and data.get("total_citations", 0) >= min_cites
            )
        ]
        graph = graph.subgraph(nodes_to_keep).copy()

    return graph


def clear_graph_cache():
    _cached_full_graph.cache_clear()
    load_data_from_db.cache_clear()

    try:
        GRAPH_CACHE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ============================================================
# CYTOSCAPE
# ============================================================

def graph_to_cytoscape_elements(graph):
    """Всегда только фамилии."""

    if graph.number_of_nodes() == 0:
        return []

    elements = []
    color_index = 0

    for node in graph.nodes():

        data = graph.nodes[node]
        is_main = data.get("is_main_author", False)

        if is_main:
            color = "#E74C3C"
        else:
            color = COLOR_PALETTE[color_index % len(COLOR_PALETTE)]
            color_index += 1

        publications = data.get("publications", 1)
        node_size = 20 + min(publications, 30)

        name = data.get("name", node)

        parts = name.split()
        label = parts[-1] if len(parts) > 1 else name

        elements.append({
            "position": data.get("pos", {}),
            "data": {
                "id": node,
                "label": label,
                "full_name": name,
                "author_id": node,
                "publications": publications,
                "citations": data.get("total_citations", 0),
                "is_main_author": is_main,
                "node_size": node_size,
                "color": color,
            },
        })

    for source, target, data in graph.edges(data=True):

        elements.append({
            "data": {
                "source": source,
                "target": target,
                "weight": data.get("weight", 1),
                "color": "#B8BEC6",
            }
        })

    return elements


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="page",
    children=[

        dcc.Location(id="network-url", refresh=False),

        # ✅ Тик для повторных попыток выделения
        dcc.Interval(
            id="network-tick",
            interval=600,
            n_intervals=0,
            max_intervals=5,
        ),

        html.Div(
            className="page-header",
            children=[
                html.H1("Исследовательская сеть СПбГУ", className="page-title"),
                html.Div(
                    "Соавторство научных публикаций на основе данных OpenAlex",
                    className="page-subtitle",
                ),
            ],
        ),

        html.Div(
            className="network-layout",
            children=[

                # ==================================================
                # FILTERS
                # ==================================================

                html.Div(
                    className="panel",
                    children=[
                        html.Div(
                            className="panel-header",
                            children=html.H3("Фильтры", className="panel-title"),
                        ),
                        html.Div(
                            className="panel-body",
                            children=[

                                # Поиск автора
                                html.Div(
                                    className="filter-group",
                                    children=[
                                        html.Label(
                                            "Поиск автора",
                                            className="filter-label",
                                        ),
                                        dcc.Dropdown(
                                            id="network-author-search",
                                            options=_load_authors_options(),
                                            value=None,
                                            placeholder="Имя автора...",
                                            searchable=True,
                                            clearable=True,
                                            className="network-dropdown",
                                        ),
                                    ],
                                ),

                                # Направление
                                html.Div(
                                    className="filter-group",
                                    children=[
                                        html.Label(
                                            "Направление",
                                            className="filter-label",
                                        ),
                                        dcc.Dropdown(
                                            id="network-topic-filter",
                                            options=[
                                                {"label": "Все направления", "value": ""}
                                            ] + [
                                                {"label": t, "value": t}
                                                for t in _load_topics_options()
                                            ],
                                            value="",
                                            clearable=False,
                                            className="network-dropdown",
                                        ),
                                    ],
                                ),

                                # Публикации
                                html.Div(
                                    className="filter-group",
                                    children=[
                                        html.Label(
                                            "Минимум публикаций",
                                            className="filter-label",
                                        ),
                                        html.Div(
                                            id="min-pubs-value",
                                            className="filter-value",
                                            children="1",
                                        ),
                                        dcc.Slider(
                                            id="min-pubs-slider",
                                            min=1, max=20, step=1, value=1,
                                            marks={1: "1", 5: "5", 10: "10", 20: "20"},
                                            tooltip={"placement": "bottom", "always_visible": False},
                                        ),
                                    ],
                                ),

                                # Цитирования
                                html.Div(
                                    className="filter-group",
                                    children=[
                                        html.Label(
                                            "Минимум цитирований",
                                            className="filter-label",
                                        ),
                                        html.Div(
                                            id="min-cites-value",
                                            className="filter-value",
                                            children="0",
                                        ),
                                        dcc.Slider(
                                            id="min-cites-slider",
                                            min=0, max=100, step=5, value=0,
                                            marks={0: "0", 50: "50", 100: "100"},
                                            tooltip={"placement": "bottom", "always_visible": False},
                                        ),
                                    ],
                                ),

                                # Кнопка сброса фильтров
                                html.Div(
                                    className="filter-group",
                                    children=dbc.Button(
                                        "Сбросить фильтры",
                                        id="network-reset-btn",
                                        color="light",
                                        size="sm",
                                        className="reset-filters-btn",
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),

                # ==================================================
                # GRAPH
                # ==================================================

                html.Div(
                    className="panel graph-panel",
                    children=[

                        html.Div(
                            className="graph-toolbar",
                            children=[
                                html.Div(
                                    className="graph-toolbar-left",
                                    children=[
                                        html.Div("Сеть соавторства", className="graph-title"),
                                        html.Div(id="graph-count", className="graph-count"),
                                    ],
                                ),
                                html.Div(
                                    className="legend",
                                    children=[
                                        html.Div(
                                            className="legend-item",
                                            children=[
                                                html.Span(className="legend-dot legend-dot-main"),
                                                "Основные авторы",
                                            ],
                                        ),
                                        html.Div(
                                            className="legend-item",
                                            children=[
                                                html.Span(className="legend-dot legend-dot-other"),
                                                "Соавторы",
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        html.Div(
                            className="network-stats",
                            children=[
                                html.Div(
                                    className="network-stat",
                                    children=[html.Strong(id="stat-papers"), " публикаций"],
                                ),
                                html.Div(
                                    className="network-stat",
                                    children=[html.Strong(id="stat-authors"), " авторов"],
                                ),
                                html.Div(
                                    className="network-stat",
                                    children=[html.Strong(id="stat-edges"), " связей"],
                                ),
                            ],
                        ),

                        html.Div(
                            className="graph-wrapper",
                            children=[
                                cyto.Cytoscape(
                                    id="coauthorship-graph",
                                    elements=[],
                                    stylesheet=STYLESHEET,
                                    layout={"name": "preset", "fit": True, "padding": 50},
                                    style={"width": "100%", "height": "100%"},
                                    minZoom=0.15,
                                    maxZoom=3,
                                    zoomingEnabled=True,
                                    userZoomingEnabled=True,
                                    panningEnabled=True,
                                    userPanningEnabled=True,
                                ),
                            ],
                        ),

                        html.Div(
                            className="graph-footer",
                            children=[
                                html.Span("Нажмите на автора, чтобы посмотреть информацию."),
                                html.Span(
                                    "Размер узла — количество публикаций · "
                                    "толщина связи — количество совместных работ"
                                ),
                            ],
                        ),
                    ],
                ),

                # ==================================================
                # AUTHOR PANEL
                # ==================================================

                html.Div(
                    className="panel author-panel",
                    children=[
                        html.Div(
                            className="panel-header",
                            children=html.H3("Исследователь", className="panel-title"),
                        ),
                        html.Div(
                            id="node-info",
                            className="panel-body",
                            children=[
                                html.Div(
                                    [
                                        "Выберите автора ",
                                        "на графе, чтобы увидеть ",
                                        "его показатели и научные темы.",
                                    ],
                                    className="author-empty",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


# ============================================================
# UPDATE GRAPH
# ============================================================

@callback(
    Output("coauthorship-graph", "elements"),
    Output("stat-papers", "children"),
    Output("stat-authors", "children"),
    Output("stat-edges", "children"),
    Output("graph-count", "children"),
    Output("min-pubs-value", "children"),
    Output("min-cites-value", "children"),
    Input("min-pubs-slider", "value"),
    Input("min-cites-slider", "value"),
    Input("network-topic-filter", "value"),
)
@timeit
def update_graph(min_pubs, min_cites, topic):

    graph = build_graph(min_pubs, min_cites, topic=topic or None)
    elements = graph_to_cytoscape_elements(graph)

    total_papers, _ = _graph_stats(graph)
    authors_count = graph.number_of_nodes()
    edges_count = graph.number_of_edges()

    return (
        elements,
        str(total_papers),
        str(authors_count),
        str(edges_count),
        f"{authors_count} авторов · {edges_count} связей",
        str(min_pubs),
        str(min_cites),
    )


# ============================================================
# RESET FILTERS
# ============================================================

@callback(
    Output("min-pubs-slider", "value", allow_duplicate=True),
    Output("min-cites-slider", "value", allow_duplicate=True),
    Output("network-author-search", "value", allow_duplicate=True),
    Output("network-topic-filter", "value", allow_duplicate=True),
    Input("network-reset-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(n_clicks):
    """Сбрасывает все фильтры в дефолт."""
    return 1, 0, None, ""


# ============================================================
# GRAPH STATS
# ============================================================

def _graph_stats(graph):

    if graph.number_of_nodes() == 0:
        return 0, 0

    key = _db_state_key()
    df_pubs, df_auth = load_data_from_db(key)

    if df_pubs.empty or df_auth.empty:
        return 0, 0

    node_ids = set(graph.nodes())
    auth_in_graph = df_auth[df_auth["author_id"].isin(node_ids)]
    publication_ids = set(auth_in_graph["publication_id"])

    total_papers = len(publication_ids)
    total_citations = int(
        df_pubs[df_pubs["id"].isin(publication_ids)]["cited_by_count"].sum()
    )

    return total_papers, total_citations


# ============================================================
# AUTHOR INFO
# ============================================================

def get_coauthors_count(author_id):

    if not author_id:
        return 0

    try:
        with db_session() as conn:
            result = pd.read_sql(
                """
                SELECT COUNT(DISTINCT a2.author_id) AS count
                FROM authorship a1
                JOIN authorship a2
                    ON a1.publication_id = a2.publication_id
                WHERE a1.author_id = ?
                    AND a2.author_id != ?
                """,
                conn,
                params=[author_id, author_id],
            )

        return int(result.iloc[0]["count"])

    except Exception as e:
        logger.warning(f"Не удалось получить число соавторов: {e}")
        return 0


@callback(
    Output("node-info", "children"),
    Input("coauthorship-graph", "selectedNodeData"),
)
def display_node_info(selected_nodes):

    if not selected_nodes:
        return html.Div(
            [
                "Выберите автора ",
                "на графе, чтобы увидеть ",
                "его показатели и научные темы.",
            ],
            className="author-empty",
        )

    node = selected_nodes[0]

    author_id = node.get("author_id", "")
    full_name = node.get("full_name", "Неизвестный автор")
    publications = node.get("publications", 0)
    citations = node.get("citations", 0)

    coauthors_count = get_coauthors_count(author_id)

    topics = []
    if author_id:
        try:
            with db_session() as conn:
                df = pd.read_sql(
                    """
                    SELECT topics
                    FROM publications p
                    JOIN authorship a ON a.publication_id = p.id
                    WHERE a.author_id = ?
                        AND p.topics IS NOT NULL
                        AND p.topics != ''
                    """,
                    conn,
                    params=[author_id],
                )

            for topic_string in df["topics"].dropna():
                for topic in topic_string.split(";"):
                    topic = topic.strip()
                    if topic and topic not in topics:
                        topics.append(topic)

            topics = topics[:5]

        except Exception as e:
            logger.warning(f"Не удалось загрузить темы автора: {e}")

    if topics:
        topics_component = html.Div(
            [html.Span(topic, className="topic-tag") for topic in topics]
        )
    else:
        topics_component = html.Div("Темы не найдены", className="filter-help")

    short_id = author_id.rstrip("/").split("/")[-1] if author_id else ""

    profile_button = dbc.Button(
        "Открыть профиль",
        href=f"/author/{short_id}" if short_id else "#",
        color="primary",
        className="open-profile-btn",
        size="sm",
    )

    return html.Div([
        html.Div(full_name, className="author-name"),

        html.Div(
            className="author-metrics",
            children=[
                html.Div(
                    className="author-metric",
                    children=[
                        html.Div(f"{publications:,}", className="author-metric-value"),
                        html.Div("публикаций", className="author-metric-label"),
                    ],
                ),
                html.Div(
                    className="author-metric",
                    children=[
                        html.Div(f"{citations:,}", className="author-metric-value"),
                        html.Div("цитирований", className="author-metric-label"),
                    ],
                ),
                html.Div(
                    className="author-metric",
                    children=[
                        html.Div(str(coauthors_count), className="author-metric-value"),
                        html.Div("соавторов", className="author-metric-label"),
                    ],
                ),
            ],
        ),

        html.Div(
            className="author-section",
            children=[
                html.Div("Основные темы", className="author-section-title"),
                topics_component,
            ],
        ),

        profile_button,
    ])


# ============================================================
# ВЫДЕЛЕНИЕ АВТОРА (URL + поиск)
# ============================================================

@callback(
    Output("coauthorship-graph", "elements", allow_duplicate=True),
    Output("coauthorship-graph", "selectedNodeData", allow_duplicate=True),
    Input("network-url", "search"),
    Input("network-author-search", "value"),
    Input("network-tick", "n_intervals"),
    State("coauthorship-graph", "elements"),
    prevent_initial_call=True,
)
def highlight_author(search, search_author, n_intervals, current_elements):
    """
    Выделяет автора из URL или из поиска.
    Использует State + dcc.Interval для гарантии, что граф уже построен.
    """

    if not current_elements:
        return dash.no_update, dash.no_update

    author_id = None

    # Приоритет: поиск → URL
    if search_author:
        author_id = search_author
    elif search:
        from urllib.parse import parse_qs
        query = parse_qs(search.lstrip("?"))
        author_id = query.get("author", [None])[0]

    if not author_id:
        return dash.no_update, dash.no_update

    def _short(x):
        return x.rstrip("/").split("/")[-1] if x else ""

    target_short = _short(author_id)

    selected_node = None
    for el in current_elements:
        data = el.get("data", {})
        if "author_id" in data and _short(data["author_id"]) == target_short:
            selected_node = el
            break

    if not selected_node:
        return dash.no_update, dash.no_update

    real_id = selected_node["data"]["author_id"]

    neighbors = set()
    for el in current_elements:
        data = el.get("data", {})
        if "source" in data and "target" in data:
            if data["source"] == real_id:
                neighbors.add(data["target"])
            elif data["target"] == real_id:
                neighbors.add(data["source"])

    new_elements = []
    for el in current_elements:
        data = el.get("data", {})

        if "author_id" in data:
            if data["author_id"] == real_id:
                data["color"] = "#20242A"
                data["node_size"] = data.get("node_size", 30) + 10
            elif data["author_id"] in neighbors:
                data["color"] = "#3B82F6"
            else:
                data["color"] = "#D1D5DB"

        if "source" in data and "target" in data:
            if data["source"] == real_id or data["target"] == real_id:
                data["color"] = "#3B82F6"
            else:
                data["color"] = "#E5E7EB"

        new_elements.append(el)

    return new_elements, [selected_node["data"]]

# ============================================================
# ЧТЕНИЕ ?topic= ИЗ URL
# ============================================================

@callback(
    Output("network-topic-filter", "value", allow_duplicate=True),
    Input("network-url", "search"),
    prevent_initial_call=True,
)
def apply_topic_from_url(search):
    """Если в URL есть ?topic=..., устанавливаем фильтр."""
    if not search:
        return dash.no_update

    from urllib.parse import parse_qs, unquote

    query = parse_qs(search.lstrip("?"))
    topic = query.get("topic", [None])[0]

    if not topic:
        return dash.no_update

    return unquote(topic)