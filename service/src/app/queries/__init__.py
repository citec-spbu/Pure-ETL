import datetime

import sqlalchemy
from sqlalchemy import CTE, func
from sqlalchemy.dialects.postgresql import Range

from app.models import (
    Person,
    PersonOrganisationalUnitStaffAssociation,
    PersonOrganisationalUnitStudentAssociation,
    ResearchOutput,
    ResearchOutputOrganisationalUnitAssociation,
    ResearchOutputPersonAssociation,
)

from . import examples as examples
from . import organisational_units as organisational_units
from . import research_outputs as research_outputs
from . import search as search


def select_persons_for_units(
    units: CTE,
    staff=True,
    student=False,
    outerjoin=False,
    rightjoin=False,
    date: None | datetime.datetime = None,
    period_overlaps: None | Range = None,
    period_contained: None | Range = None,
) -> sqlalchemy.Select:
    """
    Persons joined as staff or students with `units` cte.

    Params:
    - `staff` - whether to join as staff
    - `student` - whether to join as student
    - `outerjoin` - controls whether to perform left outer join from persons - returns persons without links
    - `rightjoin` - controls whether to perform right join instead
    - `date` - date that needs to be inside of the link period
    - `period_overlaps` - period that needs to overlap with the link period
    - `period_contained` - period that needs to be fully contained within the link period

    Columns expected in the provided cte:
    - `organisational_unit_id` - `uuid`

    Columns returned:
    - `person_id` - `uuid`
    - `period_start`
    - `period_end`
    - All from provided `units` cte
    """

    def query(is_staff: bool) -> sqlalchemy.Select:
        table = PersonOrganisationalUnitStaffAssociation if is_staff else PersonOrganisationalUnitStudentAssociation
        query = sqlalchemy.select(
            Person.id.label("person_id"),
            Person.first_name,
            Person.last_name,
            units,
            func.lower(table.period).label("period_start"),
            func.upper(table.period).label("period_end"),
        )

        return (
            query.select_from(units)
            .join(table, table.organisational_unit_id == units.c.organisational_unit_id, isouter=outerjoin)
            .join(
                Person,
                Person.id == table.person_id,
                isouter=outerjoin,
            )
            if rightjoin
            else query.select_from(Person)
            .join(table, Person.id == table.person_id, isouter=outerjoin)
            .join(
                units,
                units.c.organisational_unit_id == table.organisational_unit_id,
                isouter=outerjoin,
            )
        ).where(
            (table.period.contains(date) if date is not None else sqlalchemy.true())
            & (table.period.contains(period_contained) if period_contained is not None else sqlalchemy.true())
            & (table.period.overlaps(period_overlaps) if period_overlaps is not None else sqlalchemy.true())
        )

    if staff and student:
        return sqlalchemy.select(query(True).union_all(query(False)).cte())
    elif staff:
        return query(True)
    elif student:
        return query(False)
    else:
        raise Exception("Cannot select no associations")


def select_persons_named_for_units(
    units: None | CTE = None,
    staff=True,
    outerjoin=False,
    date: None | datetime.datetime = None,
    period_overlaps: None | Range = None,
    period_contained: None | Range = None,
) -> sqlalchemy.Select:
    """
    Persons joined as staff or students with `select_units_with_all_children_named` as cte.

    Exists just for backwards compatibility, use `select_persons_for_units`

    Params:
    - `staff` - controls whether to join as staff or as students
    - `outerjoin` - controls whether to perform left outer join from persons - returns persons without links
    - `date` - date that needs to be inside of the link period
    - `period_overlaps` - period that needs to overlap with the link period
    - `period_contained` - period that needs to be fully contained within the link period

    Columns expected in the provided cte:
    - `organisational_unit_id` - `uuid`

    Columns returned:
    - `person_id` - `uuid`
    - `first_name` - `text`
    - `last_name` - `text`
    - `period_start`
    - `period_end`
    - All from provided `units` cte
    """

    if units is None:
        units = organisational_units.select_units_with_all_children_named().cte()

    joined = select_persons_for_units(
        units,
        staff=staff,
        student=not staff,
        outerjoin=outerjoin,
        date=date,
        period_contained=period_contained,
        period_overlaps=period_overlaps,
    ).cte()

    query = (
        sqlalchemy.select(
            joined,
            Person.first_name,
            Person.last_name,
        )
        .select_from(joined)
        .outerjoin(Person, Person.id == joined.c.person_id)
    )

    return query


