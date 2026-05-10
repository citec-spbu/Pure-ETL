import json

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.config
import app.database
import app.load.pure.classification_schemes
import app.load.pure.organisational_units
import app.load.pure.persons
import app.load.pure.research_outputs
from app.models import (
    Classification,
    ClassificationScheme,
    OrganisationalUnit,
    Person,
    ResearchOutput,
)


def test_persons_load(session: Session):
    """Loads one person and then deletes it"""

    print("Created session")

    with open("tests/data/persons.json") as f:
        persons = json.load(f)["items"]

    print("Read json")

    person = persons[0]
    persons = [person]

    statement = select(Person).where(Person.id == person["uuid"])
    assert session.execute(statement).first() is None, "person does not exist yet"

    lf = app.load.pure.persons.transform(persons)
    df_iter = lf.collect_batches(chunk_size=2)

    print("Created persons iterator")

    executed = False

    for df in df_iter:
        assert len(df) == 1, "There is one person in the dataframe"
        executed = True
        app.load.pure.persons.load(df, session)

    assert executed, "load was executed"

    print("Loaded persons to the database")

    assert session.execute(statement).first() is not None, "person was loaded"

    person_selected = session.scalars(statement).one()

    session.delete(person_selected)

    print("Deleted person")

    assert session.execute(statement).first() is None, "person was deleted"


def test_persons_reload(session: Session):
    """Loads one person and then loads it again"""

    print("Created session")

    with open("tests/data/persons.json") as f:
        persons = json.load(f)["items"]

    print("Read json")

    person = persons[0]
    persons = [person]

    statement = select(Person).where(Person.id == person["uuid"])
    assert session.execute(statement).first() is None, "person does not exist yet"

    lf = app.load.pure.persons.transform(persons)
    df_iter = lf.collect_batches(chunk_size=2)

    print("Created persons iterator")

    executed = False

    for df in df_iter:
        assert len(df) == 1, "There is one person in the dataframe"
        executed = True
        app.load.pure.persons.load(df, session)

    assert executed, "load was executed"

    print("Loaded persons to the database")

    assert session.execute(statement).first() is not None, "person was loaded"

    person_selected = session.scalars(statement).one()

    persons = [person_selected.raw]

    lf = app.load.pure.persons.transform(persons)
    df_iter = lf.collect_batches(chunk_size=2)

    print("Created persons iterator again")

    executed = False

    for df in df_iter:
        assert len(df) == 1, "There is one person in the dataframe"
        executed = True
        app.load.pure.persons.load(df, session)

    assert executed, "load was executed again"

    print("Loaded persons to the database again")

    person_selected = session.scalars(statement).one()

    session.delete(person_selected)

    print("Deleted person")

    assert session.execute(statement).first() is None, "person was deleted"


def test_research_outputs_load(session):
    """Loads one research output and then deletes it"""

    print("Created session")

    with open("tests/data/research-outputs.json") as f:
        research_outputs = json.load(f)["items"]

    print("Read json")

    research_output = research_outputs[0]
    research_outputs = [research_output]

    statement = select(ResearchOutput).where(ResearchOutput.id == research_output["uuid"])
    assert session.execute(statement).first() is None

    lf = app.load.pure.research_outputs.transform(research_outputs)
    df_iter = lf.collect_batches(chunk_size=1)

    print("Created research outputs iterator")

    for df in df_iter:
        app.load.pure.research_outputs.load(df, session)

    print("Loaded research_outputs to the database")

    research_outputs_selected = session.scalars(statement).one()

    session.delete(research_outputs_selected)

    print("Deleted research output")

    assert session.execute(statement).first() is None


def test_organisational_units_load(session):
    """Loads one organisational unit and then deletes it"""

    print("Created session")

    with open("tests/data/organisational-units.json") as f:
        organisational_units = json.load(f)["items"]

    print("Read json")

    organisational_unit = organisational_units[0]
    organisational_units = [organisational_unit]

    statement = select(OrganisationalUnit).where(OrganisationalUnit.id == organisational_unit["uuid"])
    assert session.execute(statement).first() is None

    lf = app.load.pure.organisational_units.transform(organisational_units)
    df_iter = lf.collect_batches(chunk_size=1)

    print("Created organisational units iterator")

    for df in df_iter:
        app.load.pure.organisational_units.load(df, session)

    print("Loaded organisational units to the database")

    organisational_units_selected = session.scalars(statement).one()

    session.delete(organisational_units_selected)

    print("Deleted organisational unit")

    assert session.execute(statement).first() is None


def test_classification_schemes_load(session: Session):
    """Loads one classification scheme and then deletes it"""

    print("Created session")

    with open("tests/data/classification-schemes.json") as f:
        classification_schemes = json.load(f)["items"]

    print("Read json")

    classification_scheme = classification_schemes[0]
    classification_schemes = [classification_scheme]

    statement = select(ClassificationScheme).where(ClassificationScheme.id == classification_scheme["uuid"])
    assert session.execute(statement).first() is None

    lf = app.load.pure.classification_schemes.transform(classification_schemes)
    df_iter = lf.collect_batches(chunk_size=1)

    print("Created classification schemes iterator")

    for df in df_iter:
        app.load.pure.classification_schemes.load(df, session)

    print("Loaded classification schemes to the database")

    classification_schemes_selected = session.scalars(statement).one()

    select_classifications = select(Classification).where(
        Classification.classification_scheme_id == classification_schemes_selected.id
    )

    classifications = session.execute(select_classifications).all()
    assert len(classifications) == 5

    session.delete(classification_schemes_selected)

    print("Deleted classification scheme")

    assert session.execute(statement).first() is None

    classifications = session.execute(select_classifications).all()
    assert len(classifications) == 0
