from datetime import datetime

import dash
import polars as pl
import sqlalchemy
import sqlalchemy.orm
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate
from plotly import express as px

from app import queries
from app.aio_components.arbitrary_dropdown_aio import ArbitraryDropdownAIO
from app.aio_components.table_aio import TableAIO
from app.aio_components.tabs_aio import TabsAIO
from app.client_types import AppState
from app.models import OrganisationalUnit, Person
from app.ui_parts.search_units import search_units_element

dash.register_page(__name__, path="/report-1", name="Отчет 1", order=1)


def layout():
    state: AppState = dash.get_app().server.config["APP_STATE"]
    return html.Div(
        className="padded-box",
        children=[
            html.H1("Отчет 1"),
            html.Div(
                className="vertical-content vertical-content_large-gap",
                children=[
                    TabsAIO(
                        "tabs-unit-searching",
                        [
                            {
                                "label": "Выбор факультетов",
                                "content": settings_select_faculties(state),
                            },
                            {
                                "label": "Поиск организационных единиц",
                                "content": settings_search_units(),
                            },
                        ],
                    ),
                    settings_units_dropdown(),
                    settings_select_period(),
                    settings_toggles(),
                    settings_trigger_report(),
                    html.Div(
                        className="horizontal-content horizontal-content_center",
                        children=[
                            html.H2(children="Отчет"),
                            html.Abbr(
                                "?",
                                title="В соответствии с настройками выше при нажатии на кнопку генерируется отчет.\n"
                                "В отчете предоставляются три блока результатов, каждый из которых ограничен "
                                "5000 результатами. Если результатов больше, остальные просто не покажутся.\n"
                                "При подсчете учитывается иерархичность структуры, и ассоциация учитывается как и при "
                                "прямой связи, так и через любое подразделение.",
                                className="help-icon",
                            ),
                        ],
                    ),
                    html.Div(
                        className="vertical-content",
                        children=[
                            html.Div(
                                className="horizontal-content horizontal-content_center",
                                children=[
                                    html.H3(children="Количество результатов исследований по факультетам"),
                                    html.Abbr(
                                        "?",
                                        title="В соответствии с настройками выше за указанный период подсчитывается "
                                        "количество публикаций в выбранных выше органицазионных единицах",
                                        className="help-icon",
                                    ),
                                ],
                            ),
                            report_count_by_unit(),
                        ],
                    ),
                    html.Div(
                        className="vertical-content",
                        children=[
                            html.Div(
                                className="horizontal-content horizontal-content_center",
                                children=[
                                    html.H3(children="Количество результатов исследований по кафедрам"),
                                    html.Abbr(
                                        "?",
                                        title="В соответствии с настройками выше за указанный период подсчитывается "
                                        "количество публикаций в органицазионных единицах уровня 2, являющихся "
                                        "подразделениями выбранных. Выбранные организационные единицы - highest parent",
                                        className="help-icon",
                                    ),
                                ],
                            ),
                            report_count_by_division(),
                        ],
                    ),
                    html.Div(
                        className="vertical-content",
                        children=[
                            html.Div(
                                className="horizontal-content horizontal-content_center",
                                children=[
                                    html.H3(children="Количество результатов исследований по персонам"),
                                    html.Abbr(
                                        "?",
                                        title="В соответствии с настройками выше за указанный период подсчитывается "
                                        "количество публикаций у персон, когда либо ассоциированных с выбранными "
                                        "органицазионными единицами.\n"
                                        "В таблицах для каждой персоны присутствует множество записей в соответствии "
                                        "с каждой аффилиацией и ее периодом, но подсчет верный и от аффилиации "
                                        "не зависит.",
                                        className="help-icon",
                                    ),
                                ],
                            ),
                            report_count_by_person(),
                        ],
                    ),
                ],
            ),
        ],
    )


