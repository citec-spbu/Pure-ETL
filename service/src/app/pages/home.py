import dash
from dash import html

from app.aio_components.tabs_aio import TabsAIO
from app.ui_parts.search_persons import search_persons_element
from app.ui_parts.search_research_outputs import (
    search_research_outputs_element,
)
from app.ui_parts.search_units import search_units_element

dash.register_page(__name__, path="/", order=0)


def layout():
    return html.Div(
        className="padded-box vertical-content vertical-content_large-gap",
        children=[
            html.Div(
                [
                    html.H1("Home"),
                    html.P(
                        "Домашняя страница ничего особенного из себя не представляет. "
                        "Ниже можно попробовать поискать данные по разным таблицам. "
                        "Конфигурация поиска синхронизируется между перезагрузками страницы и между страницами с "
                        "помощью локального хранилища, но результаты поиска должны быть получены каждый раз заново."
                    ),
                    html.P(
                        "Вкладки представленные ниже, как и на других страницах, следуют eager loading, это нужно для "
                        "того, чтобы загрузить предыдущую конфигурацию из local storage при загрузке страницы. "
                        "Но это значит что все они одновременно подгружаются и производят запросы в бд. Можно считать "
                        "что с такими вкладками конфигурация такая же, как если бы весь их контент просто находился на "
                        "странице последовательно, вкладки просто упрощают навигацию."
                    ),
                ]
            ),
            TabsAIO(
                "tabs-searching",
                [
                    {
                        "label": "Поиск по организационным единицам",
                        "content": [search_units_element()],
                    },
                    {
                        "label": "Поиск по персонам",
                        "content": [search_persons_element()],
                    },
                    {
                        "label": "Поиск по результатам исследований",
                        "content": [search_research_outputs_element()],
                    },
                ],
            ),
        ],
    )
