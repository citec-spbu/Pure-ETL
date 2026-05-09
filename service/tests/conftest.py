import pytest
from sqlalchemy.orm import Session

import app.config
import app.database


@pytest.fixture()
def session():
    config = app.config.Config.from_file("config.toml")
    engine = app.database.init_db(config)
    with engine.connect() as conn, Session(conn) as session:
        yield session