def settings_select_faculties(state: AppState):
    return [
        html.Div(
            className="vertical-content",
            children=[
                html.Div(
                    className="horizontal-content horizontal-content_center",
                    children=[
                        html.H3(children="Выбор факультетов"),
                        html.Abbr(
                            "?",
                            title="Здесь представлены все организационные единицы 1 уровня.\n"
                            "Если этого недостаточно, в следующей вкладке можно воспользоваться поиском.\n"
                            "Для выбора организационных единиц нужно пометить их галочками и нажать на кнопку "
                            "под таблицей.",
                            className="help-icon",
                        ),
                    ],
                ),
                TableAIO(
                    aio_id="report-1-select-faculties",
                    csv_filename="selected-faculties",
                    column_defs=[
                        {"field": i, "colId": i}
                        for i in [
                            "organisational_unit_id",
                            "name_ru",
                            "name_en",
                            "pure_id",
                            "type_id",
                        ]
                    ],
                    row_data=collect_faculties(state).to_dicts(),
                ),
                html.Div(
                    [
                        dcc.Button(
                            "Выбрать организационные единицы",
                            id="report-1-add-selected-units-from-faculties",
                            className="button",
                        ),
                    ]
                ),
            ],
        )
    ]


def settings_search_units():
    return [
        html.Div(
            className="vertical-content",
            children=[
                search_units_element(
                    aio_id="report-1-search-units",
                ),
                html.Div(
                    [
                        dcc.Button(
                            "Выбрать организационные единицы",
                            id="report-1-add-selected-units-from-search",
                            className="button",
                        ),
                    ]
                ),
            ],
        ),
    ]


def settings_units_dropdown():
    return html.Div(
        [
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H3(children="Выбранные организационные единицы"),
                    html.Abbr(
                        "?",
                        title='При нажатии на кнопку "Выбрать организационные единицы" выше сюда добавляются '
                        "отмеченные огранизационные единицы.\n"
                        "Выбранные organisational units используются для генерации отчета.\n"
                        "Можно занести дополнительные опции с помощью предоставленных полей. Добавленные "
                        "опции сохраняются в local storage.",
                        className="help-icon",
                    ),
                ],
            ),
            ArbitraryDropdownAIO(
                aio_id="report-1-units-selected",
                placeholder="Выберите organisational units...",
            ),
        ]
    )


