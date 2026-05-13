import pytest
from sqlalchemy.orm import Session

import app.config
import app.database


@pytest.fixture(scope="session")
def engine():
    config = app.config.Config.from_file("config.toml")
    return app.database.init_db(config)


@pytest.fixture()
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
