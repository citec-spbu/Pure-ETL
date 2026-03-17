import json
import uuid
import app.database
from app.models import Person
import app.config
import app.load.pure.persons
from sqlalchemy.orm import Session
from sqlalchemy import select


def test_persons_load():
    """Loads one person and then deletes it"""

    config = app.config.Config.from_file("config.toml")
    engine = app.database.init_db(config)
    conn = engine.connect()
    session = Session(conn)

    print("Created session")

    with open("data/persons.json") as f:
        persons = json.load(f)["items"]

    print("Read json")

    person = persons[0]
    persons = [person]

    statement = select(Person).where(Person.id == person["uuid"])
    assert session.execute(statement).first() is None

    lf = app.load.pure.persons.transform_persons(persons)
    df = lf.collect_batches(chunk_size=1)

    print("Created persons iterator")

    for df in df:
        app.load.pure.persons.load_persons(df, conn)

    print("Loaded persons to the database")

    person_selected = session.scalars(statement).one()

    session.delete(person_selected)
    session.commit()

    print("Deleted person")

    assert session.execute(statement).first() is None
