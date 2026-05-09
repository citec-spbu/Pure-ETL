from dash import dcc, html


def generate_tabs(id: str, labels: list[str]) -> dcc.Tabs:
    """
    Generates tabs with no content - use your own callback.
    Values are `tab-x` where x starts from 1.
    """
    return dcc.Tabs(
        id=id,
        persistence=True,
        value="tab-1",
        children=[
            dcc.Tab(
                label=label,
                value=f"tab-{i + 1}",
                className="dcc-tab",
                selected_className="dcc-tab_selected",
            )
            for i, label in enumerate(labels)
        ],
    )


def generate_tabs_with_content(id: str, tabs: list[dict]) -> html.Div:
    """
    Generates tabs with content outside - use your own callback to switch.
    Values are `tab-x` where x starts from 1.
    Use `hidden` className on elements `id-content-x`
    """
    return html.Div(
        className="shadow",
        children=[
            generate_tabs(id, [tab["label"] for tab in tabs]),
            html.Div(
                className="padded-box",
                children=[
                    html.Div(
                        id=f"{id}-content-{i + 1}",
                        className="hidden",
                        children=tab["content"],
                    )
                    for i, tab in enumerate(tabs)
                ],
            ),
        ],
    )
