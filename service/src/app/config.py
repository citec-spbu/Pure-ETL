import tomllib
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="_",
        extra="forbid",
    )

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
