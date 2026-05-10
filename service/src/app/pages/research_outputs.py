import dash
from dash import html

from app.aio_components.collapse_aio import CollapseAIO
from app.aio_components.tabs_aio import TabsAIO
from app.ui_parts.find_organisational_unit_research_outputs import (
    find_organisational_unit_research_outputs_element,
)
from app.ui_parts.find_person_research_outputs import (
    find_person_research_outputs_element,
)
from app.ui_parts.find_research_output_organisational_units import (
    find_research_output_organisational_units_element,
)
from app.ui_parts.find_research_output_persons import (
    find_research_output_persons_element,
)
from app.ui_parts.find_unit_parents import find_unit_parents_element
from app.ui_parts.search_persons import search_persons_element
from app.ui_parts.search_research_outputs import (
    search_research_outputs_element,
)
from app.ui_parts.search_units import search_units_element

dash.register_page(__name__, path="/research-outputs")


def layout():
    return html.Div(
        className="padded-box vertical-content vertical-content_large-gap",
        children=[
            html.H1("Research outputs"),
            CollapseAIO(
                "tabs-research-outputs-searching-collapse",
                label="Показать/спрятать поиск",
                content=TabsAIO(
                    "tabs-research-outputs-searching",
                    [
                        {
                            "label": "Поиск по research outputs",
                            "content": [search_research_outputs_element()],
                        },
                        {
                            "label": "Поиск по persons",
                            "content": [search_persons_element()],
                        },
                        {
                            "label": "Поиск по organisational units",
                            "content": [search_units_element()],
                        },
                        {
                            "label": "Найти parents organisational unit",
                            "content": [find_unit_parents_element()],
                        },
                    ],
                ),
            ),
            TabsAIO(
                "tabs-research-outputs-tables",
                [
                    {
                        "label": "Organisational unit -> research outputs",
                        "content": [find_organisational_unit_research_outputs_element()],
                    },
                    {
                        "label": "Research output -> organisational units",
                        "content": [find_research_output_organisational_units_element()],
                    },
                    {
                        "label": "Person -> research outputs",
                        "content": [find_person_research_outputs_element()],
                    },
                    {
                        "label": "Research output -> persons",
                        "content": [find_research_output_persons_element()],
                    },
                ],
            ),
        ],
    )
