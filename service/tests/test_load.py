import json

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.config
import app.database
import app.load.pure.persons
from app.models import Person


def test_persons_load():
    """Loads one person and then deletes it"""

    config = app.config.Config.from_file("config.toml")
    engine = app.database.init_db(config)
    conn = engine.connect()
    session = Session(conn)

    print("Created session")

    with open("tests/data/persons.json") as f:
        persons = json.load(f)["items"]

    print("Read json")

    person = persons[0]
    persons = [person]

    statement = select(Person).where(Person.id == person["uuid"])
    assert session.execute(statement).first() is None

    lf = app.load.pure.persons.transform_persons(persons)
    df_iter = lf.collect_batches(chunk_size=1)

    print("Created persons iterator")

    for df_iter in df_iter:
        app.load.pure.persons.load_persons(df_iter, conn)

    print("Loaded persons to the database")

    person_selected = session.scalars(statement).one()

    session.delete(person_selected)
    session.commit()

    print("Deleted person")

    assert session.execute(statement).first() is None
