import random
import uuid

from sqlalchemy import select

from app.models import Person


def test_db_connection(session):
    print("Created session")

    person = Person(
        id=uuid.uuid4(),
        pure_id=random.randint(0, 9999999999999),
        first_name="Test Person",
    )
    session.add(person)

    print("Created person")

    statement = select(Person).where(Person.id == person.id)
    person_selected = session.scalars(statement).one()

    session.delete(person_selected)

    print("Deleted person")

    assert session.execute(statement).first() is None
