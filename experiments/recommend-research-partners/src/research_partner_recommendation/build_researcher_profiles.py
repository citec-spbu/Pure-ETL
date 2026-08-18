from __future__ import annotations

import argparse
import csv
import html
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_FILE = (
    EXPERIMENT_DIR
    / "output"
    / "researcher_publications.csv"
)

DEFAULT_OUTPUT_FILE = (
    EXPERIMENT_DIR
    / "output"
    / "researcher_profiles.csv"
)

DEFAULT_REPORT_FILE = (
    EXPERIMENT_DIR
    / "reports"
    / "researcher_profiles_summary.md"
)

REQUIRED_COLUMNS = {
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
    "researcher_organisational_unit_ids",
    "researcher_organisational_units",
}

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


def parse_arguments() -> argparse.Namespace:
   
    parser = argparse.ArgumentParser(
        description=(
            "Объединить публикации каждого исследователя "
            "в единый текстовый профиль"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help="Путь к researcher_publications.csv",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="Путь к researcher_profiles.csv",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_FILE,
        help="Путь к Markdown-отчёту",
    )

    return parser.parse_args()


def clean_text(value: Any) -> str:
   
    if not isinstance(value, str):
        return ""

    text = html.unescape(value)
    text = HTML_TAG_PATTERN.sub(" ", text)
    text = unicodedata.normalize("NFKC", text)
    text = WHITESPACE_PATTERN.sub(" ", text)

    return text.strip()


def normalize_for_model(value: Any) -> str:
   

    return clean_text(value).casefold()


def split_multivalue(value: Any) -> list[str]:
 
    text = clean_text(value)

    if not text:
        return []

    return [
        cleaned
        for part in text.split(";")
        if (cleaned := clean_text(part))
    ]


def stable_unique(values: list[str]) -> list[str]:
  
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = clean_text(value)

        if not cleaned:
            continue

        normalized = normalize_for_model(cleaned)

        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(cleaned)

    return result


def parse_year(value: Any) -> int | None:
  
    text = clean_text(value)

    if not text:
        return None

    try:
        return int(text)
    except ValueError:
        return None


def join_text_parts(parts: list[str]) -> str:
  
    cleaned_parts = [
        cleaned
        for part in parts
        if (cleaned := clean_text(part))
    ]

    return ". ".join(cleaned_parts)


@dataclass
class Publication:
   
    publication_id: str
    title: str
    year: int | None
    abstract: str
    keywords: list[str]
    publication_type: str
    category: str
    language: str


@dataclass
class ResearcherAccumulator:
   
    researcher_id: str

    names: Counter[str] = field(
        default_factory=Counter
    )

    publications: dict[str, Publication] = field(
        default_factory=dict
    )

    organisational_unit_ids: list[str] = field(
        default_factory=list
    )

    organisational_units: list[str] = field(
        default_factory=list
    )

    def add_row(self, row: dict[str, str]) -> bool:
       
        researcher_name = clean_text(
            row.get("researcher_name")
        )

        if researcher_name:
            self.names[researcher_name] += 1

        self.organisational_unit_ids.extend(
            split_multivalue(
                row.get(
                    "researcher_organisational_unit_ids"
                )
            )
        )

        self.organisational_units.extend(
            split_multivalue(
                row.get(
                    "researcher_organisational_units"
                )
            )
        )

        publication_id = clean_text(
            row.get("publication_id")
        )

        if not publication_id:
            return False

        if publication_id in self.publications:
            return False

        self.publications[publication_id] = Publication(
            publication_id=publication_id,
            title=clean_text(
                row.get("publication_title")
            ),
            year=parse_year(
                row.get("publication_year")
            ),
            abstract=clean_text(
                row.get("abstract")
            ),
            keywords=split_multivalue(
                row.get("keywords")
            ),
            publication_type=clean_text(
                row.get("publication_type")
            ),
            category=clean_text(
                row.get("category")
            ),
            language=clean_text(
                row.get("language")
            ),
        )

        return True

    def select_name(self) -> str:
       
        if not self.names:
            return ""

        return self.names.most_common(1)[0][0]


def load_rows(
    input_file: Path,
) -> list[dict[str, str]]:
   
    if not input_file.exists():
        raise FileNotFoundError(
            f"Файл не найден: {input_file}\n"
            "Сначала запусти build-researcher-publications"
        )

    with input_file.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                "CSV не содержит заголовка"
            )

        missing_columns = (
            REQUIRED_COLUMNS
            - set(reader.fieldnames)
        )

        if missing_columns:
            columns = ", ".join(
                sorted(missing_columns)
            )

            raise ValueError(
                "В исходном CSV отсутствуют поля: "
                f"{columns}"
            )

        return [dict(row) for row in reader]


