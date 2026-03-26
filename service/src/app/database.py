from sqlalchemy import Engine, create_engine

from app.config import Config


def init_db(config: Config) -> Engine:
    engine = create_engine(str(config.postgres.sqlalchemy_database_uri))
    return engine
