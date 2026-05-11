from uuid import UUID

import dash
import plotly.express as px
import polars as pl
import sqlalchemy
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate
from sqlalchemy import cast

from app import queries
from app.aio_components.arbitrary_dropdown_aio import ArbitraryDropdownAIO
from app.aio_components.collapse_aio import CollapseAIO
from app.aio_components.table_aio import TableAIO
from app.aio_components.tabs_aio import TabsAIO
from app.client_types import AppState
from app.ui_parts.find_unit_parents import find_unit_parents_element
from app.ui_parts.search_units import search_units_element

dash.register_page(__name__)


def layout():

    initial_options = [
        {
            "label": f"Факультет прикладной математики-процессов управления - {queries.pm_id}",
            "value": str(queries.pm_id),
        },
        {
            "label": f"Факультет математико-механический - {queries.mat_id}",
            "value": str(queries.mat_id),
        },
        {
            "label": f"Факультет физический - {queries.phys_id}",
            "value": str(queries.phys_id),
        },
    ]

    return html.Div(
        className="padded-box vertical-content vertical-content_large-gap",
        children=[
            html.H1("Units"),
            CollapseAIO(
                "tabs-units-searching-collapse",
                label="Показать/спрятать поиск",
                content=TabsAIO(
                    "tabs-unit-searching",
                    [
                        {
                            "label": "Поиск organisational units",
                            "content": [
                                search_units_element(
                                    additional_controls=[
                                        dcc.Button(
                                            "Add selected units",
                                            id="add-search-units-to-selection-button",
                                            className="button",
                                        )
                                    ],
                                )
                            ],
                        },
                        {
                            "label": "Найти parents organisational unit",
                            "content": [find_unit_parents_element()],
                        },
                    ],
                ),
            ),
            html.Div(
                [
                    html.Div(
                        className="horizontal-content horizontal-content_center",
                        children=[
                            html.H2(children="Выбрать organisational units"),
                            html.Abbr(
                                "?",
                                title="Выбранные organisational units используются в таблицах ниже.\n"
                                "Можно занести дополнительные опции с помощью предоставленных полей. Добавленные "
                                "опции сохраняются в local storage.",
                                className="help-icon",
                            ),
                        ],
                    ),
                    ArbitraryDropdownAIO(
                        aio_id="units-select-dropdown",
                        initial_options=initial_options,
                        placeholder="Выберите organisational units...",
                    ),
                ]
            ),
            table_tabs(initial_options),
        ],
    )


def table_tabs(initial_options):
    return TabsAIO(
        "tabs-units-flows",
        [
            {
                "label": "Подразделения выбранных organisational units",
                "content": [
                    html.Div(
                        className="horizontal-content horizontal-content_center",
                        children=[
                            html.H2(children="Подразделения выбранных organisational units"),
                            html.Abbr(
                                "?",
                                title="Выбранные organisational units (highest parent) и все их подразделения, "
                                "собранные рекурсивно. Ограничено 100.",
                                className="help-icon",
                            ),
                            dcc.Button(
                                "Add selected units",
                                id="add-child-units-to-selection-button",
                                className="button",
                            ),
                        ],
                    ),
                    TableAIO(
                        aio_id="units_with_parents",
                        column_defs=[
                            {"field": i, "colId": i}
                            for i in [
                                "organisational_unit_id",
                                "name_ru",
                                "type_id",
                                "recursion_level",
                                "highest_parent_organisational_unit_id",
                                "highest_parent_name_ru",
                                "highest_parent_type_id",
                            ]
                        ],
                    ),
                ],
            },
            {
                "label": "Persons выбранных organisational units",
                "content": [
                    html.Div(
                        className="horizontal-content horizontal-content_center",
                        children=[
                            html.H2(children="Persons выбранных organisational units"),
                            html.Abbr(
                                "?",
                                title="Все persons, которые принадлежат выбранным organisational units "
                                "(highest parent), либо напрямую, либо через подразделения.\nОграничено 100.",
                                className="help-icon",
                            ),
                        ],
                    ),
                    TableAIO(
                        aio_id="persons_with_units",
                        column_defs=[
                            {"field": i, "colId": i}
                            for i in [
                                "person_id",
                                "first_name",
                                "last_name",
                                "period_start",
                                "period_end",
                                "linked_through_organisational_unit_id",
                                "linked_through_name_ru",
                                "linked_through_type_id",
                                "linked_through_recursion_level",
                                "highest_parent_organisational_unit_id",
                                "highest_parent_name_ru",
                                "highest_parent_type_id",
                            ]
                        ],
                    ),
                ],
            },
            {
                "label": "Количество persons в выбранных organisational units",
                "content": [
                    html.Div(
                        className="horizontal-content horizontal-content_center",
                        children=[
                            html.H2(children="Persons в выбранных organisational units."),
                            html.Abbr(
                                "?",
                                title="Количество persons, которые принадлежат выбранным organisational units "
                                "(highest parent), либо напрямую, либо через подразделения.",
                                className="help-icon",
                            ),
                        ],
                    ),
                    person_count_tabs(),
                ],
            },
        ],
    )


def person_count_tabs():
    return TabsAIO(
        "faculty-persons-tabs",
        [
            {
                "label": "Table",
                "content": [
                    TableAIO(
                        aio_id="faculty_persons",
                        column_defs=[
                            {"field": i, "colId": i}
                            for i in [
                                "highest_parent_organisational_unit_id",
                                "highest_parent_name_ru",
                                "persons_count",
                            ]
                        ],
                    ),
                ],
            },
            {
                "label": "Chart",
                "content": [
                    dcc.Graph(
                        figure={},
                        id="faculty_persons_graph",
                    ),
                ],
            },
        ],
    )


