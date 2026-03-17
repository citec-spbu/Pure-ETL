from litestar.logging import LoggingConfig
import json
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.openapi import OpenAPIConfig
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.models import Person
import pprint
from sqlalchemy import Engine, select
from litestar.di import Provide
from app.database import init_db
from app.config import Config
import app.load.pure.persons
import uvicorn
from litestar import Litestar, get, post, Request


@get("/")
async def root(app_state: tuple[Config, Engine], request: Request) -> dict[str, str]:
    request.logger.info("This is logging")
    return {"config": pprint.pformat(app_state[0])}


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str | None


class PersonsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    persons: list[PersonOut]


@get("/persons")
async def persons(app_state: tuple[Config, Engine]) -> PersonsResponse:
    session = Session(app_state[1])
    statement = select(Person)
    persons = session.scalars(statement).all()
    return PersonsResponse.model_validate({"persons": persons})


@post("/load")
async def load(app_state: tuple[Config, Engine], data: dict[str, str]) -> None:
    conn = app_state[1].connect()
    lf = app.load.pure.persons.transform_persons(json.loads(data["persons"]))
    for df in lf.collect_batches(chunk_size=100):
        app.load.pure.persons.load_persons(df, conn)


def run():
    config = Config.from_file("config.toml")
    engine = init_db(config)
    logging_config = LoggingConfig(
        root={"level": config.logging.level, "handlers": ["queue_listener"]},
        formatters={"standard": {"format": config.logging.format_str}},
        log_exceptions="always",
    )
    app = Litestar(
        route_handlers=[root, persons, load],
        debug=True,
        dependencies={
            "app_state": Provide(lambda: (config, engine), sync_to_thread=True)
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
