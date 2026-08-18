from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]

DEFAULT_INPUT_FILE = (
    REPOSITORY_ROOT / "Data" / "research-outputs.json"
)

DEFAULT_OUTPUT_FILE = (
    EXPERIMENT_DIR
    / "output"
    / "researcher_publications.csv"
)

DEFAULT_REPORT_FILE = (
    EXPERIMENT_DIR
    / "reports"
    / "researcher_publications_summary.md"
)

PREFERRED_LOCALES = (
    "ru_RU",
    "en_US",
)


def parse_arguments() -> argparse.Namespace:
    """Прочитать параметры кс"""

    parser = argparse.ArgumentParser(
        description=(
            "Построить таблицу связей внутренних исследователей "
            "с публикациями"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help="Путь к research-outputs.json",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="Путь к результирующему CSV",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_FILE,
        help="Путь к Markdown-отчёту",
    )

    return parser.parse_args()


def load_publications(
    input_file: Path,
) -> list[dict[str, Any]]:
    """Загрузить публикации из поля items."""

    if not input_file.exists():
        raise FileNotFoundError(
            f"Файл не найден: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise TypeError(
            "Корневой JSON должен быть объектом"
        )

    items = data.get("items")

    if not isinstance(items, list):
        raise TypeError(
            'Поле "items" отсутствует или не массив'
        )

    publications: list[dict[str, Any]] = []

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(
                f"Элемент items[{index}] не объектом"
            )

        publications.append(item)

    return publications


def clean_text(value: Any) -> str:
    """Очистить строковое значение"""

    if not isinstance(value, str):
        return ""

    return " ".join(
        value
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )


def unique_values(values: list[str]) -> list[str]:
    """Удалить повторы, сохранив исходный порядок"""

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = clean_text(value)

        if not cleaned:
            continue

        normalized = cleaned.casefold()

        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(cleaned)

    return result


def extract_localized_values(
    container: Any,
) -> list[tuple[str, str]]:
    """
    Извлечь пары locale-value из объекта с полем text

    Пример:

    {
        "text": [
            {"locale": "ru_RU", "value": "..."}
        ]
    }
    """

    if not isinstance(container, dict):
        return []

    text_items = container.get("text")

    if not isinstance(text_items, list):
        return []

    result: list[tuple[str, str]] = []

    for item in text_items:
        if not isinstance(item, dict):
            continue

        value = clean_text(item.get("value"))

        if not value:
            continue

        locale = clean_text(item.get("locale"))

        result.append((locale, value))

    return result


def select_localized_value(
    container: Any,
) -> str:
    """
    Выбрать одно локализованное значение

    Приоритет:
    1. ru_RU;
    2. en_US;
    3. первое доступное значение
    """

    values = extract_localized_values(container)

    for preferred_locale in PREFERRED_LOCALES:
        for locale, value in values:
            if locale == preferred_locale:
                return value

    if values:
        return values[0][1]

    return ""


def extract_title(publication: dict[str, Any]) -> str:
    """Извлечь название публикации"""

    title = publication.get("title")

    if not isinstance(title, dict):
        return ""

    return clean_text(title.get("value"))


def extract_abstract(
    publication: dict[str, Any],
) -> str:
    """Извлечь и объединить все версии аннотации"""

    abstract = publication.get("abstract")

    if not isinstance(abstract, dict):
        return ""

    text_items = abstract.get("text")

    if not isinstance(text_items, list):
        return ""

    values: list[str] = []

    for item in text_items:
        if not isinstance(item, dict):
            continue

        value = clean_text(item.get("value"))

        if value:
            values.append(value)

    return " ".join(unique_values(values))


def select_current_status(
    publication: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Выбрать текущий статус публикации

    Если current=true отсутствует, используется первый статус
    """

    statuses = publication.get("publicationStatuses")

    if not isinstance(statuses, list):
        return None

    valid_statuses = [
        status
        for status in statuses
        if isinstance(status, dict)
    ]

    for status in valid_statuses:
        if status.get("current") is True:
            return status

    if valid_statuses:
        return valid_statuses[0]

    return None


def extract_publication_year(
    publication: dict[str, Any],
) -> int | None:
    """Извлечь год из текущего статуса"""

    status = select_current_status(publication)

    if status is None:
        return None

    publication_date = status.get("publicationDate")

    if not isinstance(publication_date, dict):
        return None

    year = publication_date.get("year")

    if isinstance(year, int):
        return year

    return None


def extract_term_value(value: Any) -> str:
    """Извлечь локализованное значение из поля term"""

    if not isinstance(value, dict):
        return ""

    return select_localized_value(
        value.get("term")
    )


def extract_keywords(
    publication: dict[str, Any],
) -> list[str]:
    """
    Извлечь структурированные и свободные ключевые слова
    """

    groups = publication.get("keywordGroups")

    if not isinstance(groups, list):
        return []

    keywords: list[str] = []

    for group in groups:
        if not isinstance(group, dict):
            continue

        containers = group.get("keywordContainers")

        if not isinstance(containers, list):
            continue

        for container in containers:
            if not isinstance(container, dict):
                continue

            structured_keyword = container.get(
                "structuredKeyword"
            )

            if isinstance(structured_keyword, dict):
                keyword = extract_term_value(
                    structured_keyword
                )

                if keyword:
                    keywords.append(keyword)

            free_keyword_groups = container.get(
                "freeKeywords"
            )

            if not isinstance(free_keyword_groups, list):
                continue

            for free_keyword_group in free_keyword_groups:
                if not isinstance(free_keyword_group, dict):
                    continue

                free_keywords = free_keyword_group.get(
                    "freeKeywords"
                )

                if not isinstance(free_keywords, list):
                    continue

                for keyword in free_keywords:
                    cleaned = clean_text(keyword)

                    if cleaned:
                        keywords.append(cleaned)

    return unique_values(keywords)


def extract_entity_name(entity: Any) -> str:
    """Извлечь локал имя объекта Pure"""

    if not isinstance(entity, dict):
        return ""

    name = entity.get("name")

    return select_localized_value(name)


def extract_researcher_name(
    association: dict[str, Any],
) -> str:
    """Извлечь полное имя внутреннего исследователя"""

    person = association.get("person")

    if isinstance(person, dict):
        person_name = extract_entity_name(person)

        if person_name:
            return person_name

    short_name = association.get("name")

    if not isinstance(short_name, dict):
        return ""

    first_name = clean_text(
        short_name.get("firstName")
    )

    last_name = clean_text(
        short_name.get("lastName")
    )

    return " ".join(
        value
        for value in (first_name, last_name)
        if value
    )


def extract_organisational_units(
    association: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Извлечь UUID и названия подразделений автора"""

    units = association.get("organisationalUnits")

    if not isinstance(units, list):
        return [], []

    unit_ids: list[str] = []
    unit_names: list[str] = []

    for unit in units:
        if not isinstance(unit, dict):
            continue

        unit_id = clean_text(unit.get("uuid"))
        unit_name = extract_entity_name(unit)

        if unit_id:
            unit_ids.append(unit_id)

        if unit_name:
            unit_names.append(unit_name)

    return (
        unique_values(unit_ids),
        unique_values(unit_names),
    )


def create_rows(
    publications: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Создать строки таблицы researcher-publication"""

    rows: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    statistics = Counter(
        {
            "publications": len(publications),
            "associations": 0,
            "internal_associations": 0,
            "external_associations": 0,
            "duplicate_pairs": 0,
            "publications_without_internal_researcher": 0,
            "publications_with_multiple_statuses": 0,
            "publications_without_current_status": 0,
            "publications_with_multiple_current_statuses": 0,
            "author_count_mismatches": 0,
        }
    )

    for publication in publications:
        publication_id = clean_text(
            publication.get("uuid")
        )

        title = extract_title(publication)
        abstract = extract_abstract(publication)
        year = extract_publication_year(publication)
        keywords = extract_keywords(publication)

        publication_type = extract_term_value(
            publication.get("type")
        )

        category = extract_term_value(
            publication.get("category")
        )

        language = extract_term_value(
            publication.get("language")
        )

        managing_unit = publication.get(
            "managingOrganisationalUnit"
        )

        managing_unit_id = ""

        if isinstance(managing_unit, dict):
            managing_unit_id = clean_text(
                managing_unit.get("uuid")
            )

        managing_unit_name = extract_entity_name(
            managing_unit
        )

        statuses = publication.get(
            "publicationStatuses"
        )

        if isinstance(statuses, list):
            valid_statuses = [
                status
                for status in statuses
                if isinstance(status, dict)
            ]

            if len(valid_statuses) > 1:
                statistics[
                    "publications_with_multiple_statuses"
                ] += 1

            current_statuses = [
                status
                for status in valid_statuses
                if status.get("current") is True
            ]

            if not current_statuses:
                statistics[
                    "publications_without_current_status"
                ] += 1

            if len(current_statuses) > 1:
                statistics[
                    "publications_with_multiple_current_statuses"
                ] += 1

        associations = publication.get(
            "personAssociations"
        )

        if not isinstance(associations, list):
            associations = []

        valid_associations = [
            association
            for association in associations
            if isinstance(association, dict)
        ]

        statistics["associations"] += len(
            valid_associations
        )

        declared_author_count = publication.get(
            "totalNumberOfAuthors"
        )

        if (
            isinstance(declared_author_count, int)
            and declared_author_count
            != len(valid_associations)
        ):
            statistics["author_count_mismatches"] += 1

        internal_researchers_in_publication = 0

        for association in valid_associations:
            person = association.get("person")

            if not isinstance(person, dict):
                statistics["external_associations"] += 1
                continue

            researcher_id = clean_text(
                person.get("uuid")
            )

            if not researcher_id:
                statistics["external_associations"] += 1
                continue

            statistics["internal_associations"] += 1
            internal_researchers_in_publication += 1

            pair = (
                researcher_id,
                publication_id,
            )

            if pair in seen_pairs:
                statistics["duplicate_pairs"] += 1
                continue

            seen_pairs.add(pair)

            researcher_name = extract_researcher_name(
                association
            )

            role = extract_term_value(
                association.get("personRole")
            )

            role_uri = ""

            person_role = association.get(
                "personRole"
            )

            if isinstance(person_role, dict):
                role_uri = clean_text(
                    person_role.get("uri")
                )

            (
                researcher_unit_ids,
                researcher_unit_names,
            ) = extract_organisational_units(
                association
            )

            rows.append(
                {
                    "researcher_id": researcher_id,
                    "researcher_name": researcher_name,
                    "publication_id": publication_id,
                    "publication_title": title,
                    "publication_year": (
                        year if year is not None else ""
                    ),
                    "abstract": abstract,
                    "keywords": "; ".join(keywords),
                    "publication_type": publication_type,
                    "category": category,
                    "language": language,
                    "author_role": role,
                    "author_role_uri": role_uri,
                    "researcher_organisational_unit_ids": (
                        "; ".join(researcher_unit_ids)
                    ),
                    "researcher_organisational_units": (
                        "; ".join(researcher_unit_names)
                    ),
                    "managing_organisational_unit_id": (
                        managing_unit_id
                    ),
                    "managing_organisational_unit_name": (
                        managing_unit_name
                    ),
                    "total_number_of_authors": (
                        declared_author_count
                        if isinstance(
                            declared_author_count,
                            int,
                        )
                        else ""
                    ),
                }
            )

        if internal_researchers_in_publication == 0:
            statistics[
                "publications_without_internal_researcher"
            ] += 1

    statistics["rows"] = len(rows)
    statistics["unique_researchers"] = len(
        {
            row["researcher_id"]
            for row in rows
        }
    )

    return rows, dict(statistics)


def write_csv(
    output_file: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Сохранить таблицу в CSV"""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "researcher_id",
        "researcher_name",
        "publication_id",
        "publication_title",
        "publication_year",
        "abstract",
        "keywords",
        "publication_type",
        "category",
        "language",
        "author_role",
        "author_role_uri",
        "researcher_organisational_unit_ids",
        "researcher_organisational_units",
        "managing_organisational_unit_id",
        "managing_organisational_unit_name",
        "total_number_of_authors",
    ]

    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def build_report(
    input_file: Path,
    output_file: Path,
    rows: list[dict[str, Any]],
    statistics: dict[str, int],
) -> str:
    """Сформировать Markdown-отчёт"""

    rows_with_abstract = sum(
        bool(row["abstract"])
        for row in rows
    )

    rows_with_keywords = sum(
        bool(row["keywords"])
        for row in rows
    )

    rows_with_units = sum(
        bool(row["researcher_organisational_units"])
        for row in rows
    )

    publication_counts = Counter(
        row["researcher_id"]
        for row in rows
    )

    researchers_with_one_publication = sum(
        count == 1
        for count in publication_counts.values()
    )

    researchers_with_two_or_more = sum(
        count >= 2
        for count in publication_counts.values()
    )

    researchers_with_five_or_more = sum(
        count >= 5
        for count in publication_counts.values()
    )

    total_rows = len(rows)

    def percentage(value: int) -> float:
        if total_rows == 0:
            return 0.0

        return value / total_rows * 100

    lines = [
        "# Отчёт о таблице researcher-publication",
        "",
        "## Файлы",
        "",
        f"- Исходный JSON: `{input_file}`",
        f"- Результирующий CSV: `{output_file}`",
        "",
        "## Общая статистика",
        "",
        f"- Публикаций: **{statistics['publications']}**",
        f"- Авторских связей: **{statistics['associations']}**",
        (
            "- Связей с внутренними исследователями: "
            f"**{statistics['internal_associations']}**"
        ),
        (
            "- Связей с внешними авторами без внутреннего UUID: "
            f"**{statistics['external_associations']}**"
        ),
        (
            "- Уникальных внутренних исследователей: "
            f"**{statistics['unique_researchers']}**"
        ),
        (
            "- Строк в результирующей таблице: "
            f"**{statistics['rows']}**"
        ),
        (
            "- Повторных пар researcher-publication: "
            f"**{statistics['duplicate_pairs']}**"
        ),
        "",
        "## Качество связей",
        "",
        (
            "- Публикаций без внутреннего исследователя: "
            f"**{statistics['publications_without_internal_researcher']}**"
        ),
        (
            "- Публикаций с несколькими статусами: "
            f"**{statistics['publications_with_multiple_statuses']}**"
        ),
        (
            "- Публикаций без current=true: "
            f"**{statistics['publications_without_current_status']}**"
        ),
        (
            "- Публикаций с несколькими current=true: "
            f"**{statistics['publications_with_multiple_current_statuses']}**"
        ),
        (
            "- Несовпадений totalNumberOfAuthors "
            "с количеством personAssociations: "
            f"**{statistics['author_count_mismatches']}**"
        ),
        "",
        "## Заполненность строк",
        "",
        (
            f"- С аннотацией: **{rows_with_abstract} "
            f"({percentage(rows_with_abstract):.2f}%)**"
        ),
        (
            f"- С ключевыми словами: **{rows_with_keywords} "
            f"({percentage(rows_with_keywords):.2f}%)**"
        ),
        (
            f"- С подразделением исследователя: "
            f"**{rows_with_units} "
            f"({percentage(rows_with_units):.2f}%)**"
        ),
        "",
        "## Публикационная активность исследователей",
        "",
        (
            "- Исследователей ровно с одной публикацией: "
            f"**{researchers_with_one_publication}**"
        ),
        (
            "- Исследователей с двумя и более публикациями: "
            f"**{researchers_with_two_or_more}**"
        ),
        (
            "- Исследователей с пятью и более публикациями: "
            f"**{researchers_with_five_or_more}**"
        ),
        "",
        "## Решение для первой версии",
        "",
        (
            "В таблицу включены только внутренние исследователи, "
            "для которых присутствует стабильный `person.uuid`"
        ),
        "",
        (
            "Внешние авторы учтены в статистике, но не включены "
            "в таблицу рекомендаций из-за отсутствия устойчивого "
            "идентификатора"
        ),
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """Запустить формирование таблицы"""

    args = parse_arguments()

    input_file = args.input.resolve()
    output_file = args.output.resolve()
    report_file = args.report.resolve()

    publications = load_publications(
        input_file
    )

    rows, statistics = create_rows(
        publications
    )

    write_csv(
        output_file,
        rows,
    )

    report = build_report(
        input_file=input_file,
        output_file=output_file,
        rows=rows,
        statistics=statistics,
    )

    report_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_file.write_text(
        report,
        encoding="utf-8",
    )

    print(f"Исходный файл: {input_file}")
    print(
        f"Обработано публикаций: "
        f"{statistics['publications']}"
    )
    print(
        f"Найдено внутренних исследователей: "
        f"{statistics['unique_researchers']}"
    )
    print(
        f"Создано строк researcher-publication: "
        f"{statistics['rows']}"
    )
    print(f"CSV сохранён: {output_file}")
    print(f"Отчёт сохранён: {report_file}")


if __name__ == "__main__":
    main()