import uuid
from typing import Any

import dash
from dash import MATCH, Input, Output, State, callback, ctx, dcc, html

from app.aio_components.collapse_aio import CollapseAIO


class ArbitraryDropdownAIO(html.Div):
    """
    Multiselect dropdown with editable set of options.
    Supports a list of default options that are always available.
    Selected values, as well as the edited list of options, are persisted.
    """

    class ids:
        def store(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "store",
                "aio_id": aio_id,
            }

        def store_init(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "store_init",
                "aio_id": aio_id,
            }

        def dropdown(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "dropdown",
                "aio_id": aio_id,
            }

        def preview(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "preview",
                "aio_id": aio_id,
            }

        def label_input(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "label_input",
                "aio_id": aio_id,
            }

        def value_input(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "value_input",
                "aio_id": aio_id,
            }

        def add_button(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "add_button",
                "aio_id": aio_id,
            }

        def remove_button(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "remove_button",
                "aio_id": aio_id,
            }

        def clear_button(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "clear_button",
                "aio_id": aio_id,
            }

        def clear_options_button(aio_id: Any):
            return {
                "component": "ArbitraryDropdownAIO",
                "subcomponent": "clear_options_button",
                "aio_id": aio_id,
            }

    ids = ids

    def __init__(self, aio_id=None, initial_options=None, placeholder="Select values"):
        if initial_options is None:
            initial_options = []
        if aio_id is None:
            aio_id = str(uuid.uuid4())

        # todo: add props customization

        super().__init__(
            className="vertical-content",
            children=[
                dcc.Store(
                    id=self.ids.store(aio_id),
                    storage_type="local",
                    data={"options": [], "values": []},
                ),
                dcc.Store(
                    id=self.ids.store_init(aio_id),
                    storage_type="memory",
                    data=initial_options,
                ),
                dcc.Dropdown(
                    id=self.ids.dropdown(aio_id),
                    multi=True,
                    searchable=True,
                    debounce=True,
                    placeholder=placeholder,
                ),
                html.Div(
                    dcc.Button(
                        "Очистить добавленные опции",
                        id=self.ids.clear_options_button(aio_id),
                        className="button",
                    ),
                ),
                CollapseAIO(
                    aio_id=f"{aio_id}-collapse-selected",
                    label="Показать/спрятать выбранное",
                    content=html.Div(
                        [
                            html.P(children="Selected:"),
                            html.Ul(className="list", id=self.ids.preview(aio_id)),
                        ]
                    ),
                ),
                CollapseAIO(
                    aio_id=f"{aio_id}-collapse-add-item",
                    label="Добавить/удалить опцию",
                    content=html.Div(
                        [
                            html.P(children="Add another item to options, or remove one:"),
                            dcc.Input(
                                id=self.ids.label_input(aio_id),
                                className="dcc-input",
                                name="Label",
                                placeholder="Label",
                                persistence=True,
                            ),
                            dcc.Input(
                                id=self.ids.value_input(aio_id),
                                className="dcc-input",
                                name="Value",
                                placeholder="Value",
                                persistence=True,
                            ),
                            html.Div(
                                className="horizontal-content horizontal-content_small-gap",
                                children=[
                                    dcc.Button(
                                        "Add",
                                        id=self.ids.add_button(aio_id),
                                        className="button",
                                    ),
                                    dcc.Button(
                                        "Remove",
                                        id=self.ids.remove_button(aio_id),
                                        className="button",
                                    ),
                                    dcc.Button(
                                        "Clear inputs",
                                        id=self.ids.clear_button(aio_id),
                                        className="button",
                                    ),
                                ],
                            ),
                        ]
                    ),
                ),
            ],
        )

    @callback(
        dict(
            preview=Output(ids.preview(MATCH), "children"),
            options=Output(ids.dropdown(MATCH), "options"),
            selected_values=Output(ids.dropdown(MATCH), "value"),
            store_data=Output(ids.store(MATCH), "data"),
            clear_label=Output(ids.label_input(MATCH), "value"),
            clear_value=Output(ids.value_input(MATCH), "value"),
        ),
        dict(
            add_button=Input(ids.add_button(MATCH), "n_clicks"),
            remove_button=Input(ids.remove_button(MATCH), "n_clicks"),
            clear_button=Input(ids.clear_button(MATCH), "n_clicks"),
            clear_options_button=Input(ids.clear_options_button(MATCH), "n_clicks"),
            selected_values=Input(ids.dropdown(MATCH), "value"),
        ),
        dict(
            label=State(ids.label_input(MATCH), "value"),
            value=State(ids.value_input(MATCH), "value"),
            options=State(ids.dropdown(MATCH), "options"),
            initial_options=State(ids.store_init(MATCH), "data"),
            store=State(ids.store(MATCH), "data"),
        ),
    )
    def update_unit_input(inputs, state):
        selected_values = inputs["selected_values"] or []
        label = state["label"]
        value = state["value"]
        options = state["options"] or []
        initial_options = state["initial_options"]
        store = state["store"]

        if type(store) is not dict:
            store = {
                "options": [],
                "values": [],
            }

        changed = {
            "options": False,
            "selected_values": False,
            "inputs": False,
        }

        if not ctx.triggered:
            for v in store["values"]:
                if v not in selected_values:
                    selected_values.append(v)
                    changed["selected_values"] = True

        for stored_option in initial_options + store["options"]:
            if stored_option["value"] not in [option["value"] for option in options or []]:
                options.append(stored_option)
                changed["options"] = True
            else:
                for option in options:
                    if option["value"] == stored_option["value"] and option["label"] != stored_option["label"]:
                        option["label"] = stored_option["label"]
                        changed["options"] = True

        if ctx.triggered_id and ctx.triggered_id.get("subcomponent") == "add_button" and value:
            changed["inputs"] = True
            if value in [option["value"] for option in options or []]:
                for option in options:
                    if option["value"] == value:
                        option["label"] = f"{label} - {value}" if label else f"No label - {value}"
                        changed["options"] = True
                if value not in selected_values:
                    selected_values.append(value)
                    changed["selected_values"] = True
            else:
                options.append(
                    {
                        "value": value,
                        "label": (f"{label} - {value}" if label else f"No label - {value}"),
                    }
                )
                selected_values.append(value)
                changed["options"] = True
                changed["selected_values"] = True

        if ctx.triggered_id and ctx.triggered_id.get("subcomponent") == "remove_button":
            changed["inputs"] = True
            options = [option for option in options if option["value"] != value]
            selected_values = [v for v in selected_values if v != value]
            changed["options"] = True
            changed["selected_values"] = True

        if ctx.triggered_id and ctx.triggered_id.get("subcomponent") == "clear_button":
            changed["inputs"] = True

        if ctx.triggered_id and ctx.triggered_id.get("subcomponent") == "clear_options_button":
            options = initial_options
            selected_values = []
            changed["options"] = True
            changed["selected_values"] = True

        new_store = {
            "options": [option for option in options],
            "values": [value for value in selected_values],
        }

        return {
            "preview": list(
                map(
                    lambda x: html.Li(className="list__item", children=html.Pre(x)),
                    selected_values,
                )
            )
            or html.Li(className="list__item", children="Empty"),
            "options": options if changed["options"] else dash.no_update,
            "selected_values": (selected_values if changed["selected_values"] else dash.no_update),
            "store_data": new_store,
            "clear_label": "" if changed["inputs"] else dash.no_update,
            "clear_value": "" if changed["inputs"] else dash.no_update,
        }