def build_profile_row(
    researcher: ResearcherAccumulator,
) -> dict[str, Any]:

    publications = sorted(
        researcher.publications.values(),
        key=lambda publication: (
            publication.year is None,
            publication.year or 0,
            publication.publication_id,
        ),
    )

    publication_ids = [
        publication.publication_id
        for publication in publications
    ]

    years = [
        publication.year
        for publication in publications
        if publication.year is not None
    ]

    titles = stable_unique(
        [
            publication.title
            for publication in publications
        ]
    )

    abstracts = stable_unique(
        [
            publication.abstract
            for publication in publications
        ]
    )

    repeated_keywords = [
        keyword
        for publication in publications
        for keyword in publication.keywords
    ]

    unique_keywords = stable_unique(
        repeated_keywords
    )

    publication_types = stable_unique(
        [
            publication.publication_type
            for publication in publications
        ]
    )

    categories = stable_unique(
        [
            publication.category
            for publication in publications
        ]
    )

    languages = stable_unique(
        [
            publication.language
            for publication in publications
        ]
    )

    core_parts: list[str] = []
    full_parts: list[str] = []

    for publication in publications:
        publication_core = [
            publication.title,
            *publication.keywords,
            publication.publication_type,
            publication.category,
        ]

        core_parts.extend(publication_core)
        full_parts.extend(publication_core)

        if publication.abstract:
            full_parts.append(
                publication.abstract
            )

    profile_text_core = join_text_parts(
        core_parts
    )

    profile_text_full = join_text_parts(
        full_parts
    )

    organisational_unit_ids = stable_unique(
        researcher.organisational_unit_ids
    )

    organisational_units = stable_unique(
        researcher.organisational_units
    )

    return {
        "researcher_id": researcher.researcher_id,
        "researcher_name": researcher.select_name(),
        "publication_count": len(publications),
        "first_publication_year": (
            min(years) if years else ""
        ),
        "last_publication_year": (
            max(years) if years else ""
        ),
        "publication_years": "; ".join(
            str(year)
            for year in sorted(set(years))
        ),
        "publication_ids": "; ".join(
            publication_ids
        ),
        "title_count": len(titles),
        "titles": " || ".join(titles),
        "abstract_publication_count": sum(
            bool(publication.abstract)
            for publication in publications
        ),
        "abstracts": " || ".join(abstracts),
        "unique_keyword_count": len(
            unique_keywords
        ),
        "keyword_occurrence_count": len(
            repeated_keywords
        ),
        "keywords": "; ".join(
            unique_keywords
        ),
        "publication_types": "; ".join(
            publication_types
        ),
        "categories": "; ".join(
            categories
        ),
        "languages": "; ".join(
            languages
        ),
        "organisational_unit_ids": "; ".join(
            organisational_unit_ids
        ),
        "organisational_units": "; ".join(
            organisational_units
        ),
        "profile_text_core": profile_text_core,
        "profile_text_full": profile_text_full,
        "profile_text_core_normalized": (
            normalize_for_model(
                profile_text_core
            )
        ),
        "profile_text_full_normalized": (
            normalize_for_model(
                profile_text_full
            )
        ),
    }


