import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    OrganisationalUnit,
    Person,
    PersonOrganisationalUnitStaffAssociation,
    PersonOrganisationalUnitStudentAssociation,
)


def test_organisational_units_relation(session: Session):
    units = [
        OrganisationalUnit(id=uuid.uuid4(), pure_id=random.randint(0, 9999999999999)),
        OrganisationalUnit(id=uuid.uuid4(), pure_id=random.randint(0, 9999999999999)),
        OrganisationalUnit(id=uuid.uuid4(), pure_id=random.randint(0, 9999999999999)),
    ]
    session.add_all(units)

    person_id = uuid.uuid4()

    staff_associations = [
        PersonOrganisationalUnitStaffAssociation(
            person_id=person_id, organisational_unit=units[0]
        ),
        PersonOrganisationalUnitStaffAssociation(
            person_id=person_id, organisational_unit=units[1]
        ),
    ]

    student_associations = [
        PersonOrganisationalUnitStudentAssociation(
            person_id=person_id, organisational_unit=units[1]
        ),
        PersonOrganisationalUnitStudentAssociation(
            person_id=person_id, organisational_unit=units[2]
        ),
    ]

    person = Person(
        id=person_id,
        pure_id=random.randint(0, 9999999999999),
        first_name="Test Person",
        staff_organisation_associations=staff_associations,
        student_organisation_associations=student_associations,
    )
    session.add(person)

    print("Created person")

    statement = select(Person).where(Person.id == person.id)
    person_selected = session.scalars(statement).one()

    select_units_statement = select(OrganisationalUnit).where(
        OrganisationalUnit.id.in_([unit.id for unit in units])
    )

    units_selected = session.scalars(select_units_statement).all()
    assert len(units_selected) == 3

    # sqlalchemy would not override links on its own so we have to
    # modify the person from session

    person_selected.staff_organisation_associations.clear()
    person_selected.student_organisation_associations.clear()

    person_selected.staff_organisation_associations.extend([staff_associations[0]])

    session.merge(person_selected)

    units_selected = session.scalars(select_units_statement).all()
    assert len(units_selected) == 3

    person_selected = session.scalars(statement).one()

    assert len(person_selected.staff_organisation_associations) == 1
    assert len(person_selected.student_organisation_associations) == 0

    session.delete(person_selected)

    print("Deleted person")

    assert session.execute(statement).first() is None

    units_selected = session.scalars(select_units_statement).all()
    assert len(units_selected) == 3
