import dash
import dash_ag_grid as dag
import plotly.express as px
import polars as pl
import sqlalchemy
from dash import Dash, Input, Output, State, callback, dcc, html
from sqlalchemy import Engine, cast

import app.queries
from app.config import Config
from app.database import init_db


def new_app_state() -> AppState:
    config = Config.from_file("config.toml")
    engine = init_db(config)
    return AppState(config=config, engine=engine)


class AppState:
    """Immutable application state"""

    config: Config
    engine: Engine

    def __init__(self, config: Config, engine: Engine) -> None:
        self.config = config
        self.engine = engine


def collect_units_with_parents(state: AppState) -> pl.DataFrame:
    conn = state.engine.connect()

    statement = app.queries.select_units_with_faculties_named().cte()

    df = pl.read_database(
        sqlalchemy.select(
            sqlalchemy.cast(statement.c.organisational_unit_id, sqlalchemy.String),
            statement.c.name_ru,
            statement.c.type_id,
            statement.c.level,
            sqlalchemy.cast(
                statement.c.highest_parent_organisational_unit_id, sqlalchemy.String
            ),
            statement.c.highest_parent_name_ru,
            statement.c.highest_parent_type_id,
        ).select_from(statement),
        conn,
    )
    conn.close()
    return df


def collect_persons_with_units(state: AppState) -> pl.DataFrame:
    conn = state.engine.connect()

    statement = app.queries.select_persons_staff_with_units_and_faculties_named().cte()

    df = pl.read_database(
        sqlalchemy.select(
            cast(statement.c.person_id, sqlalchemy.String),
            statement.c.first_name,
            statement.c.last_name,
            sqlalchemy.cast(
                statement.c.highest_parent_organisational_unit_id, sqlalchemy.String
            ),
            statement.c.highest_parent_name_ru,
            statement.c.highest_parent_type_id,
            sqlalchemy.cast(
                statement.c.organisational_unit_id, sqlalchemy.String
            ).label("linked_through_organisational_unit_id"),
            statement.c.name_ru.label("linked_through_name_ru"),
            statement.c.type_id.label("linked_through_type_id"),
            statement.c.level.label("linked_through_level"),
        ).select_from(statement),
        conn,
    )
    conn.close()
    return df


def collect_faculty_people(state: AppState) -> pl.DataFrame:
    conn = state.engine.connect()

    statement = app.queries.select_faculty_persons_count_named().cte()

    df = pl.read_database(
        sqlalchemy.select(
            sqlalchemy.cast(
                statement.c.highest_parent_organisational_unit_id, sqlalchemy.String
            ),
            statement.c.highest_parent_name_ru,
            statement.c.persons_count,
        ).select_from(statement),
        conn,
    )
    conn.close()
    return df


def main():
    state = new_app_state()
    units_with_parents = collect_units_with_parents(state)
    persons_with_units = collect_persons_with_units(state)
    faculty_persons = collect_faculty_people(state)

    app = Dash()

    app.layout = [
        html.H1(children="Dash App"),
        html.H2(children="Units with parents"),
        html.P(children="This might still work with full dataset."),
        html.P(
            children="Level 1 units with all their children selected recursively. Level 1 parent is called highest parent."
        ),
        dag.AgGrid(
            rowData=units_with_parents.to_dicts(),
            columnDefs=[
                {"field": i, "filter": True} for i in units_with_parents.columns
            ],
            dashGridOptions={
                "pagination": True,
                "enableCellTextSelection": True,
                "ensureDomOrder": True,
            },
            id="units_with_parents",
            persistence=True,
        ),
        html.H2(children="Persons - Units"),
        html.H3(children="All persons with their units"),
        html.P(children="This will likely break on full data."),
        html.P(children="Persons recursively linked to level 1 units."),
        dag.AgGrid(
            rowData=persons_with_units.to_dicts(),
            columnDefs=[
                {"field": i, "filter": True} for i in persons_with_units.columns
            ],
            dashGridOptions={
                "pagination": True,
                "enableCellTextSelection": True,
                "ensureDomOrder": True,
            },
            id="persons_with_units",
            persistence=True,
        ),
        html.H3(children="Faculties and how many people are in them"),
        html.P(children="This should work even on the full dataset"),
        html.P(
            children="Count how many persons are recursively linked to each level 1 unit, but only those level 1 units that have persons"
        ),
        dag.AgGrid(
            rowData=faculty_persons.to_dicts(),
            columnDefs=[{"field": i, "filter": True} for i in faculty_persons.columns],
            dashGridOptions={
                "pagination": True,
                "enableCellTextSelection": True,
                "ensureDomOrder": True,
            },
            id="faculty_persons",
            persistence=True,
        ),
        html.H3(children="Faculties and how many people are in them, graphically"),
        dcc.Graph(figure={}, id="faculty_persons_graph"),
        html.H4(children="Filter by unit name:"),
        dcc.Input(id="input"),
        dcc.Button("Submit", id="submit"),
    ]

    app.server.config["APP_STATE"] = state

    app.run(debug=True)


@callback(
    Output(component_id="faculty_persons_graph", component_property="figure"),
    Input(component_id="submit", component_property="n_clicks"),
    State(component_id="input", component_property="value"),
)
def update_graph(clicks, input):
    state: AppState = dash.get_app().server.config["APP_STATE"]
    units = collect_faculty_people(state)
    if input is not None and len(input) > 0:
        units = units.filter(pl.col("highest_parent_name_ru").str.contains(input))
    fig = px.bar(
        units,
        x="highest_parent_organisational_unit_id",
        y="persons_count",
        labels={
            "highest_parent_organisational_unit_id": "Unit id",
            "persons_count": "Number of people",
        },
        hover_name="highest_parent_name_ru",
        height=800,
    )
    return fig


if __name__ == "__main__":
    main()
