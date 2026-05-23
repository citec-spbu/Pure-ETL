import uuid
from typing import Any

import dash
from dash import MATCH, Input, Output, State, callback, dcc, html


class CollapseAIO(html.Div):
    """
    Collapse that always eagerly loads its content

    Example usage:
    ```
    CollapseAIO(
        "some-unique-id",
        "Some label",
        [html.Div("Some content")],
    )
    ```
    """

    class ids:
        def button(aio_id: Any):
            return {
                "component": "CollapseAIO",
                "subcomponent": "button",
                "aio_id": aio_id,
            }

        def arrow(aio_id: Any):
            return {
                "component": "CollapseAIO",
                "subcomponent": "arrow",
                "aio_id": aio_id,
            }

        def memory_store(aio_id: Any):
            return {
                "component": "CollapseAIO",
                "subcomponent": "memory_store",
                "aio_id": aio_id,
            }

        def store(aio_id: Any):
            return {
                "component": "CollapseAIO",
                "subcomponent": "store",
                "aio_id": aio_id,
            }

        def content(aio_id: Any):
            return {
                "component": "CollapseAIO",
                "subcomponent": "content",
                "aio_id": aio_id,
            }

    ids = ids

    def __init__(self, aio_id=None, label="Collapse", content=None, default_hidden: bool = False):
        if content is None:
            content = []
        if aio_id is None:
            aio_id = str(uuid.uuid4())
        super().__init__(
            children=[
                dcc.Store(
                    id=self.ids.memory_store(aio_id),
                    storage_type="memory",
                    data={"default_hidden": default_hidden},
                ),
                dcc.Store(id=self.ids.store(aio_id), storage_type="local", data={}),
                dcc.Button(
                    id=self.ids.button(aio_id),
                    className="collapse-button",
                    children=[html.Div(id=self.ids.arrow(aio_id), className="collapse-button__arrow-right"), label],
                ),
                html.Div(
                    id=self.ids.content(aio_id),
                    className="",
                    children=content,
                ),
            ],
        )

    @callback(
        dict(
            class_name=Output(ids.content(MATCH), "className"),
            arrow=Output(ids.arrow(MATCH), "className"),
            store_data=Output(ids.store(MATCH), "data"),
        ),
        dict(
            button=Input(ids.button(MATCH), "n_clicks"),
        ),
        dict(
            store_data=State(ids.store(MATCH), "data"),
            memory_store_data=State(ids.memory_store(MATCH), "data"),
            class_name=State(ids.content(MATCH), "className"),
        ),
    )
    def switch_tab(inputs, state):
        hidden = state["store_data"].get("hidden", state["memory_store_data"]["default_hidden"])
        if dash.ctx.triggered_id is not None:
            hidden = not hidden
        arrow = "collapse-button__arrow-right" if hidden else "collapse-button__arrow-down"
        class_name = "hidden" if hidden else ""
        return dict(
            class_name=class_name,
            arrow=arrow,
            store_data={"hidden": hidden},
        )
