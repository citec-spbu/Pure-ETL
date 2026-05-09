from sqlalchemy import Engine

from app.config import Config


class AppState:
    """Immutable application state"""

    config: Config
    engine: Engine

    def __init__(self, config: Config, engine: Engine) -> None:
        self.config = config
        self.engine = engine
