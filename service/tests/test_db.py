import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.config
import app.database
from app.models import Person


def test_db_connection():
    config = app.config.Config.from_file("config.toml")
    engine = app.database.init_db(config)
    with engine.connect() as conn:
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
