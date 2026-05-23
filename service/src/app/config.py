import tomllib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings


class LoggingConfig(BaseModel):
    level: Annotated[Literal["DEBUG", "INFO", "WARNING", "ERROR"], Field(default="INFO")]
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class PostgresConfig(BaseModel):
    host: str
    port: int = 5432
    user: str
    password: str = ""
    database_name: str = ""

    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            path=self.database_name,
        )


class Config(BaseSettings):
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    postgres: PostgresConfig

    @classmethod
    def from_file(cls, path: str) -> Config:
        """Load configuration from a specified TOML file."""
        config_path = Path(path).resolve()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open("rb") as f:
            data = tomllib.load(f)

        config = cls.model_validate(data)
        return config