def build_profiles(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:

    researchers: dict[
        str,
        ResearcherAccumulator,
    ] = {}

    skipped_without_researcher_id = 0
    skipped_without_publication_id = 0
    duplicate_pairs = 0

    for row in rows:
        researcher_id = clean_text(
            row.get("researcher_id")
        )

        if not researcher_id:
            skipped_without_researcher_id += 1
            continue

        publication_id = clean_text(
            row.get("publication_id")
        )

        if not publication_id:
            skipped_without_publication_id += 1
            continue

        researcher = researchers.setdefault(
            researcher_id,
            ResearcherAccumulator(
                researcher_id=researcher_id
            ),
        )

        added = researcher.add_row(row)

        if not added:
            duplicate_pairs += 1

    profile_rows = [
        build_profile_row(researcher)
        for researcher in researchers.values()
    ]

    profile_rows.sort(
        key=lambda row: (
            -int(row["publication_count"]),
            str(row["researcher_name"]).casefold(),
            str(row["researcher_id"]),
        )
    )

    statistics = {
        "input_rows": len(rows),
        "profiles": len(profile_rows),
        "skipped_without_researcher_id": (
            skipped_without_researcher_id
        ),
        "skipped_without_publication_id": (
            skipped_without_publication_id
        ),
        "duplicate_pairs": duplicate_pairs,
    }

    return profile_rows, statistics


def write_profiles(
    output_file: Path,
    profiles: list[dict[str, Any]],
) -> None:
   
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "researcher_id",
        "researcher_name",
        "publication_count",
        "first_publication_year",
        "last_publication_year",
        "publication_years",
        "publication_ids",
        "title_count",
        "titles",
        "abstract_publication_count",
        "abstracts",
        "unique_keyword_count",
        "keyword_occurrence_count",
        "keywords",
        "publication_types",
        "categories",
        "languages",
        "organisational_unit_ids",
        "organisational_units",
        "profile_text_core",
        "profile_text_full",
        "profile_text_core_normalized",
        "profile_text_full_normalized",
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
        writer.writerows(profiles)


def build_report(
    *,
    input_file: Path,
    output_file: Path,
    profiles: list[dict[str, Any]],
    statistics: dict[str, int],
) -> str:
   
    publication_counts = [
        int(profile["publication_count"])
        for profile in profiles
    ]

    core_lengths = [
        len(
            str(
                profile[
                    "profile_text_core_normalized"
                ]
            )
        )
        for profile in profiles
    ]

    full_lengths = [
        len(
            str(
                profile[
                    "profile_text_full_normalized"
                ]
            )
        )
        for profile in profiles
    ]

    profiles_with_abstracts = sum(
        int(
            profile[
                "abstract_publication_count"
            ]
        ) > 0
        for profile in profiles
    )

    profiles_with_keywords = sum(
        int(
            profile[
                "unique_keyword_count"
            ]
        ) > 0
        for profile in profiles
    )

    profiles_with_units = sum(
        bool(profile["organisational_units"])
        for profile in profiles
    )

    researchers_with_one_publication = sum(
        count == 1
        for count in publication_counts
    )

    researchers_with_two_or_more = sum(
        count >= 2
        for count in publication_counts
    )

    researchers_with_five_or_more = sum(
        count >= 5
        for count in publication_counts
    )

    total_profiles = len(profiles)

    def percentage(value: int) -> float:
        if total_profiles == 0:
            return 0.0

        return value / total_profiles * 100

    def average(values: list[int]) -> float:
        if not values:
            return 0.0

        return mean(values)

    def middle(values: list[int]) -> float:
        if not values:
            return 0.0

        return median(values)

    lines = [
        "# Отчёт о публикационных профилях",
        "",
        "## Файлы",
        "",
        f"- Исходная таблица: `{input_file}`",
        f"- Результирующий CSV: `{output_file}`",
        "",
        "## Общая статистика",
        "",
        (
            "- Строк researcher-publication прочитано: "
            f"**{statistics['input_rows']}**"
        ),
        (
            "- Сформировано профилей исследователей: "
            f"**{statistics['profiles']}**"
        ),
        (
            "- Пропущено строк без researcher_id: "
            f"**{statistics['skipped_without_researcher_id']}**"
        ),
        (
            "- Пропущено строк без publication_id: "
            f"**{statistics['skipped_without_publication_id']}**"
        ),
        (
            "- Повторных пар researcher-publication: "
            f"**{statistics['duplicate_pairs']}**"
        ),
        "",
        "## Публикационная активность",
        "",
        (
            "- Исследователей с одной публикацией: "
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
        (
            "- Среднее число публикаций: "
            f"**{average(publication_counts):.2f}**"
        ),
        (
            "- Медианное число публикаций: "
            f"**{middle(publication_counts):.2f}**"
        ),
        (
            "- Максимальное число публикаций: "
            f"**{max(publication_counts) if publication_counts else 0}**"
        ),
        "",
        "## Заполненность профилей",
        "",
        (
            f"- С ключевыми словами: "
            f"**{profiles_with_keywords} "
            f"({percentage(profiles_with_keywords):.2f}%)**"
        ),
        (
            f"- Хотя бы с одной аннотацией: "
            f"**{profiles_with_abstracts} "
            f"({percentage(profiles_with_abstracts):.2f}%)**"
        ),
        (
            f"- С подразделением: "
            f"**{profiles_with_units} "
            f"({percentage(profiles_with_units):.2f}%)**"
        ),
        "",
        "## Размер текста",
        "",
        (
            "- Средняя длина core-профиля: "
            f"**{average(core_lengths):.2f} символа**"
        ),
        (
            "- Медианная длина core-профиля: "
            f"**{middle(core_lengths):.2f} символа**"
        ),
        (
            "- Средняя длина full-профиля: "
            f"**{average(full_lengths):.2f} символа**"
        ),
        (
            "- Медианная длина full-профиля: "
            f"**{middle(full_lengths):.2f} символа**"
        ),
        "",
        "## Сформированные варианты профиля",
        "",
        (
            "- `profile_text_core`: названия, ключевые "
            "слова, типы и категории публикаций"
        ),
        (
            "- `profile_text_full`: core-профиль плюс "
            "аннотации при их наличии"
        ),
        (
            "- Нормализованные варианты приведены к "
            "единому Unicode-представлению и регистру"
        ),
        "",
        "## Решение для следующего этапа",
        "",
        (
            "На этапе TF-IDF необходимо сравнить качество "
            "`profile_text_core_normalized` и "
            "`profile_text_full_normalized`"
        ),
        "",
        (
            "Исследователи с одной публикацией пока сохранены, "
            "но качество их рекомендаций следует оценивать отдельно"
        ),
        "",
    ]

    return "\n".join(lines)


def main() -> None:
  
    args = parse_arguments()

    input_file = args.input.resolve()
    output_file = args.output.resolve()
    report_file = args.report.resolve()

    rows = load_rows(input_file)

    profiles, statistics = build_profiles(
        rows
    )

    write_profiles(
        output_file,
        profiles,
    )

    report = build_report(
        input_file=input_file,
        output_file=output_file,
        profiles=profiles,
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
        f"Прочитано связей researcher-publication: "
        f"{statistics['input_rows']}"
    )
    print(
        f"Сформировано профилей: "
        f"{statistics['profiles']}"
    )
    print(f"CSV сохранён: {output_file}")
    print(f"Отчёт сохранён: {report_file}")


if __name__ == "__main__":
    main()