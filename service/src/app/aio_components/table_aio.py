import uuid
from typing import Any

import dash_ag_grid as dag
from dash import MATCH, Input, Output, callback, dcc, html


class TableAIO(html.Div):
    class ids:
        def ag_grid(aio_id: Any):
            return {
                "component": "TableAIO",
                "subcomponent": "ag_grid",
                "aio_id": aio_id,
            }

        def download_csv_button(aio_id: Any):
            return {
                "component": "TableAIO",
                "subcomponent": "download_csv_button",
                "aio_id": aio_id,
            }

        def clear_column_state_button(aio_id: Any):
            return {
                "component": "TableAIO",
                "subcomponent": "clear_column_state_button",
                "aio_id": aio_id,
            }

        def clear_filters_button(aio_id: Any):
            return {
                "component": "TableAIO",
                "subcomponent": "clear_filters_button",
                "aio_id": aio_id,
            }

        def size_to_fit_button(aio_id: Any):
            return {
                "component": "TableAIO",
                "subcomponent": "size_to_fit_button",
                "aio_id": aio_id,
            }

    ids = ids

    def __init__(self, aio_id=None, csv_filename=None, column_defs=None):
        if column_defs is None:
            column_defs = []
        if aio_id is None:
            aio_id = str(uuid.uuid4())
        if csv_filename is None:
            csv_filename = aio_id

        # todo: add props customization

        super().__init__(
            className="vertical-content",
            children=[
                dag.AgGrid(
                    id=self.ids.ag_grid(aio_id),
                    rowData=[],
                    columnDefs=column_defs,
                    dashGridOptions={
                        "pagination": True,
                        "paginationPageSize": 10,
                        "paginationPageSizeSelector": [10, 20, 50, 100],
                        "enableCellTextSelection": True,
                        "ensureDomOrder": True,
                        "maintainColumnOrder": True,
                        "rowSelection": {"mode": "multiRow"},
                        "animateRows": False,
                        "suppressColumnMoveAnimation": True,
                        "domLayout": "autoHeight",
                    },
                    style={"height": None},
                    persistence=True,
                    persistence_type="session",
                    defaultColDef={"filter": True, "cellDataType": False},
                    persisted_props=["columnState", "rowSelection", "filterModel"],
                    csvExportParams={
                        "fileName": f"{csv_filename}.csv",
                    },
                ),
                html.Div(
                    className="horizontal-content horizontal-content_small-gap",
                    children=[
                        dcc.Button(
                            "Download CSV",
                            id=self.ids.download_csv_button(aio_id),
                            className="button",
                            n_clicks=0,
                        ),
                        dcc.Button(
                            "Clear column state",
                            id=self.ids.clear_column_state_button(aio_id),
                            className="button",
                        ),
                        dcc.Button(
                            "Clear filters",
                            id=self.ids.clear_filters_button(aio_id),
                            className="button",
                        ),
                        dcc.Button(
                            "Size to fit",
                            id=self.ids.size_to_fit_button(aio_id),
                            className="button",
                        ),
                    ],
                ),
            ],
        )

    @callback(
        Output(component_id=ids.ag_grid(MATCH), component_property="exportDataAsCsv"),
        Input(component_id=ids.download_csv_button(MATCH), component_property="n_clicks"),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks):
        return bool(n_clicks)

    @callback(
        Output(component_id=ids.ag_grid(MATCH), component_property="resetColumnState"),
        Input(
            component_id=ids.clear_column_state_button(MATCH),
            component_property="n_clicks",
        ),
        prevent_initial_call=True,
    )
    def reset_columns(n_clicks):
        return True

    @callback(
        Output(component_id=ids.ag_grid(MATCH), component_property="filterModel"),
        Input(component_id=ids.clear_filters_button(MATCH), component_property="n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(n_clicks):
        return {}

    @callback(
        Output(component_id=ids.ag_grid(MATCH), component_property="columnSize"),
        Input(
            component_id=ids.size_to_fit_button(MATCH),
            component_property="n_clicks",
        ),
        prevent_initial_call=True,
    )
    def size_to_fit(n_clicks):
        return "sizeToFit"
