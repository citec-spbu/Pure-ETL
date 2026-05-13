import argparse
import datetime
import logging
import random
import uuid
from uuid import UUID

import sqlalchemy
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.orm import Session

from app import queries
from app.config import Config
from app.database import init_db
from app.models import (
    Classification,
    OrganisationalUnit,
    Person,
    PersonOrganisationalUnitStaffAssociation,
    PersonOrganisationalUnitStudentAssociation,
    ResearchOutput,
    ResearchOutputOrganisationalUnitAssociation,
    ResearchOutputPersonAssociation,
)


class DryRun(Exception):
    pass


_generated_pure_ids: set[int] = set()


def random_pure_id() -> int:
    while True:
        value = random.randint(100_000_000_000, 999_999_999_999)
        if value not in _generated_pure_ids:
            _generated_pure_ids.add(value)
            return value


def generate_fake_orcid():
    groups = ["".join(str(random.randint(0, 9)) for _ in range(4)) for _ in range(4)]
    if random.random() > 0.9:
        groups[3] = groups[3][:3] + "X"
    return "-".join(groups)


def unit_id_groups() -> dict[str, sqlalchemy.CTE]:
    units_ord = queries.select_units_with_all_children(
        filter_units_by_id=[UUID("65666392-9044-41de-aebd-3f58d14f5679")]
    ).cte()
    units_ord_ids = sqlalchemy.select(units_ord.c.organisational_unit_id).select_from(units_ord)

    units_asp = queries.select_units_with_all_children(
        filter_units_by_id=[UUID("48d3663f-c069-4000-bb53-efeec4d313b2")]
    ).cte()
    units_asp_ids = sqlalchemy.select(units_asp.c.organisational_unit_id).select_from(units_asp)

    units_all_tree = queries.select_units_with_all_children(filter_units_by_id=[queries.spbu]).cte()
    units_other_ids = (
        sqlalchemy.select(units_all_tree.c.organisational_unit_id)
        .select_from(units_all_tree)
        .except_all(units_ord_ids, units_asp_ids)
    )

    return dict(
        ord=units_ord_ids.cte(),
        asp=units_asp_ids.cte(),
        other=units_other_ids.cte(),
    )


def generate_more_units(
    session: Session,
    generate_amount: list[int],
    level_types: list[int],
    select_unit_ids_cte: sqlalchemy.CTE,
    verbose: bool,
):
    select_unit_ids_for_level = [
        sqlalchemy.select(select_unit_ids_cte.c.organisational_unit_id)
        .select_from(select_unit_ids_cte)
        .join(OrganisationalUnit, OrganisationalUnit.id == select_unit_ids_cte.c.organisational_unit_id)
        .where(OrganisationalUnit.type_id == level_type_id)
        for level_type_id in level_types
    ]

    initial_unit_ids_by_level = [list(session.scalars(statement).all()) for statement in select_unit_ids_for_level]

    for level, initial_unit_ids in enumerate(initial_unit_ids_by_level):
        logging.info(f"Working with {len(initial_unit_ids)} initial organisational units for level {level}")

    unit_ids_by_level = [
        [unit_id for unit_id in initial_unit_ids_by_level[0]],
        [unit_id for unit_id in initial_unit_ids_by_level[1]],
        [unit_id for unit_id in initial_unit_ids_by_level[2]],
        [unit_id for unit_id in initial_unit_ids_by_level[3]],
    ]

    def into_units(ids: sqlalchemy.CTE) -> sqlalchemy.Select[tuple[OrganisationalUnit]]:
        return (
            sqlalchemy.select(OrganisationalUnit)
            .select_from(OrganisationalUnit)
            .join(ids, OrganisationalUnit.id == ids.c.organisational_unit_id)
        )

    def into_word_pools(select_units: sqlalchemy.Select[tuple[OrganisationalUnit]]) -> tuple[list[str], list[str]]:
        units = session.scalars(select_units).all()

        word_pool_ru: list[str] = []
        word_pool_en: list[str] = []

        for unit in units:
            if unit.name_ru:
                word_pool_ru.extend(unit.name_ru.replace('"', "").replace("(", "").replace(")", "").split())
            if unit.name_en:
                word_pool_en.extend(unit.name_en.replace('"', "").replace("(", "").replace(")", "").split())

        return word_pool_ru, word_pool_en

    word_pools_by_level = [into_word_pools(into_units(statement.cte())) for statement in select_unit_ids_for_level]

    ids_pool = [unit.ids for unit in session.scalars(into_units(select_unit_ids_cte))]

    if not ids_pool:
        raise Exception("Not enough data")

    for level, generate_units in enumerate(generate_amount):
        logging.info(f"Will generate {generate_units} organisational units for level {level}")

    for level, generate_units in enumerate(generate_amount):
        if level == 0 or generate_units == 0:
            logging.debug(f"Skipping level {level}")
            continue

        logging.info(f"Generating {generate_units} units for level {level}")

        if len(unit_ids_by_level[level - 1]) == 0:
            raise Exception("Expected > 0 units in previous level")

        word_pool_ru, word_pool_en = word_pools_by_level[level]

        if not word_pool_ru or not word_pool_en:
            raise Exception("Not enough data")

        for i in range(generate_units):
            logging.debug(f"Generating unit {i + 1}/{generate_units} in level {level}")
            unit = OrganisationalUnit(
                id=uuid.uuid4(),
                pure_id=random_pure_id(),
                type_id=level_types[level],
                name_ru=" ".join(random.choices(word_pool_ru, k=random.randint(2, 8))),
                name_en=" ".join(random.choices(word_pool_en, k=random.randint(2, 8))),
                parents=[str(random.choice(unit_ids_by_level[level - 1]))],
                ids=random.choice(ids_pool),
            )
            if verbose:
                logging.debug(
                    "Generated\n"
                    f"  id={unit.id}\n"
                    f"  pure_id={unit.pure_id}\n"
                    f"  type_id={unit.type_id}\n"
                    f"  name_ru={unit.name_ru}\n"
                    f"  name_en={unit.name_en}\n"
                    f"  parents={unit.parents}\n"
                    f"  ids={unit.ids}\n"
                    f"  raw={unit.raw}"
                )
            unit_ids_by_level[level].append(unit.id)
            session.add(unit)


