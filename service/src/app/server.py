from typing import Any, Callable
from uuid import UUID

import uvicorn
from litestar import Litestar, get, post
from litestar.di import Provide
from litestar.exceptions import ClientException
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

import app.load.pure.classification_schemes
import app.load.pure.organisational_units
import app.load.pure.persons
import app.load.pure.research_outputs
from app.config import Config
from app.database import init_db
from app.models import (
    ClassificationScheme,
    OrganisationalUnit,
    Person,
    ResearchOutput,
)


class AppState:
    """Immutable application state"""

    config: Config
    engine: Engine
    app: Litestar

    def __init__(self, config: Config, engine: Engine, app: Litestar) -> None:
        self.config = config
        self.engine = engine
        self.app = app


class LoadData(BaseModel):
    pure_data: Any
    object_type: str


class LoadResponse(BaseModel):
    number_loaded: int


@post("/load", sync_to_thread=True)
def load(app_state: AppState, data: LoadData) -> LoadResponse:
    handler = get_load_handler(data.object_type)
    items = data.pure_data["items"]
    return handler(app_state, items)


@post("/load/{object_type:str}", sync_to_thread=True)
def load_raw(app_state: AppState, object_type: str, data: Any) -> LoadResponse:
    handler = get_load_handler(object_type)
    items = data["items"]
    return handler(app_state, items)


def get_load_handler(object_type: str) -> Callable[[AppState, list[Any]], LoadResponse]:
    try:
        return load_handlers[object_type]
    except KeyError as err:
        raise ClientException(detail="Unsupported data type") from err


def load_persons(app_state: AppState, items: list[Any]) -> LoadResponse:
    with Session(app_state.engine) as session:
        lf = app.load.pure.persons.transform(items)
        loaded = 0
        for df in lf.collect_batches(chunk_size=100):
            loaded += len(df)
            app.load.pure.persons.load(df, session, app_state.app.get_logger())
        session.commit()
        return LoadResponse(number_loaded=loaded)


def load_organisational_units(app_state: AppState, items: list[Any]) -> LoadResponse:
    with Session(app_state.engine) as session:
        lf = app.load.pure.organisational_units.transform(items)
        loaded = 0
        for df in lf.collect_batches(chunk_size=100):
            loaded += len(df)
            app.load.pure.organisational_units.load(df, session)
        session.commit()
        return LoadResponse(number_loaded=loaded)


def load_research_outputs(app_state: AppState, items: list[Any]) -> LoadResponse:
    with Session(app_state.engine) as session:
        lf = app.load.pure.research_outputs.transform(items)
        loaded = 0
        for df in lf.collect_batches(chunk_size=100):
            loaded += len(df)
            app.load.pure.research_outputs.load(df, session)
        session.commit()
        return LoadResponse(number_loaded=loaded)


def load_classification_schemes(app_state: AppState, items: list[Any]) -> LoadResponse:
    with Session(app_state.engine) as session:
        lf = app.load.pure.classification_schemes.transform(items)
        loaded = 0
        for df in lf.collect_batches(chunk_size=100):
            loaded += len(df)
            app.load.pure.classification_schemes.load(df, session)
        session.commit()
        return LoadResponse(number_loaded=loaded)


load_handlers = {
    "persons": load_persons,
    "research-outputs": load_research_outputs,
    "organisational-units": load_organisational_units,
    "classification-schemes": load_classification_schemes,
}


def reload(app_state, items, session, transform, load) -> LoadResponse:
    if len(items) == 0:
        return LoadResponse(number_loaded=0)
    lf = transform(items)
    loaded = 0
    for df in lf.collect_batches(chunk_size=100):
        loaded += len(df)
        load(df, session, logger=app_state.app.get_logger(), update_raw=False)
    session.commit()
    return LoadResponse(number_loaded=loaded)


@post("/reload/persons", sync_to_thread=True)
def reload_persons(app_state: AppState) -> LoadResponse:
    """Selects all persons raw data and tries to reload it"""
    with Session(app_state.engine) as session:
        items = list(
            session.scalars(select(Person.raw).where(Person.raw.is_not(None))).all()
        )
        return reload(
            app_state,
            items,
            session,
            app.load.pure.persons.transform,
            app.load.pure.persons.load,
        )


@post("/reload/organisational-units", sync_to_thread=True)
def reload_organisational_units(app_state: AppState) -> LoadResponse:
    """Selects all organisational units raw data and tries to reload it"""
    with Session(app_state.engine) as session:
        items = list(
            session.scalars(
                select(OrganisationalUnit.raw).where(
                    OrganisationalUnit.raw.is_not(None)
                )
            ).all()
        )
        return reload(
            app_state,
            items,
            session,
            app.load.pure.organisational_units.transform,
            app.load.pure.organisational_units.load,
        )


@post("/reload/research-outputs", sync_to_thread=True)
def reload_research_outputs(app_state: AppState) -> LoadResponse:
    """Selects all research outputs raw data and tries to reload it"""
    with Session(app_state.engine) as session:
        items = list(
            session.scalars(
                select(ResearchOutput.raw).where(ResearchOutput.raw.is_not(None))
            ).all()
        )
        return reload(
            app_state,
            items,
            session,
            app.load.pure.research_outputs.transform,
            app.load.pure.research_outputs.load,
        )


@post("/reload/classification-schemes", sync_to_thread=True)
def reload_classification_schemes(app_state: AppState) -> LoadResponse:
    """Selects all classification schemes raw data and tries to reload it"""
    with Session(app_state.engine) as session:
        items = list(
            session.scalars(
                select(ClassificationScheme.raw).where(
                    ClassificationScheme.raw.is_not(None)
                )
            ).all()
        )
        return reload(
            app_state,
            items,
            session,
            app.load.pure.classification_schemes.transform,
            app.load.pure.classification_schemes.load,
        )


def run():
    config = Config.from_file("config.toml")
    engine = init_db(config)
    logging_config = LoggingConfig(
        root={"level": config.logging.level, "handlers": ["queue_listener"]},
        formatters={"standard": {"format": config.logging.format_str}},
        log_exceptions="always",
    )
    app = Litestar(
        route_handlers=[
            load,
            load_raw,
            reload_persons,
            reload_organisational_units,
            reload_research_outputs,
            reload_classification_schemes,
        ],
        debug=True,
        request_max_body_size=50 * 1000 * 1000,
        dependencies={
            "app_state": Provide(
                lambda: AppState(config=config, engine=engine, app=app),
                sync_to_thread=True,
            )
        },
        openapi_config=OpenAPIConfig(
            title="ETL",
            version="0.0.0",
            render_plugins=[SwaggerRenderPlugin()],
        ),
        logging_config=logging_config,
    )
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
