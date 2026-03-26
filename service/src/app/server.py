import pprint
from typing import Any
from uuid import UUID

import uvicorn
from litestar import Litestar, Request, get, post
from litestar.di import Provide
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

import app.load.pure.persons
from app.config import Config
from app.database import init_db
from app.models import Person


class AppState:
    """Immutable application state"""

    config: Config
    engine: Engine

    def __init__(self, config: Config, engine: Engine) -> None:
        self.config = config
        self.engine = engine


@get("/", sync_to_thread=True)
def root(app_state: AppState, request: Request) -> dict[str, str]:
    request.logger.info("This is logging")
    return {"config": pprint.pformat(app_state.config)}


class LoadData(BaseModel):
    pure_data: Any
    object_type: str


class LoadResponse(BaseModel):
    number_loaded: int


@post("/load", sync_to_thread=True)
def load(app_state: AppState, data: LoadData) -> LoadResponse:
    items = data.pure_data["items"]
    return load_persons(app_state, items)


@post("/load/{object_type:str}", sync_to_thread=True)
def load_raw(app_state: AppState, object_type: str, data: Any) -> LoadResponse:
    items = data["items"]
    return load_persons(app_state, items)


def load_persons(app_state: AppState, items: list[Any]) -> LoadResponse:
    with app_state.engine.connect() as conn:
        lf = app.load.pure.persons.transform_persons(items)
        loaded = 0
        for df in lf.collect_batches(chunk_size=100):
            loaded += len(df)
            app.load.pure.persons.load_persons(df, conn)
        return LoadResponse(number_loaded=loaded)


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str | None


class PersonsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    persons: list[PersonOut]


@get("/persons", sync_to_thread=True)
def persons(app_state: AppState) -> PersonsResponse:
    session = Session(app_state.engine)
    statement = select(Person)
    persons = session.scalars(statement).all()
    return PersonsResponse.model_validate({"persons": persons})


def run():
    config = Config.from_file("config.toml")
    engine = init_db(config)
    logging_config = LoggingConfig(
        root={"level": config.logging.level, "handlers": ["queue_listener"]},
        formatters={"standard": {"format": config.logging.format_str}},
        log_exceptions="always",
    )
    app = Litestar(
        route_handlers=[root, persons, load, load_raw],
        debug=True,
        dependencies={
            "app_state": Provide(
                lambda: AppState(config=config, engine=engine), sync_to_thread=True
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