def select_research_outputs_for_units(
    units: None | CTE = None,
    outerjoin: bool = False,
    rightjoin: bool = False,
    research_outputs: CTE | None = None,
) -> sqlalchemy.Select:
    """
    Research outputs joined with `select_units_with_all_children_named` as cte.

    Params:
    - `outerjoin` - controls whether to perform left outer join from research
      outputs - returns research ouputs without links
    - `right` - whether to do right join instead

    Columns expected in the provided cte:
    - `organisational_unit_id` - `uuid`

    Columns expected in the `research_outputs` cte if provided:
    - `research_output_id` - `uuid`

    Columns returned:
    - `research_output_id` - `uuid`
    - `research_output_title` - `text`
    - `research_output_pure_id` - integer
    - `research_output_type_id` - integer
    - `research_output_language_type_id` - integer
    - `research_output_category_type_id` - integer
    - All from the provided `units` cte
    """

    if units is None:
        units = organisational_units.select_units_with_all_children_named(
            units=organisational_units.select_units_with_all_children_filter(
                filter_units_by_id=[organisational_units.spbu]
            ).cte()
        ).cte()

    research_outputs_unfiltered = sqlalchemy.select(
        ResearchOutput.id.label("research_output_id"),
        ResearchOutput.title.label("research_output_title"),
        ResearchOutput.pure_id.label("research_output_pure_id"),
        ResearchOutput.type_id.label("research_output_type_id"),
        ResearchOutput.category_type_id.label("research_output_category_type_id"),
        ResearchOutput.language_type_id.label("research_output_language_type_id"),
    ).select_from(ResearchOutput)

    filtered_research_outputs = (
        research_outputs_unfiltered.cte()
        if research_outputs is None
        else research_outputs_unfiltered.join(
            research_outputs, ResearchOutput.id == research_outputs.c.research_output_id
        ).cte()
    )

    select = sqlalchemy.select(
        filtered_research_outputs,
        units,
    )
    return (
        select.select_from(units)
        .join(
            ResearchOutputOrganisationalUnitAssociation,
            units.c.organisational_unit_id == ResearchOutputOrganisationalUnitAssociation.organisational_unit_id,
            isouter=outerjoin,
        )
        .join(
            filtered_research_outputs,
            filtered_research_outputs.c.research_output_id
            == ResearchOutputOrganisationalUnitAssociation.research_output_id,
            isouter=outerjoin,
        )
        if rightjoin
        else select.select_from(filtered_research_outputs)
        .join(
            ResearchOutputOrganisationalUnitAssociation,
            filtered_research_outputs.c.research_output_id
            == ResearchOutputOrganisationalUnitAssociation.research_output_id,
            isouter=outerjoin,
        )
        .join(
            units,
            units.c.organisational_unit_id == ResearchOutputOrganisationalUnitAssociation.organisational_unit_id,
            isouter=outerjoin,
        )
    )


def select_persons_with_research_outputs() -> sqlalchemy.Select:
    """
    Exists for compatibility reasons, use `select_research_outputs_for_persons`.

    Columns returned:
    - `person_id` - `uuid`
    - `first_name` - `text`
    - `last_name` - `text`
    - `person_role_type_id` - integer
    - `research_output_id` - `uuid`
    - `title` - `text`
    - `pure_id` - integer
    - `type_id` - integer
    - `language_type_id` - integer
    - `category_type_id` - integer
    """

    return (
        sqlalchemy.select(
            Person.id.label("person_id"),
            Person.first_name,
            Person.last_name,
            ResearchOutputPersonAssociation.person_role_type_id,
            ResearchOutput.id.label("research_output_id"),
            ResearchOutput.title,
            ResearchOutput.pure_id,
            ResearchOutput.type_id,
            ResearchOutput.category_type_id,
            ResearchOutput.language_type_id,
        )
        .select_from(ResearchOutput)
        .join(ResearchOutput.person_associations)
        .join(ResearchOutputPersonAssociation.person)
    )


def select_research_outputs_for_persons(
    persons: CTE,
    outerjoin: bool = False,
    rightjoin: bool = False,
    research_outputs: CTE | None = None,
) -> sqlalchemy.Select:
    """
    Research outputs joined with `persons` cte.

    Params:
    - `outerjoin` - controls whether to perform left outer join from research
      outputs - returns research ouputs without links
    - `right` - whether to do right join instead

    Columns expected in the provided cte:
    - `person_id` - `uuid`

    Columns expected in the `research_outputs` cte if provided:
    - `research_output_id` - `uuid`

    Columns returned:
    - `research_output_id` - `uuid`
    - `research_output_title` - `text`
    - `research_output_pure_id` - integer
    - `research_output_type_id` - integer
    - `research_output_language_type_id` - integer
    - `research_output_category_type_id` - integer
    - All from the provided `persons` cte
    """

    research_outputs_unfiltered = sqlalchemy.select(
        ResearchOutput.id.label("research_output_id"),
        ResearchOutput.title.label("research_output_title"),
        ResearchOutput.pure_id.label("research_output_pure_id"),
        ResearchOutput.type_id.label("research_output_type_id"),
        ResearchOutput.category_type_id.label("research_output_category_type_id"),
        ResearchOutput.language_type_id.label("research_output_language_type_id"),
    ).select_from(ResearchOutput)

    filtered_research_outputs = (
        research_outputs_unfiltered.cte()
        if research_outputs is None
        else research_outputs_unfiltered.join(
            research_outputs, ResearchOutput.id == research_outputs.c.research_output_id
        ).cte()
    )

    query = sqlalchemy.select(
        filtered_research_outputs,
        persons,
    )
    return (
        query.select_from(persons)
        .join(
            ResearchOutputPersonAssociation,
            persons.c.person_id == ResearchOutputPersonAssociation.person_id,
            isouter=outerjoin,
        )
        .join(
            filtered_research_outputs,
            filtered_research_outputs.c.research_output_id == ResearchOutputPersonAssociation.research_output_id,
            isouter=outerjoin,
        )
        if rightjoin
        else query.select_from(filtered_research_outputs)
        .join(
            ResearchOutputPersonAssociation,
            filtered_research_outputs.c.research_output_id == ResearchOutputPersonAssociation.research_output_id,
            isouter=outerjoin,
        )
        .join(
            persons,
            persons.c.person_id == ResearchOutputPersonAssociation.person_id,
            isouter=outerjoin,
        )
    )