def generate_units(session: Session, amount: int, verbose: bool):
    """
    Actual amount will be a bit larger but close enough
    """

    level_types = [
        17276,
        17278,
        17281,
        17284,
    ]

    initial_units_all = session.scalars(sqlalchemy.select(OrganisationalUnit.id)).all()
    logging.info(f"Working with {len(initial_units_all)} initial organisational units")

    unit_ids = unit_id_groups()

    amount = amount // 5

    generate_amount = [0, 0, amount // 10, amount * 2]

    logging.info("Generating ORD")
    generate_more_units(session, generate_amount, level_types, unit_ids["ord"], verbose)
    logging.info("Generating ASP")
    generate_more_units(session, generate_amount, level_types, unit_ids["asp"], verbose)

    generate_amount = [0, amount // 100, amount // 10, amount]

    logging.info("Generating NORMAL")
    generate_more_units(session, generate_amount, level_types, unit_ids["other"], verbose)


def generate_persons(session: Session, amount: int, verbose: bool):
    initial_persons_all = session.scalars(sqlalchemy.select(Person)).all()
    logging.info(f"Working with {len(initial_persons_all)} initial persons")

    unit_ids = unit_id_groups()

    unit_ids_ord = unit_ids["ord"]
    unit_ids_asp = unit_ids["asp"]
    unit_ids_other = unit_ids["other"]

    unit_ids_ord = list(
        session.scalars(
            sqlalchemy.select(unit_ids_ord.c.organisational_unit_id)
            .select_from(unit_ids_ord)
            .where(unit_ids_ord.c.organisational_unit_id != UUID("65666392-9044-41de-aebd-3f58d14f5679"))
        ).all()
    )
    unit_ids_asp = list(
        session.scalars(
            sqlalchemy.select(unit_ids_asp.c.organisational_unit_id)
            .select_from(unit_ids_asp)
            .where(unit_ids_asp.c.organisational_unit_id != UUID("48d3663f-c069-4000-bb53-efeec4d313b2"))
        ).all()
    )

    unit_ids_student = unit_ids_ord + unit_ids_asp
    unit_ids_staff = list(
        session.scalars(
            sqlalchemy.select(unit_ids_other.c.organisational_unit_id)
            .select_from(unit_ids_other)
            .where(unit_ids_other.c.organisational_unit_id != queries.spbu)
        ).all()
    )

    logging.info(f"Working with {len(unit_ids_student)} possible units for students")
    logging.info(f"Working with {len(unit_ids_staff)} possible units for staff")

    first_name_1_pool: list[str] = []
    first_name_2_pool: list[str] = []
    last_name_pool: list[str] = []

    ids_pool = []
    titles_pool = []

    for person in initial_persons_all:
        if person.first_name:
            names = person.first_name.split()
            first_name_1_pool.extend(names[:1])
            first_name_2_pool.extend(names[1:])
        if person.last_name:
            last_name_pool.append(person.last_name)
        ids_pool.append(person.ids)
        titles_pool.append(person.titles)

    if not ids_pool or not titles_pool or not first_name_1_pool or not first_name_2_pool or not last_name_pool:
        raise Exception("Not enough data")

    logging.info(f"Now generating {amount} persons")
    for i in range(amount):
        logging.debug(f"Generating person {i + 1}/{amount}")
        person = Person(
            id=uuid.uuid4(),
            pure_id=random_pure_id(),
            first_name=f"{random.choice(first_name_1_pool)} {random.choice(first_name_2_pool)}",
            last_name=random.choice(last_name_pool),
            titles=random.choice(titles_pool),
            ids=random.choice(ids_pool),
            orcid=generate_fake_orcid() if random.random() < 0.2 else None,
        )
        period_start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=random.randint(10, 2000))
        period_end = None if random.random() < 0.2 else period_start + datetime.timedelta(days=random.randint(10, 2000))
        period = Range(period_start, period_end)
        if random.random() < 0.8:
            person.student_organisation_associations.append(
                PersonOrganisationalUnitStudentAssociation(
                    person_id=person.id,
                    organisational_unit_id=random.choice(unit_ids_student),
                    period=period,
                )
            )
        else:
            person.staff_organisation_associations.append(
                PersonOrganisationalUnitStaffAssociation(
                    person_id=person.id,
                    organisational_unit_id=random.choice(unit_ids_staff),
                    period=period,
                )
            )
        staff_associations = [
            association.organisational_unit_id for association in person.staff_organisation_associations
        ]
        student_associations = [
            association.organisational_unit_id for association in person.student_organisation_associations
        ]
        if verbose:
            logging.debug(
                "Generated\n"
                f"  id={person.id}\n"
                f"  pure_id={person.pure_id}\n"
                f"  first_name={person.first_name}\n"
                f"  last_name={person.last_name}\n"
                f"  titles={person.titles}\n"
                f"  ids={person.ids}\n"
                f"  orcid={person.orcid}\n"
                f"  raw={person.raw}\n"
                f"  staff_organisation_associations={staff_associations}\n"
                f"  student_organisation_associations={student_associations}\n"
                f"  period={period}"
            )
        session.add(person)

    pass


def generate_research_outputs(session: Session, amount: int, verbose: bool):
    initial_research_outputs_all = session.scalars(sqlalchemy.select(ResearchOutput)).all()
    logging.info(f"Working with {len(initial_research_outputs_all)} initial research outputs")

    research_output_type_classification_scheme_id = UUID("aa4a3e1a-c2d2-4d8c-b839-00f6a3b4df4f")
    _language_type_classification_scheme_id = UUID("3a08c244-09de-4302-870b-0764ae00d168")
    _category_type_classification_scheme_id = UUID("f1ce2bfe-779c-48b6-8e0e-6f079056cdb3")

    research_output_types = list(
        session.scalars(
            sqlalchemy.select(Classification.pure_id).where(
                Classification.classification_scheme_id == research_output_type_classification_scheme_id
            )
        ).all()
    )
    favorite_research_output_types = [
        4082,  # Review
        3973,  # Article
        4029,  # Conference contribution
    ]
    language_types = [
        17022,  # English US
        209,  # Undefined
        201,  # Russian
    ]
    category_types = [
        3937,  # Research
        3943,  # Other
    ]
    logging.info(f"Working with the the following favorited research output types: {favorite_research_output_types}")
    logging.info(f"Working with the the following research output types: {research_output_types}")
    logging.info(f"Working with the the following language types: {language_types}")
    logging.info(f"Working with the the following category types: {category_types}")

    title_pool: list[str] = []

    for research_output in initial_research_outputs_all:
        if research_output.title:
            title_pool.extend(research_output.title.split())

    if not title_pool:
        raise Exception("Not enough data")

    all_staff_person_associations = session.scalars(
        sqlalchemy.select(
            PersonOrganisationalUnitStaffAssociation,
        ).select_from(PersonOrganisationalUnitStaffAssociation)
    ).all()

    persons_units: dict[UUID, list[UUID]] = {}
    for association in all_staff_person_associations:
        if association.person_id not in persons_units:
            persons_units[association.person_id] = []
        persons_units[association.person_id].append(association.organisational_unit_id)

    all_staff_person_ids = list(persons_units.keys())

    if not all_staff_person_ids:
        raise Exception("Not enough data")

    logging.info(f"Working with {len(all_staff_person_ids)} staff")

    logging.info(f"Now generating {amount} research outputs")
    for i in range(amount):
        logging.debug(f"Generating research_output {i + 1}/{amount}")
        research_output = ResearchOutput(
            id=uuid.uuid4(),
            pure_id=random_pure_id(),
            type_id=random.choice(favorite_research_output_types)
            if random.random() < 0.8
            else random.choice(research_output_types),
            category_type_id=random.choice(category_types),
            language_type_id=random.choice(language_types),
            title=" ".join(random.choices(title_pool, k=random.randint(5, 15))).capitalize(),
        )
        number_of_authors = random.choices(
            [1, 2, 3, 4, 5],
            [36, 16, 8, 4, 2],  # Distribution counted from sciscinet dataset
            k=1,
        )[0]
        authors = random.sample(all_staff_person_ids, min(number_of_authors, len(all_staff_person_ids)))
        units = set(unit_id for author in authors for unit_id in persons_units[author])
        for author in authors:
            research_output.person_associations.append(
                ResearchOutputPersonAssociation(
                    research_output_id=research_output.id,
                    person_id=author,
                    pure_id=random_pure_id(),
                )
            )
        for unit_id in units:
            research_output.organisational_unit_associations.append(
                ResearchOutputOrganisationalUnitAssociation(
                    research_output_id=research_output.id,
                    organisational_unit_id=unit_id,
                )
            )
        person_associations = [association.person_id for association in research_output.person_associations]
        organisational_unit_associations = [
            association.organisational_unit_id for association in research_output.organisational_unit_associations
        ]
        if verbose:
            logging.debug(
                "Generated\n"
                f"  id={research_output.id}\n"
                f"  pure_id={research_output.pure_id}\n"
                f"  type_id={research_output.type_id}\n"
                f"  category_type_id={research_output.category_type_id}\n"
                f"  language_type_id={research_output.language_type_id}\n"
                f"  title={research_output.title}\n"
                f"  raw={research_output.raw}\n"
                f"  person_associations={person_associations}\n"
                f"  organisational_unit_associations={organisational_unit_associations}\n"
            )
        session.add(research_output)


def generate(units: int, persons: int, research_outputs: int, dry: bool, verbose: bool):
    config = Config.from_file("config.toml")
    logging.basicConfig(format=config.logging.format_str, level=config.logging.level)
    if dry:
        logging.info("Dry run")
    else:
        logging.info("Will commit changes")
    engine = init_db(config)
    with engine.connect() as conn, Session(conn) as session, session.begin():
        if units > 0:
            generate_units(session, units, verbose)
        else:
            logging.info("Skipping organisational units")
        if persons > 0:
            generate_persons(session, persons, verbose)
        else:
            logging.info("Skipping persons")
        if research_outputs > 0:
            generate_research_outputs(session, research_outputs, verbose)
        else:
            logging.info("Skipping research outputs")
        if dry:
            logging.info("Successfully generated all objects, now rolling back")
            raise DryRun("Dry run")
        else:
            logging.info("Successfully generated all objects, now committing")


def main():
    parser = argparse.ArgumentParser(
        description="Generate persons, units, and outputs from already existing records in the database."
    )
    parser.add_argument("organisational_units", type=int, help="Number of organisational units to generate")
    parser.add_argument("persons", type=int, help="Number of persons to generate")
    parser.add_argument("research_outputs", type=int, help="Number or research outputs to generate")
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Don't commit changes",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print generated items",
    )
    args = parser.parse_args()
    try:
        generate(
            units=args.organisational_units,
            persons=args.persons,
            research_outputs=args.research_outputs,
            dry=args.dry,
            verbose=args.verbose,
        )
    except DryRun:
        print("Rolled back")


if __name__ == "__main__":
    main()
