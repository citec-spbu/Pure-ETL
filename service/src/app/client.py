import dash
import plotly.io as pio
from dash import (
    Dash,
    Input,
    Output,
    Patch,
    State,
    callback,
    clientside_callback,
    dcc,
    html,
)

from app.client_types import AppState
from app.config import Config
from app.database import init_db


def new_app_state() -> AppState:
    config = Config.from_file("config.toml")
    engine = init_db(config)
    return AppState(config=config, engine=engine)


def main():
    state = new_app_state()

    app = Dash(use_pages=True)

    app.server.config["APP_STATE"] = state

    app.layout = html.Div(
        className="vertical-content vertical-content_large-gap",
        children=[
            dcc.Store(id="theme-store", storage_type="local"),
            html.Div(
                className=(
                    "padded-box horizontal-content horizontal-content_large-gap "
                    "horizontal-content_spread horizontal-content_center"
                ),
                children=[
                    html.Div(
                        className="horizontal-content horizontal-content_large-gap",
                        children=[
                            html.Div(children="Dash App"),
                            html.Div(
                                className="horizontal-content",
                                children=[
                                    html.Div(
                                        dcc.Link(
                                            f"{page['name']}",
                                            className="link",
                                            href=page["relative_path"],
                                        )
                                    )
                                    for page in dash.page_registry.values()
                                ],
                            ),
                        ],
                    ),
                    dcc.Button(
                        "Toggle Dark Mode",
                        id="theme-toggle",
                        className="button",
                        n_clicks=0,
                    ),
                ],
            ),
            dash.page_container,
        ],
    )

    app.run(debug=True)


clientside_callback(
    """
    function(n_clicks, current_store) {
        let theme = current_store || 'light';
        if (n_clicks > 0) {
            theme = theme === 'dark' ? 'light' : 'dark';
        }

        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-ag-theme-mode', theme);

        return theme;
    }
    """,
    Output("theme-store", "data"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data"),
)


@callback(
    dict(
        graph=Output("faculty_persons_graph", "figure", allow_duplicate=True),
    ),
    dict(
        theme=Input("theme-store", "data"),
    ),
    dict(
        graph=State("faculty_persons_graph", "figure"),
    ),
    prevent_initial_call=True,
)
def sync_all_graphs(inputs, state):
    template = "plotly_dark" if inputs.get("theme") == "dark" else "plotly_white"

    template = pio.templates[template]

    fig = Patch()
    fig["layout"]["template"] = template

    return {
        "graph": fig,
    }


if __name__ == "__main__":
    main()
