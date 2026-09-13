# pages/author.py

import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import pandas as pd

from utils import logger
from etl import db_session


dash.register_page(
    __name__,
    path_template="/author/<author_id>",
    name="Профиль",
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
# ЗАГРУЗКА ДАННЫХ
# ============================================================

def _load_author(author_id):

    full_id = _normalize_id(author_id)

    try:
        with db_session() as conn:

            df_name = pd.read_sql(
                "SELECT id, name FROM authors WHERE id = ?",
                conn,
                params=[full_id],
            )

            if df_name.empty:
                return None

            name = df_name.iloc[0]["name"]
            db_id = df_name.iloc[0]["id"]

            df_metrics = pd.read_sql(
                """
                SELECT
                    COUNT(DISTINCT a.publication_id) AS publications,
                    COALESCE(SUM(p.cited_by_count), 0) AS citations
                FROM authorship a
                JOIN publications p ON p.id = a.publication_id
                WHERE a.author_id = ?
                """,
                conn,
                params=[db_id],
            )

            publications = int(df_metrics.iloc[0]["publications"])
            citations = int(df_metrics.iloc[0]["citations"])

            df_coauthors = pd.read_sql(
                """
                SELECT COUNT(DISTINCT a2.author_id) AS n
                FROM authorship a1
                JOIN authorship a2 ON a1.publication_id = a2.publication_id
                WHERE a1.author_id = ? AND a2.author_id != ?
                """,
                conn,
                params=[db_id, db_id],
            )

            coauthors = int(df_coauthors.iloc[0]["n"])

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
                params=[db_id],
            )

        topics = []
        for row in df_topics["topics"].dropna():
            for t in row.split(";"):
                t = t.strip()
                if t and t not in topics:
                    topics.append(t)

        return {
            "id": db_id,
            "short_id": _short_id(db_id),
            "name": name,
            "publications": publications,
            "citations": citations,
            "coauthors": coauthors,
            "topics": topics[:8],
        }

    except Exception as e:
        logger.warning(f"Не удалось загрузить автора {author_id}: {e}")
        return None


