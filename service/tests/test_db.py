import uuid
import app.database
from app.models import Person
import app.config
from sqlalchemy.orm import Session
from sqlalchemy import select


def test_db_connection():
    config = app.config.Config.from_file("config.toml")
    engine = app.database.init_db(config)
    conn = engine.connect()
    session = Session(conn)

    print("Created session")

    person = Person(id=uuid.uuid4(), name="Test Person")
    session.add(person)
    session.commit()

    print("Created person")

    statement = select(Person).where(Person.id == person.id)
    person_selected = session.scalars(statement).one()

    session.delete(person_selected)
    session.commit()

    print("Deleted person")

    assert session.execute(statement).first() is None
