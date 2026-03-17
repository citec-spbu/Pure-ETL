from app.config import Config
from app.models import Base
from sqlalchemy import Engine, create_engine


def init_db(config: Config) -> Engine:
    engine = create_engine(str(config.postgres.sqlalchemy_database_uri))
    Base.metadata.create_all(engine)
    return engine
