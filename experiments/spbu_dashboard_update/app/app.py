import os

import dash
from dash import html, page_container
import dash_bootstrap_components as dbc
from utils import logger
from etl import ensure_data

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.FLATLY])
server = app.server


# ===== НАВИГАЦИОННАЯ ПАНЕЛЬ =====
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink(page['name'], href=page['relative_path']))
        for page in dash.page_registry.values()
        if page.get('path_template') is None
    ],
    brand="SPBU Dashboard",
    brand_href="/",
    color="primary",
    dark=True,
    className="mb-4"
)

# ===== ОСНОВНОЙ LAYOUT =====
app.layout = html.Div([
    navbar,
    page_container
])

# ===== ЗАПУСК =====
if __name__ == '__main__':
    # debug включается через DASH_DEBUG=1; по умолчанию выключен,
    debug = os.environ.get('DASH_DEBUG', '0').lower() in ('1', 'true', 'yes')

    # Авто-загрузка данных: если pure_data.db пуст/отсутствует — ETL запуститс ясам (нужен интернет). Отключить можно AUTO_ETL=0.
    if os.environ.get('AUTO_ETL', '1').lower() not in ('0', 'false', 'no'):
        if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            try:
                ensure_data()
            except Exception as e:
                logger.error(f"Автозагрузка данных не удалась: {e}")

    logger.info("Зарегистрированные страницы: %s", sorted(dash.page_registry.keys()))
    app.run(host='0.0.0.0', port=8050, debug=debug)

