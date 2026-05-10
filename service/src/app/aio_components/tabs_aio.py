import uuid
from typing import Any

from dash import ALL, MATCH, Input, Output, State, callback, html

from app.ui_parts.tabs import generate_tabs


class TabsAIO(html.Div):
    """
    Tabs that eagerly load all their content.

    Example usage:
    ```
    TabsAIO(
        "some-unique-id",
        [
            {
                "label": "Tab 1",
                "content": [html.Div("Tab 1 content")],
            },
            {
                "label": "Tab 2",
                "content": [html.Div("Tab 2 content")],
            },
        ],
    )
    ```
    """

    class ids:
        def tabs(aio_id: Any):
            return {
                "component": "TabsAIO",
                "subcomponent": "tabs",
                "aio_id": aio_id,
            }

        def content(aio_id: Any, tab_number: Any):
            return {
                "component": "TabsAIO",
                "subcomponent": "content",
                "aio_id": aio_id,
                "tab_number": tab_number,
            }

    ids = ids

    def __init__(self, aio_id=None, tabs=None):
        if tabs is None:
            tabs = []
        if aio_id is None:
            aio_id = str(uuid.uuid4())
        super().__init__(
            className="shadow",
            children=[
                generate_tabs(self.ids.tabs(aio_id), [tab["label"] for tab in tabs]),
                html.Div(
                    className="padded-box",
                    children=[
                        html.Div(
                            id=self.ids.content(aio_id, i + 1),
                            className="hidden",
                            children=tab["content"],
                        )
                        for i, tab in enumerate(tabs)
                    ],
                ),
            ],
        )

    @callback(
        Output(ids.content(MATCH, ALL), "className"),
        Input(ids.tabs(MATCH), "value"),
        State(ids.content(MATCH, ALL), "className"),
    )
    def switch_tab(active_tab, tabs):
        return ["" if active_tab == f"tab-{i + 1}" else "hidden" for i, _ in enumerate(tabs)]
