import uuid
from app.models import Person
from sqlalchemy import Connection
from sqlalchemy.orm import Session
import polars as pl


def transform_persons(persons: list) -> pl.LazyFrame:
    """Transforms persons dictionary to a format ready to be loaded to the database"""
    lf = pl.LazyFrame(persons).select(
        pl.col("uuid").alias("person_id"),
        pl.col("name").map_elements(
            lambda s: f"{s["firstName"]} {s["lastName"]}", return_dtype=pl.String
        ),
    )
    return lf


def load_persons(df: pl.DataFrame, conn: Connection):
    """
    Loads persons from prepared dataframe into the database
    See `transform_persons`
    """
    with Session(conn) as session:
        for person in df.rows(named=True):
            person = Person(id=uuid.UUID(person["person_id"]), name=person["name"])
            session.merge(person)
        session.commit()