def _load_publications(author_id):
    """Все публикации автора."""

    full_id = _normalize_id(author_id)

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT p.id, p.title, p.publication_year, p.cited_by_count, p.journal
                FROM publications p
                JOIN authorship a ON a.publication_id = p.id
                WHERE a.author_id = ?
                ORDER BY p.publication_year DESC, p.cited_by_count DESC
                """,
                conn,
                params=[full_id],
            )
        return df.to_dict("records")

    except Exception as e:
        logger.warning(f"Не удалось загрузить публикации: {e}")
        return []


def _load_coauthors(author_id, limit=10):

    full_id = _normalize_id(author_id)

    try:
        with db_session() as conn:
            df = pd.read_sql(
                """
                SELECT
                    au.id AS author_id,
                    au.name,
                    COUNT(DISTINCT a1.publication_id) AS shared
                FROM authorship a1
                JOIN authorship a2 ON a1.publication_id = a2.publication_id
                JOIN authors au ON au.id = a2.author_id
                WHERE a1.author_id = ? AND a2.author_id != ?
                GROUP BY au.id, au.name
                ORDER BY shared DESC
                LIMIT ?
                """,
                conn,
                params=[full_id, full_id, limit],
            )
        return df.to_dict("records")
    except Exception as e:
        logger.warning(f"Не удалось загрузить соавторов: {e}")
        return []


# ============================================================
# КОМПОНЕНТЫ
# ============================================================

def _metric(label, value):
    return html.Div(
        className="profile-metric",
        children=[
            html.Div(f"{value:,}", className="profile-metric-value"),
            html.Div(label, className="profile-metric-label"),
        ],
    )


def _publication_row(pub):
    """Публикация — ссылка на OpenAlex."""

    title = pub.get("title") or "Без названия"
    year = pub.get("publication_year") or "—"
    cites = pub.get("cited_by_count") or 0
    journal = pub.get("journal") or ""

    pub_id = pub.get("id") or ""
    short_pub_id = pub_id.rstrip("/").split("/")[-1] if pub_id else ""
    url = f"https://openalex.org/{short_pub_id}" if short_pub_id else "#"

    return html.A(
        href=url,
        target="_blank",
        className="publication-row",
        children=[
            html.Div(
                className="publication-year",
                children=str(year),
            ),
            html.Div(
                className="publication-body",
                children=[
                    html.Div(
                        title,
                        className="publication-title",
                    ),
                    html.Div(
                        journal,
                        className="publication-journal",
                    ) if journal else None,
                ],
            ),
            html.Div(
                className="publication-cites",
                children=[
                    html.Span(f"{cites}", className="publication-cites-value"),
                    html.Span(" цит.", className="publication-cites-label"),
                ],
            ),
        ],
    )


def _coauthor_row(coauthor, idx):
    short = _short_id(coauthor["author_id"])

    return html.A(
        href=f"/author/{short}",
        className="coauthor-row",
        children=[
            html.Div(
                className="coauthor-rank",
                children=str(idx),
            ),
            html.Div(
                className="coauthor-name",
                children=coauthor["name"],
            ),
            html.Div(
                className="coauthor-count",
                children=f"{coauthor['shared']} работ",
            ),
        ],
    )


def _not_found():
    return html.Div(
        className="empty-state",
        children=[
            html.Div("😕", className="empty-state-icon"),
            html.Div("Автор не найден", className="empty-state-title"),
            html.Div(
                "Возможно, он ещё не загружен в базу",
                className="empty-state-subtitle",
            ),
            html.A(
                "← Вернуться к исследователям",
                href="/researchers",
                className="link-arrow",
            ),
        ],
    )


# ============================================================
# LAYOUT
# ============================================================

layout = html.Div(
    className="page",
    children=[

        dcc.Location(id="author-url", refresh=False),

        html.Div(id="author-content"),

        dcc.Interval(
            id="author-trigger",
            interval=300,
            n_intervals=0,
            max_intervals=1,
        ),
    ],
)


# ============================================================
# CALLBACK
# ============================================================

@callback(
    Output("author-content", "children"),
    Input("author-trigger", "n_intervals"),
    Input("author-url", "pathname"),
)
def render_author(_trigger, pathname):

    if not pathname or not pathname.startswith("/author/"):
        return html.Div()

    author_id = pathname.replace("/author/", "").strip("/")
    if not author_id:
        return _not_found()

    author = _load_author(author_id)
    if not author:
        return _not_found()

    publications = _load_publications(author_id)
    coauthors = _load_coauthors(author_id)

    short_id = author["short_id"]

    # ---- Шапка профиля ----
    topics_ui = html.Div(
        [
            html.Span(t, className="topic-tag")
            for t in author["topics"]
        ]
    ) if author["topics"] else html.Div(
        "Темы не указаны",
        className="filter-help",
    )

    header = html.Div(
        className="profile-header panel",
        children=[
            html.Div(
                className="panel-body",
                children=[
                    html.Div(
                        className="profile-name",
                        children=[
                            html.Span("👤", className="profile-name-icon"),
                            html.Span(author["name"]),
                        ],
                    ),

                    html.Div(
                        className="profile-meta",
                        children=[
                            html.Span("СПбГУ", className="profile-meta-item"),
                            html.A(
                                "Открыть в OpenAlex ↗",
                                href=f"https://openalex.org/authors/{short_id}",
                                target="_blank",
                                className="profile-meta-link",
                            ),
                        ],
                    ),

                    html.Div(
                        className="profile-metrics",
                        children=[
                            _metric("публикаций", author["publications"]),
                            _metric("цитирований", author["citations"]),
                            _metric("соавторов", author["coauthors"]),
                        ],
                    ),

                    html.Div(
                        className="profile-topics",
                        children=[
                            html.Div(
                                "Основные темы",
                                className="profile-topics-title",
                            ),
                            topics_ui,
                        ],
                    ),

                    dbc.Button(
                        "🔗 Показать в сети",
                        href=f"/network?author={short_id}",
                        color="primary",
                        className="profile-network-btn",
                    ),
                ],
            ),
        ],
    )

    # ---- Публикации ----
    if publications:
        pubs_rows = [_publication_row(p) for p in publications]

        publications_panel = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header publications-header",
                    children=[
                        html.H3(
                            f"📄 Публикации ({len(publications)})",
                            className="panel-title",
                        ),
                        html.A(
                            "Открыть в OpenAlex ↗",
                            href=f"https://openalex.org/authors/{short_id}",
                            target="_blank",
                            className="publications-link",
                        ),
                    ],
                ),
                html.Div(
                    className="panel-body publications-list",
                    children=pubs_rows,
                ),
            ],
        )
    else:
        publications_panel = html.Div(
            className="panel",
            children=[
                html.Div(
                    className="panel-header",
                    children=html.H3(
                        "📄 Публикации (0)",
                        className="panel-title",
                    ),
                ),
                html.Div(
                    className="panel-body",
                    children=html.Div(
                        "Публикации не найдены",
                        className="filter-help",
                    ),
                ),
            ],
        )

    # ---- Соавторы ----
    coauthors_ui = html.Div(
        [_coauthor_row(c, i + 1) for i, c in enumerate(coauthors)]
    ) if coauthors else html.Div(
        "Соавторы не найдены",
        className="filter-help",
    )

    coauthors_panel = html.Div(
        className="panel",
        children=[
            html.Div(
                className="panel-header",
                children=html.H3(
                    f"👥 Соавторы ({author['coauthors']})",
                    className="panel-title",
                ),
            ),
            html.Div(
                className="panel-body",
                children=coauthors_ui,
            ),
        ],
    )

    return html.Div(
        [
            html.A(
                "← К исследователям",
                href="/researchers",
                className="back-link",
            ),

            header,

            html.Div(
                className="profile-grid",
                children=[
                    publications_panel,
                    coauthors_panel,
                ],
            ),
        ]
    )