def collect_units_with_parents(state: AppState, unit_ids=queries.faculties) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.select_units_with_all_children_named(
            units=queries.select_units_with_all_children(filter_units_by_id=unit_ids).cte()
        ).cte()
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String),
                statement.c.name_ru,
                statement.c.type_id,
                statement.c.recursion_level,
                sqlalchemy.cast(statement.c.highest_parent_organisational_unit_id, sqlalchemy.String),
                statement.c.highest_parent_name_ru,
                statement.c.highest_parent_type_id,
            )
            .select_from(statement)
            .limit(100),
            conn,
        )
        return df


def collect_persons_with_units(state: AppState, unit_ids=None) -> pl.DataFrame:
    if unit_ids is None:
        unit_ids = [queries.pm_id]
    with state.engine.connect() as conn:
        statement = queries.select_persons_named_for_units(
            units=queries.select_units_with_all_children_named(
                units=queries.select_units_with_all_children(filter_units_by_id=unit_ids).cte()
            ).cte(),
            # date=datetime.now(timezone.utc),
        ).cte()
        df = pl.read_database(
            sqlalchemy.select(
                cast(statement.c.person_id, sqlalchemy.String),
                statement.c.first_name,
                statement.c.last_name,
                statement.c.period_start,
                statement.c.period_end,
                sqlalchemy.cast(statement.c.highest_parent_organisational_unit_id, sqlalchemy.String),
                statement.c.highest_parent_name_ru,
                statement.c.highest_parent_type_id,
                sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String).label(
                    "linked_through_organisational_unit_id"
                ),
                statement.c.name_ru.label("linked_through_name_ru"),
                statement.c.type_id.label("linked_through_type_id"),
                statement.c.recursion_level.label("linked_through_recursion_level"),
            )
            .select_from(statement)
            .limit(100),
            conn,
        )
        return df


def collect_faculty_people(state: AppState, unit_ids=queries.faculties) -> pl.DataFrame:
    with state.engine.connect() as conn:
        statement = queries.select_highest_units_persons_count_named(
            persons=queries.select_persons_named_for_units(
                units=queries.select_units_with_all_children(
                    filter_units_by_id=unit_ids,
                ).cte(),
                # date=datetime.now(timezone.utc),
            ).cte()
        ).cte()
        df = pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(statement.c.highest_parent_organisational_unit_id, sqlalchemy.String),
                statement.c.highest_parent_name_ru,
                statement.c.persons_count,
            ).select_from(statement),
            conn,
        )
        return df


@callback(
    dict(
        t1=Output(
            TableAIO.ids.ag_grid("units_with_parents"),
            "rowData",
        ),
        t2=Output(
            TableAIO.ids.ag_grid("persons_with_units"),
            "rowData",
        ),
        t3=Output(
            TableAIO.ids.ag_grid("faculty_persons"),
            "rowData",
        ),
        fig=Output(
            "faculty_persons_graph",
            "figure",
        ),
    ),
    dict(
        unit_ids=Input(
            ArbitraryDropdownAIO.ids.dropdown("units-select-dropdown"),
            "value",
        ),
    ),
    dict(
        theme=State("theme-store", "data"),
    ),
)
def update_tables(inputs, state):
    template = "plotly_dark" if state["theme"] == "dark" else "plotly_white"
    selected_values = inputs["unit_ids"]
    state: AppState = dash.get_app().server.config["APP_STATE"]

    try:
        unit_ids = [UUID(value) for value in selected_values]
    except ValueError:
        # todo say to user that value is not uuid
        raise PreventUpdate() from None

    units_with_parents = collect_units_with_parents(state, unit_ids)
    persons_with_units = collect_persons_with_units(state, unit_ids)
    faculty_persons = collect_faculty_people(state, unit_ids)

    fig = px.bar(
        faculty_persons,
        x="highest_parent_organisational_unit_id",
        y="persons_count",
        labels={
            "highest_parent_organisational_unit_id": "Organisational unit id",
            "persons_count": "Количество persons",
        },
        hover_name="highest_parent_name_ru",
        template=template,
    )

    return dict(
        t1=units_with_parents.to_dicts(),
        t2=persons_with_units.to_dicts(),
        t3=faculty_persons.to_dicts(),
        fig=fig,
    )


@callback(
    dict(
        selection=Output(
            ArbitraryDropdownAIO.ids.dropdown("units-select-dropdown"),
            "value",
            allow_duplicate=True,
        ),
        options=Output(
            ArbitraryDropdownAIO.ids.dropdown("units-select-dropdown"),
            "options",
            allow_duplicate=True,
        ),
    ),
    dict(
        add_button_search=Input("add-search-units-to-selection-button", "n_clicks"),
        add_button_child=Input("add-child-units-to-selection-button", "n_clicks"),
    ),
    dict(
        selection=State(
            ArbitraryDropdownAIO.ids.dropdown("units-select-dropdown"),
            "value",
        ),
        options=State(
            ArbitraryDropdownAIO.ids.dropdown("units-select-dropdown"),
            "options",
        ),
        search_table=State(
            TableAIO.ids.ag_grid("search-units-field"),
            "selectedRows",
        ),
        children_table=State(
            TableAIO.ids.ag_grid("units_with_parents"),
            "selectedRows",
        ),
    ),
    prevent_initial_call=True,
)
def add_selected_units(inputs, state):
    options = {option["value"]: option for option in (state["options"] or [])}
    selection = state["selection"] or []

    if dash.ctx.triggered_id == "add-search-units-to-selection-button":
        table = state["search_table"]
    elif dash.ctx.triggered_id == "add-child-units-to-selection-button":
        table = state["children_table"]
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