def settings_select_period():
    return html.Div(
        [
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H3(children="Период отчета"),
                    html.Abbr(
                        "?",
                        title="Период задается в годах. Границы включаются в диапазоон."
                        "Эти года означают в какой год должна быть опубликована работа.\n"
                        "Информация берется из publication_statuses.",
                        className="help-icon",
                    ),
                ],
            ),
            html.Div(
                className="vertical-content",
                children=[
                    html.Div(
                        className="horizontal-content",
                        children=[
                            html.Label("От"),
                            dcc.Input(
                                id="report-1-year-picker-start",
                                value=datetime.now().year,
                                type="number",
                                persistence=True,
                                style={"width": "8em"},
                            ),
                        ],
                    ),
                    html.Div(
                        className="horizontal-content",
                        children=[
                            html.Label("До"),
                            dcc.Input(
                                id="report-1-year-picker-end",
                                value=datetime.now().year,
                                type="number",
                                persistence=True,
                                style={"width": "8em"},
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


def settings_toggles():
    return html.Div(
        [
            html.Div(
                className="horizontal-content horizontal-content_center",
                children=[
                    html.H3(children="Опции"),
                    html.Abbr(
                        "?",
                        title="Дополнительные переключатели для генерации отчета.",
                        className="help-icon",
                    ),
                ],
            ),
            dcc.Checklist(
                id="report-1-options",
                value=[],
                options=[
                    {
                        "label": "Исключить людей без результатов исследований",
                        "value": "exclude_persons_without_research_outuputs",
                    },
                ],
                persistence=True,
            ),
        ]
    )


def settings_trigger_report():
    return html.Div(
        [
            dcc.Button(
                "Сгенерировать",
                id="report-1-trigger",
                className="button",
            ),
        ]
    )


def report_count_by_unit():
    return TabsAIO(
        "report-1-research-outputs-count-by-unit",
        [
            {
                "label": "Chart",
                "content": [
                    dcc.Graph(
                        figure={},
                        id="report-1-graph-by-unit",
                    ),
                ],
            },
            {
                "label": "Table",
                "content": [
                    TableAIO(
                        aio_id="report-1-table-by-unit",
                        column_defs=[
                            {"field": i, "colId": i}
                            for i in [
                                "organisational_unit_id",
                                "name_ru",
                                "research_outputs_count",
                            ]
                        ],
                    ),
                ],
            },
        ],
    )


def report_count_by_division():
    return TabsAIO(
        "report-1-research-outputs-count-by-division",
        [
            {
                "label": "Chart",
                "content": [
                    dcc.Graph(
                        figure={},
                        id="report-1-graph-by-division",
                    ),
                ],
            },
            {
                "label": "Table",
                "content": [
                    TableAIO(
                        aio_id="report-1-table-by-division",
                        column_defs=[
                            {"field": i, "colId": i}
                            for i in [
                                "organisational_unit_id",
                                "name_ru",
                                "research_outputs_count",
                                "highest_parent_organisational_unit_id",
                                "highest_parent_organisational_unit_name_ru",
                            ]
                        ],
                    ),
                ],
            },
        ],
    )


def report_count_by_person():
    return TabsAIO(
        "report-1-research-outputs-count-by-person",
        [
            {
                "label": "Chart",
                "content": [
                    dcc.Graph(
                        figure={},
                        id="report-1-graph-by-person",
                    ),
                ],
            },
            {
                "label": "Table",
                "content": [
                    TableAIO(
                        aio_id="report-1-table-by-person",
                        column_defs=[
                            {"field": i, "colId": i}
                            for i in [
                                "person_id",
                                "first_name",
                                "last_name",
                                "research_outputs_count",
                                "organisational_unit_id",
                                "organisational_unit_name_ru",
                                "highest_parent_organisational_unit_id",
                                "highest_parent_organisational_unit_name_ru",
                            ]
                        ],
                    ),
                ],
            },
        ],
    )


def collect_faculties(state: AppState) -> pl.DataFrame:
    with state.engine.connect() as conn:
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(OrganisationalUnit.id, sqlalchemy.String),
                OrganisationalUnit.name_ru,
                OrganisationalUnit.name_en,
                OrganisationalUnit.pure_id,
                OrganisationalUnit.type_id,
            )
            .select_from(OrganisationalUnit)
            .where(OrganisationalUnit.type_id == 17278),
            conn,
        )
        return df


@callback(
    dict(
        selection=Output(
            ArbitraryDropdownAIO.ids.dropdown("report-1-units-selected"),
            "value",
            allow_duplicate=True,
        ),
        options=Output(
            ArbitraryDropdownAIO.ids.dropdown("report-1-units-selected"),
            "options",
            allow_duplicate=True,
        ),
    ),
    dict(
        add_button_faculties=Input("report-1-add-selected-units-from-faculties", "n_clicks"),
        add_button_child=Input("report-1-add-selected-units-from-search", "n_clicks"),
    ),
    dict(
        selection=State(
            ArbitraryDropdownAIO.ids.dropdown("report-1-units-selected"),
            "value",
        ),
        options=State(
            ArbitraryDropdownAIO.ids.dropdown("report-1-units-selected"),
            "options",
        ),
        faculties_table=State(
            TableAIO.ids.ag_grid("report-1-select-faculties"),
            "selectedRows",
        ),
        search_table=State(
            TableAIO.ids.ag_grid("report-1-search-units"),
            "selectedRows",
        ),
    ),
    prevent_initial_call=True,
)
def add_selected_units(inputs, state):
    options = {option["value"]: option for option in (state["options"] or [])}
    selection = state["selection"] or []

    if dash.ctx.triggered_id == "report-1-add-selected-units-from-faculties":
        table = state["faculties_table"]
    elif dash.ctx.triggered_id == "report-1-add-selected-units-from-search":
        table = state["search_table"]
    else:
        table = []

    for row in table:
        value = row.get("organisational_unit_id")
        label = row.get("name_ru")
        if not value or not label:
            continue
        if value not in selection:
            options[value] = dict(value=value, label=label)
            selection.append(value)

    return dict(
        options=[option for option in options.values()],
        selection=selection,
    )


@callback(
    dict(
        table_units=Output(
            TableAIO.ids.ag_grid("report-1-table-by-unit"),
            "rowData",
        ),
        graph_units=Output(
            "report-1-graph-by-unit",
            "figure",
        ),
        table_persons=Output(
            TableAIO.ids.ag_grid("report-1-table-by-person"),
            "rowData",
        ),
        graph_persons=Output(
            "report-1-graph-by-person",
            "figure",
        ),
        table_divisions=Output(
            TableAIO.ids.ag_grid("report-1-table-by-division"),
            "rowData",
        ),
        graph_divisions=Output(
            "report-1-graph-by-division",
            "figure",
        ),
    ),
    dict(
        trigger_button=Input("report-1-trigger", "n_clicks"),
    ),
    dict(
        year_start=State(
            "report-1-year-picker-start",
            "value",
        ),
        year_end=State(
            "report-1-year-picker-end",
            "value",
        ),
        selected_units=State(
            ArbitraryDropdownAIO.ids.dropdown("report-1-units-selected"),
            "value",
        ),
        options=State(
            "report-1-options",
            "value",
        ),
    ),
    prevent_initial_call=True,
)
def generate_report(inputs, state):
    year_start = state["year_start"]
    year_end = state["year_end"]
    unit_ids = state["selected_units"] or []

    if year_start is None or year_end is None:
        raise PreventUpdate
    if int(year_start) > int(year_end):
        raise PreventUpdate
    year_start = int(year_start)
    year_end = int(year_end)

    exclude_persons_without_research_outuputs = "exclude_persons_without_research_outuputs" in (state["options"] or [])

    organisational_units_with_children = queries.organisational_units.select_units_with_all_children_filter(
        filter_units_by_id=unit_ids
    ).cte()

    unit_names = sqlalchemy.orm.aliased(OrganisationalUnit)
    division_names = sqlalchemy.orm.aliased(OrganisationalUnit)
    highest_parent_names = sqlalchemy.orm.aliased(OrganisationalUnit)

    def filter_research_outputs(research_outputs_unfiltered) -> sqlalchemy.CTE:
        return (
            sqlalchemy.select(research_outputs_unfiltered)
            .where(
                (research_outputs_unfiltered.c.research_output_id.is_(None))
                | (
                    (
                        sqlalchemy.cast(
                            research_outputs_unfiltered.c.publication_status["publication_year"], sqlalchemy.Integer
                        )
                        <= year_end
                    )
                    & (
                        year_start
                        <= sqlalchemy.cast(
                            research_outputs_unfiltered.c.publication_status["publication_year"], sqlalchemy.Integer
                        )
                    )
                )
            )
            .cte()
        )

    def build_research_outputs_for_units_counts():
        research_outputs_for_units = (
            queries.research_outputs.add_current_publication_status(
                queries.select_research_outputs_for_units(
                    organisational_units_with_children,
                    outerjoin=True,
                    rightjoin=True,
                ).cte()
            )
        ).cte()
        research_outputs_for_units_filtered = filter_research_outputs(research_outputs_for_units)
        research_outputs_for_units_counts = (
            sqlalchemy.select(
                research_outputs_for_units_filtered.c.highest_parent_organisational_unit_id.label(
                    "organisational_unit_id"
                ),
                sqlalchemy.func.count(
                    sqlalchemy.func.distinct(research_outputs_for_units_filtered.c.research_output_id)
                ).label("research_outputs_count"),
            )
            .select_from(research_outputs_for_units_filtered)
            .group_by(research_outputs_for_units_filtered.c.highest_parent_organisational_unit_id)
        ).cte()
        research_outputs_for_units_counts_named = (
            sqlalchemy.select(
                research_outputs_for_units_counts.c.organisational_unit_id,
                OrganisationalUnit.name_ru,
                research_outputs_for_units_counts.c.research_outputs_count,
            )
            .select_from(research_outputs_for_units_counts)
            .join(
                OrganisationalUnit, OrganisationalUnit.id == research_outputs_for_units_counts.c.organisational_unit_id
            )
        ).cte()

        return (
            sqlalchemy.select(
                sqlalchemy.cast(
                    research_outputs_for_units_counts_named.c.organisational_unit_id, sqlalchemy.String
                ).label("organisational_unit_id"),
                research_outputs_for_units_counts_named.c.name_ru,
                research_outputs_for_units_counts_named.c.research_outputs_count,
            )
            .select_from(research_outputs_for_units_counts_named)
            .limit(5000)
        )

    def build_research_outputs_for_divisions_counts():
        division_units = (
            sqlalchemy.select(
                organisational_units_with_children.c.organisational_unit_id,
                organisational_units_with_children.c.highest_parent_organisational_unit_id.label(
                    "original_highest_parent_organisational_unit_id"
                ),
            )
            .select_from(organisational_units_with_children)
            .join(
                OrganisationalUnit, OrganisationalUnit.id == organisational_units_with_children.c.organisational_unit_id
            )
            .where(OrganisationalUnit.type_id == 17281)
            .cte()
        )

        division_units_children = queries.organisational_units.select_units_with_all_children(division_units).cte()

        division_units_with_children = (
            sqlalchemy.select(
                division_units_children.c.organisational_unit_id,
                division_units_children.c.highest_parent_organisational_unit_id.label(
                    "division_organisational_unit_id"
                ),
                division_units.c.original_highest_parent_organisational_unit_id.label(
                    "highest_parent_organisational_unit_id"
                ),
            )
            .select_from(division_units_children)
            .join(
                division_units,
                division_units_children.c.highest_parent_organisational_unit_id
                == division_units.c.organisational_unit_id,
            )
            .cte()
        )

        research_outputs_for_divisions = (
            queries.research_outputs.add_current_publication_status(
                queries.select_research_outputs_for_units(
                    division_units_with_children,
                    outerjoin=True,
                    rightjoin=True,
                ).cte()
            )
        ).cte()

        research_outputs_for_divisions_filtered = filter_research_outputs(research_outputs_for_divisions)

        research_outputs_for_divisions_counts = (
            sqlalchemy.select(
                research_outputs_for_divisions_filtered.c.division_organisational_unit_id.label(
                    "organisational_unit_id"
                ),
                sqlalchemy.func.count(
                    sqlalchemy.func.distinct(research_outputs_for_divisions_filtered.c.research_output_id)
                ).label("research_outputs_count"),
            )
            .select_from(research_outputs_for_divisions_filtered)
            .group_by(research_outputs_for_divisions_filtered.c.division_organisational_unit_id)
        ).cte()

        division_units_with_parents = (
            sqlalchemy.select(
                division_units_with_children.c.division_organisational_unit_id,
                division_units_with_children.c.highest_parent_organisational_unit_id,
            )
            .select_from(division_units_with_children)
            .group_by(
                division_units_with_children.c.division_organisational_unit_id,
                division_units_with_children.c.highest_parent_organisational_unit_id,
            )
            .cte()
        )

        research_outputs_for_divisions_counts_named = (
            sqlalchemy.select(
                research_outputs_for_divisions_counts.c.organisational_unit_id,
                division_names.name_ru,
                division_units_with_parents.c.highest_parent_organisational_unit_id,
                highest_parent_names.name_ru.label("highest_parent_name_ru"),
                research_outputs_for_divisions_counts.c.research_outputs_count,
            )
            .select_from(research_outputs_for_divisions_counts)
            .join(
                division_units_with_parents,
                division_units_with_parents.c.division_organisational_unit_id
                == research_outputs_for_divisions_counts.c.organisational_unit_id,
            )
            .join(
                division_names,
                division_names.id == division_units_with_parents.c.division_organisational_unit_id,
            )
            .join(
                highest_parent_names,
                highest_parent_names.id == division_units_with_parents.c.highest_parent_organisational_unit_id,
            )
        ).cte()

        return (
            sqlalchemy.select(
                sqlalchemy.cast(
                    research_outputs_for_divisions_counts_named.c.organisational_unit_id, sqlalchemy.String
                ).label("organisational_unit_id"),
                research_outputs_for_divisions_counts_named.c.name_ru,
                sqlalchemy.cast(
                    research_outputs_for_divisions_counts_named.c.highest_parent_organisational_unit_id,
                    sqlalchemy.String,
                ).label("highest_parent_organisational_unit_id"),
                research_outputs_for_divisions_counts_named.c.highest_parent_name_ru.label(
                    "highest_parent_organisational_unit_name_ru"
                ),
                research_outputs_for_divisions_counts_named.c.research_outputs_count,
            )
            .select_from(research_outputs_for_divisions_counts_named)
            .limit(5000)
        )

    def build_research_outputs_for_persons_counts():

        persons = queries.select_persons_for_units(
            organisational_units_with_children,
            staff=True,
            student=True,
            rightjoin=True,
        ).cte()

        research_outputs_for_persons = (
            queries.research_outputs.add_current_publication_status(
                queries.select_research_outputs_for_persons(
                    persons,
                    outerjoin=True,
                    rightjoin=True,
                ).cte()
            )
        ).cte()

        research_outputs_for_persons_filtered = filter_research_outputs(research_outputs_for_persons)

        research_outputs_for_persons_counts_all = (
            sqlalchemy.select(
                research_outputs_for_persons_filtered.c.person_id,
                sqlalchemy.func.count(
                    sqlalchemy.func.distinct(research_outputs_for_persons_filtered.c.research_output_id)
                ).label("research_outputs_count"),
            )
            .select_from(research_outputs_for_persons_filtered)
            .group_by(research_outputs_for_persons_filtered.c.person_id)
        ).cte()

        research_outputs_for_persons_counts = (
            (
                sqlalchemy.select(research_outputs_for_persons_counts_all)
                .select_from(research_outputs_for_persons_counts_all)
                .where(research_outputs_for_persons_counts_all.c.research_outputs_count > 0)
                .cte()
            )
            if exclude_persons_without_research_outuputs
            else research_outputs_for_persons_counts_all
        )

        research_outputs_for_persons_counts_named = (
            sqlalchemy.select(
                research_outputs_for_persons_counts.c.person_id,
                Person.first_name,
                Person.last_name,
                research_outputs_for_persons_counts.c.research_outputs_count,
                persons.c.organisational_unit_id,
                unit_names.name_ru,
                persons.c.highest_parent_organisational_unit_id,
                highest_parent_names.name_ru.label("highest_parent_name_ru"),
            )
            .select_from(research_outputs_for_persons_counts)
            .join(Person, Person.id == research_outputs_for_persons_counts.c.person_id)
            .join(persons, persons.c.person_id == research_outputs_for_persons_counts.c.person_id)
            .join(
                unit_names,
                unit_names.id == persons.c.organisational_unit_id,
            )
            .join(
                highest_parent_names,
                highest_parent_names.id == persons.c.highest_parent_organisational_unit_id,
            )
        ).cte()

        return (
            sqlalchemy.select(
                sqlalchemy.cast(research_outputs_for_persons_counts_named.c.person_id, sqlalchemy.String).label(
                    "person_id"
                ),
                research_outputs_for_persons_counts_named.c.first_name,
                research_outputs_for_persons_counts_named.c.last_name,
                research_outputs_for_persons_counts_named.c.research_outputs_count,
                sqlalchemy.cast(
                    research_outputs_for_persons_counts_named.c.organisational_unit_id, sqlalchemy.String
                ).label("organisational_unit_id"),
                research_outputs_for_persons_counts_named.c.name_ru.label("organisational_unit_name_ru"),
                sqlalchemy.cast(
                    research_outputs_for_persons_counts_named.c.highest_parent_organisational_unit_id, sqlalchemy.String
                ).label("highest_parent_organisational_unit_id"),
                research_outputs_for_persons_counts_named.c.highest_parent_name_ru.label(
                    "highest_parent_organisational_unit_name_ru"
                ),
            )
            .select_from(research_outputs_for_persons_counts_named)
            .limit(5000)
        )

    state: AppState = dash.get_app().server.config["APP_STATE"]
    with state.engine.connect() as conn:
        research_outputs_for_units_counts_df = pl.read_database(
            build_research_outputs_for_units_counts(),
            conn,
        )
        research_outputs_for_divisions_counts_df = pl.read_database(
            build_research_outputs_for_divisions_counts(),
            conn,
        )
        research_outputs_for_persons_counts_df = pl.read_database(
            build_research_outputs_for_persons_counts(),
            conn,
        )

    def add_truncated(df):

        if len(df) > 0:
            return df.with_columns(
                [
                    pl.when((pl.len() > 0) & (pl.col("name_ru").str.len_chars() > 20))
                    .then(pl.col("name_ru").str.slice(0, 20) + "...")
                    .otherwise(pl.col("name_ru"))
                    .alias("name_ru_truncated")
                ]
            )
        else:
            return df.with_columns([pl.col("name_ru").alias("name_ru_truncated")])

    research_outputs_for_units_counts_df = add_truncated(research_outputs_for_units_counts_df)
    research_outputs_for_divisions_counts_df = add_truncated(research_outputs_for_divisions_counts_df)

    def build_research_outputs_for_units_counts_fig(df):
        fig = px.bar(
            df.unique(pl.col("organisational_unit_id")).sort(pl.col("research_outputs_count"), descending=True),
            x="organisational_unit_id",
            y="research_outputs_count",
            labels={
                "research_outputs_count": "Количество результатов исследований",
            },
            custom_data=["name_ru", "organisational_unit_id"],
            hover_name="name_ru",
            height=500,
        )

        fig.update_layout(
            xaxis={
                "type": "category",
                "tickmode": "array",
                "tickvals": df["organisational_unit_id"].to_list(),
                "ticktext": df["name_ru_truncated"].to_list(),
                "title": "Организационная единица",
            }
        )

        fig.update_traces(
            hovertemplate="<br>".join(
                [
                    "<b>%{customdata[0]}</b>",
                    "ID: %{customdata[1]}",
                    "Количество: %{y}",
                    "<extra></extra>",
                ]
            )
        )

        return fig

    def build_research_outputs_for_persons_counts_fig(df):
        fig = px.bar(
            df.unique(pl.col("person_id")).sort(pl.col("research_outputs_count"), descending=True),
            x="person_id",
            y="research_outputs_count",
            labels={
                "research_outputs_count": "Количество результатов исследований",
            },
            custom_data=["first_name", "last_name", "person_id"],
            hover_name="first_name",
            height=500,
        )

        fig.update_layout(
            xaxis={
                "type": "category",
                "tickmode": "array",
                "tickvals": df["person_id"].to_list(),
                "ticktext": df["first_name"].to_list(),
                "title": "Персона",
            }
        )

        fig.update_traces(
            hovertemplate="<br>".join(
                [
                    "<b>%{customdata[0]} %{customdata[1]}</b>",
                    "ID: %{customdata[2]}",
                    "Количество: %{y}",
                    "<extra></extra>",
                ]
            )
        )

        return fig

    return dict(
        table_units=research_outputs_for_units_counts_df.to_dicts(),
        graph_units=build_research_outputs_for_units_counts_fig(research_outputs_for_units_counts_df),
        table_persons=research_outputs_for_persons_counts_df.to_dicts(),
        graph_persons=build_research_outputs_for_persons_counts_fig(research_outputs_for_persons_counts_df),
        table_divisions=research_outputs_for_divisions_counts_df.to_dicts(),
        graph_divisions=build_research_outputs_for_units_counts_fig(research_outputs_for_divisions_counts_df),
    )
