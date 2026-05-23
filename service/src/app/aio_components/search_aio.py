import uuid
from typing import Any

import dash
from dash import MATCH, Input, Output, State, callback, ctx, dcc, html
from dash.exceptions import PreventUpdate

from app.aio_components.table_aio import TableAIO

_AIO_SEARCH_REGISTRY = {}


def aio_register_search(func):
    """
    Registered functions MUST have unique names.
    """
    if func.__name__ in _AIO_SEARCH_REGISTRY:
        raise RuntimeError(f"Duplicate search registration: {func.__name__}")
    _AIO_SEARCH_REGISTRY[func.__name__] = func
    return func


class SearchException(Exception):
    """Exception raised while searching."""

    pass


class SearchAIO(html.Div):
    """
    Note: to use this aio component, its aio_id have to be unique with any other component, even a different type

    Search function should return a polars dataframe
    """

    class ids:
        def store(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "store",
                "aio_id": aio_id,
            }

        def memory_store(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "memory_store",
                "aio_id": aio_id,
            }

        def search_bar(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "search_bar",
                "aio_id": aio_id,
            }

        def internal_toggles(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "internal_toggles",
                "aio_id": aio_id,
            }

        def toggles(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "toggles",
                "aio_id": aio_id,
            }

        def search_button(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "search_button",
                "aio_id": aio_id,
            }

        def clear_button(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "clear_button",
                "aio_id": aio_id,
            }

        def page_number(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "page_number",
                "aio_id": aio_id,
            }

        def page_size(aio_id: Any):
            return {
                "component": "SearchAIO",
                "subcomponent": "page_size",
                "aio_id": aio_id,
            }

    ids = ids

    def __init__(
        self,
        aio_id=None,
        search_function=None,
        placeholder="Search",
        csv_filename: str | None = None,
        column_defs=None,
        toggles=None,
        toggles_defaults=None,
        additional_controls: list | None = None,
    ):
        """
        Args:
            `additional_controls`: list of other elements that will be placed in the controls box
        """
        if search_function is None:
            raise Exception("Search function cannot be None")
        if toggles_defaults is None:
            toggles_defaults = []
        if toggles is None:
            toggles = []
        if column_defs is None:
            column_defs = []
        if aio_id is None:
            aio_id = str(uuid.uuid4())
        if additional_controls is None:
            additional_controls = []

        csv_filename = csv_filename or str(aio_id)

        # todo: add props customization

        super().__init__(
            className="vertical-content",
            children=[
                dcc.Store(
                    id=self.ids.store(aio_id),
                    storage_type="local",
                    data={},
                ),
                dcc.Store(
                    id=self.ids.memory_store(aio_id),
                    storage_type="memory",
                    data={
                        "search_function": search_function,
                        "toggles": toggles,
                        "toggles_defaults": toggles_defaults,
                        "internal_toggles": ["live_search"],
                        "internal_toggles_defaults": [],
                        "page_number_default": 1,
                        "page_size_default": 100,
                    },
                ),
                dcc.Input(
                    id=self.ids.search_bar(aio_id),
                    name="searchbar",
                    placeholder=placeholder,
                    value="",
                    className="dcc-input",
                ),
                html.Div(
                    className="horizontal-content horizontal-content_small-gap",
                    children=[
                        dcc.Button(
                            "Search",
                            id=self.ids.search_button(aio_id),
                            className="button",
                        ),
                        dcc.Button(
                            "Clear",
                            id=self.ids.clear_button(aio_id),
                            className="button",
                        ),
                        html.Div(
                            className="horizontal-content horizontal-content_small-gap",
                            children=[
                                html.Label("Page:"),
                                dcc.Input(
                                    id=self.ids.page_number(aio_id),
                                    type="number",
                                    debounce=True,
                                    className="dcc-input",
                                    style={"width": "8em"},
                                ),
                            ],
                        ),
                        html.Div(
                            className="horizontal-content horizontal-content_small-gap",
                            children=[
                                html.Label("Page size:"),
                                dcc.Input(
                                    id=self.ids.page_size(aio_id),
                                    type="number",
                                    debounce=True,
                                    className="dcc-input",
                                    style={"width": "8em"},
                                ),
                            ],
                        ),
                        dcc.Checklist(
                            className="padded-box dcc-checklist",
                            labelClassName="dcc-checklist__label",
                            inputClassName="dcc-checklist__input",
                            id=self.ids.internal_toggles(aio_id),
                            options=["live_search"],
                            inline=True,
                        ),
                        *additional_controls,
                    ],
                ),
                html.Div(
                    className="horizontal-content horizontal-content_small-gap",
                    children=[
                        dcc.Checklist(
                            className="padded-box dcc-checklist",
                            labelClassName="dcc-checklist__label",
                            inputClassName="dcc-checklist__input",
                            id=self.ids.toggles(aio_id),
                            options=toggles,
                            inline=True,
                        ),
                    ],
                ),
                TableAIO(
                    aio_id=aio_id,
                    csv_filename=csv_filename,
                    column_defs=column_defs,
                ),
            ],
        )

    @callback(
        dict(
            search_results=Output(TableAIO.ids.ag_grid(MATCH), "rowData", allow_duplicate=True),
            search_bar=Output(ids.search_bar(MATCH), "value"),
            store_data=Output(ids.store(MATCH), "data"),
            toggles_selected=Output(ids.toggles(MATCH), "value"),
            internal_toggles_selected=Output(ids.internal_toggles(MATCH), "value"),
            page_number=Output(ids.page_number(MATCH), "value"),
            page_size=Output(ids.page_size(MATCH), "value"),
        ),
        dict(
            search_button=Input(ids.search_button(MATCH), "n_clicks"),
            clear_button=Input(ids.clear_button(MATCH), "n_clicks"),
            toggles_selected=Input(ids.toggles(MATCH), "value"),
            internal_toggles_selected=Input(ids.internal_toggles(MATCH), "value"),
            search_bar=Input(ids.search_bar(MATCH), "value"),
            search_bar_submit=Input(ids.search_bar(MATCH), "n_submit"),
            page_number=Input(ids.page_number(MATCH), "value"),
            page_size=Input(ids.page_size(MATCH), "value"),
        ),
        dict(
            store_data=State(ids.store(MATCH), "data"),
            toggles_options=State(ids.toggles(MATCH), "options"),
            internal_toggles_options=State(ids.internal_toggles(MATCH), "options"),
            memory_store_data=State(ids.memory_store(MATCH), "data"),
        ),
        prevent_initial_call="initial_duplicate",
    )
    def update(inputs, state):
        update = {
            "search_bar": False,
            "toggles_selected": False,
            "internal_toggles_selected": False,
            "search_results": False,
            "page_number": False,
            "page_size": False,
        }

        # todo: implement pagination and store page inputs in storage

        store_data = state["store_data"] if type(state["store_data"]) is dict else {}

        if not ctx.triggered_id:
            search_bar = store_data.get("search_bar") or ""
            update["search_bar"] = True

            saved_toggles = store_data.get("toggles_selected")
            if saved_toggles is None:
                saved_toggles = state["memory_store_data"]["toggles_defaults"]
            toggles_selected = [
                option
                for option in (
                    saved_toggles if type(saved_toggles) is list else state["memory_store_data"]["toggles_defaults"]
                )
                if option in state["memory_store_data"]["toggles"]
            ]
            update["toggles_selected"] = True

            saved_internal_toggles = store_data.get("internal_toggles_selected")
            if saved_internal_toggles is None:
                saved_internal_toggles = state["memory_store_data"]["internal_toggles_defaults"]
            internal_toggles_selected = [
                option
                for option in (
                    saved_internal_toggles
                    if type(saved_internal_toggles) is list
                    else state["memory_store_data"]["internal_toggles_defaults"]
                )
                if option in state["memory_store_data"]["internal_toggles"]
            ]
            update["internal_toggles_selected"] = True

            page_number = store_data.get("page_number", state["memory_store_data"]["page_number_default"])
            page_size = store_data.get("page_size", state["memory_store_data"]["page_size_default"])
            update["page_number"] = True
            update["page_size"] = True
        else:
            search_bar = inputs["search_bar"] or ""
            toggles_selected = inputs["toggles_selected"] or []
            internal_toggles_selected = inputs["internal_toggles_selected"] or []
            page_number = inputs["page_number"]
            page_size = inputs["page_size"]

        if page_number is None:
            page_number = state["memory_store_data"]["page_number_default"]
            update["page_number"] = True
        if page_size is None:
            page_size = state["memory_store_data"]["page_size_default"]
            update["page_size"] = True
        if page_number < 1:
            page_number = 1
            update["page_number"] = True
        if page_size < 1:
            page_size = 1
            update["page_size"] = True

        if ctx.triggered_id and ctx.triggered_id["subcomponent"] == "clear_button":
            update["search_bar"] = True
            search_bar = ""
            update["toggles_selected"] = True
            toggles_selected = state["memory_store_data"]["toggles_defaults"]

        store_data["toggles_selected"] = toggles_selected
        store_data["search_bar"] = search_bar
        store_data["internal_toggles_selected"] = internal_toggles_selected
        store_data["page_number"] = page_number
        store_data["page_size"] = page_size

        if (
            "live_search" in internal_toggles_selected
            or (ctx.triggered_id and ctx.triggered_id["subcomponent"] == "search_button")
            or (ctx.triggered_id and ctx.triggered_id["subcomponent"] == "page_number")
            or (ctx.triggered_id and ctx.triggered_id["subcomponent"] == "page_size")
            or ctx.triggered_id is None
            or (
                ctx.triggered_id
                and ctx.triggered_id["subcomponent"] == "search_bar"
                and any(".n_submit" in key for key in ctx.triggered_prop_ids)
            )
        ):
            search = _AIO_SEARCH_REGISTRY.get(state["memory_store_data"]["search_function"])
            if search is None:
                raise RuntimeError("Search function was None")
            app_state = dash.get_app().server.config["APP_STATE"]
            toggles_state = {toggle: (toggle in toggles_selected) for toggle in state["toggles_options"]}
            try:
                search_results = search(
                    state=app_state,
                    pattern=search_bar,
                    page_number=page_number,
                    page_size=page_size,
                    toggles=toggles_state,
                ).to_dicts()
            except SearchException:
                # todo: communicate error to user
                raise PreventUpdate() from None
            update["search_results"] = True

        return {
            "search_results": (search_results if update["search_results"] else dash.no_update),
            "search_bar": search_bar if update["search_bar"] else dash.no_update,
            "store_data": store_data,
            "toggles_selected": (toggles_selected if update["toggles_selected"] else dash.no_update),
            "internal_toggles_selected": (
                internal_toggles_selected if update["internal_toggles_selected"] else dash.no_update
            ),
            "page_number": (page_number if update["page_number"] else dash.no_update),
            "page_size": (page_size if update["page_size"] else dash.no_update),
        }
