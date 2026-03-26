import dash
from app.config import Config
from app.database import init_db
from app.models import Person
import sqlalchemy
import dash_ag_grid as dag
from dash import Dash, html, dcc, callback, Output, Input, State
import polars as pl
import plotly.express as px
from sqlalchemy import Engine


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


def collect(state: AppState) -> pl.DataFrame:
    return (
        pl.read_database(
            sqlalchemy.select(
                sqlalchemy.cast(Person.id, sqlalchemy.String),
                Person.name,
                Person.raw,
                Person.raw["staffOrganisationAssociations"].label("associations"),
            ),
            state.engine.connect(),
        )
        .explode("associations")
        .with_columns(
            pl.col("associations")
            .struct.field("organisationalUnit")
            .struct.field("uuid")
            .alias("unit_id"),
            pl.col("associations")
            .struct.field("organisationalUnit")
            .struct.field("name")
            .struct.field("text")
            .list.filter(pl.element().struct["locale"] == "ru_RU")
            .list.first()
            .struct["value"]
            .alias("unit_name"),
        )
        .drop("raw")
        .drop("associations")
        .unique([pl.col("person_id"), pl.col("unit_id")])
    )


def main():
    state = new_app_state()
    df = collect(state)

    app = Dash()

    app.layout = [
        html.H1(children="Dash App", style={"textAlign": "center"}),
        html.Div(children="All persons"),
        dag.AgGrid(
            rowData=df.to_dicts(),
            columnDefs=[{"field": i} for i in df.columns],
        ),
        html.Div(children="Units"),
        dcc.Graph(figure={}, id="graph"),
        dcc.Input(id="input"),
        dcc.Button("Submit", id="submit"),
        dag.AgGrid(
            columnDefs=[{"field": i} for i in ["unit_id", "unit_name"]], id="table"
        ),
    ]

    app.server.config["APP_STATE"] = state

    app.run(debug=True)


@callback(
    Output(component_id="graph", component_property="figure"),
    Output(component_id="table", component_property="rowData"),
    Input(component_id="submit", component_property="n_clicks"),
    State(component_id="input", component_property="value"),
)
def update_graph(clicks, input):
    state: AppState = dash.get_app().server.config["APP_STATE"]
    df = collect(state)
    units = df.group_by(pl.col("unit_id"), pl.col("unit_name")).agg(
        pl.col("person_id").len().alias("count")
    )
    if input is not None and len(input) > 0:
        units = units.filter(pl.col("unit_name").str.contains(input))
    fig = px.bar(
        units,
        x="unit_id",
        y="count",
        labels={"unit_id": "Unit id", "count": "Number of people"},
        hover_name="unit_name",
        height=800,
    )
    rowData = units.to_dicts()
    return (fig, rowData)


if __name__ == "__main__":
    main()
