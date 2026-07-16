from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from statistics import mean
from typing import Any, Iterator


EXPERIMENT_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]

DEFAULT_DATA_FILE = REPOSITORY_ROOT / "Data" / "research-outputs.json"
DEFAULT_REPORT_FILE = (
    EXPERIMENT_DIR
    / "reports"
    / "nested_fields_structure.md"
)

TARGET_FIELDS = (
    "title",
    "abstract",
    "publicationStatuses",
    "personAssociations",
    "keywordGroups",
    "managingOrganisationalUnit",
    "organisationalUnits",
    "type",
    "category",
    "language",
)


def parse_arguments() -> argparse.Namespace:
    """Прочитать аргументы кс"""

    parser = argparse.ArgumentParser(
        description=(
            "Исследовать вложенную структуру ключевых полей "
            "файла research-outputs.json"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="Путь к JSON-файлу с публикациями",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_FILE,
        help="Путь к создаваемому Markdown-отчёту",
    )

    return parser.parse_args()


def get_json_type(value: Any) -> str:
    """Вернуть название JSON-типа значения"""

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "number"

    if isinstance(value, str):
        return "string"

    if isinstance(value, list):
        return "array"

    if isinstance(value, dict):
        return "object"

    return type(value).__name__


def is_empty(value: Any) -> bool:
    """Проверить, является ли значение пустым"""

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict)):
        return len(value) == 0

    return False


def make_preview(value: Any, max_length: int = 120) -> str:
    """Сформировать короткое представление значения"""

    if value is None:
        return "null"

    if isinstance(value, dict):
        keys = ", ".join(str(key) for key in list(value.keys())[:10])
        return f"object keys: {keys or 'none'}"

    if isinstance(value, list):
        return f"array with {len(value)} item(s)"

    text = str(value).replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())

    if len(text) > max_length:
        return text[: max_length - 3] + "..."

    return text


def walk_json(
    value: Any,
    path: str,
) -> Iterator[tuple[str, str, str]]:
    """
    Рекурсивно обойти JSON-значение

    Для элементов массива используется обозначение []
    Например:
    personAssociations[].person.uuid
    """

    yield path, get_json_type(value), make_preview(value)

    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}"
            yield from walk_json(nested_value, nested_path)

    elif isinstance(value, list):
        nested_path = f"{path}[]"

        for item in value:
            yield from walk_json(item, nested_path)


@dataclass
class FieldProfile:
    """Статистика одного поля"""

    name: str
    present: int = 0
    null_values: int = 0
    empty_values: int = 0
    type_counts: Counter[str] = dataclass_field(
        default_factory=Counter
    )
    list_lengths: list[int] = dataclass_field(
        default_factory=list
    )
    path_presence: Counter[str] = dataclass_field(
        default_factory=Counter
    )
    path_types: dict[str, Counter[str]] = dataclass_field(
        default_factory=lambda: defaultdict(Counter)
    )
    path_examples: dict[str, str] = dataclass_field(
        default_factory=dict
    )
    example: Any = None
    example_is_set: bool = False

    def add_value(self, value: Any) -> None:
        """Добавить одно значение в профиль"""

        self.present += 1
        self.type_counts[get_json_type(value)] += 1

        if value is None:
            self.null_values += 1
        elif is_empty(value):
            self.empty_values += 1

        if isinstance(value, list):
            self.list_lengths.append(len(value))

        if (
            not self.example_is_set
            and value is not None
            and not is_empty(value)
        ):
            self.example = value
            self.example_is_set = True

        paths_seen_in_record: set[str] = set()

        for path, value_type, preview in walk_json(
            value,
            self.name,
        ):
            self.path_types[path][value_type] += 1
            self.path_examples.setdefault(path, preview)
            paths_seen_in_record.add(path)

        for path in paths_seen_in_record:
            self.path_presence[path] += 1


def load_records(input_file: Path) -> list[dict[str, Any]]:
    """Загрузить публикации из поля items"""

    if not input_file.exists():
        raise FileNotFoundError(
            f"Файл не найден: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise TypeError(
            "Ожидался JSON-объект с полем items"
        )

    items = data.get("items")

    if not isinstance(items, list):
        raise TypeError(
            'Поле "items" отсутствует или не является массивом'
        )

    invalid_items = [
        index
        for index, item in enumerate(items)
        if not isinstance(item, dict)
    ]

    if invalid_items:
        preview = invalid_items[:10]

        raise TypeError(
            "Некоторые элементы items не являются объектами "
            f"Индексы первых ошибок: {preview}"
        )

    return items


def escape_markdown_cell(value: str) -> str:
    """Экранировать текст для ячейки Markdown"""

    return (
        value
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def format_json_example(
    value: Any,
    max_length: int = 4000,
) -> str:
    """Преобразовать пример значения в форматированный JSON"""

    text = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
    )

    if len(text) > max_length:
        text = text[:max_length] + "\n... пример сокращён ..."

    return text


def build_report(
    *,
    input_file: Path,
    records: list[dict[str, Any]],
    profiles: dict[str, FieldProfile],
) -> str:
    """Сформировать Markdown-отчёт"""

    total = len(records)

    lines = [
        "# Исследование вложенных полей research-outputs.json",
        "",
        "## Исходный файл",
        "",
        f"`{input_file}`",
        "",
        "## Общая информация",
        "",
        f"- Количество публикаций: **{total}**",
        f"- Исследуемых полей: **{len(TARGET_FIELDS)}**",
        "",
        "## Заполненность ключевых полей",
        "",
        (
            "| Поле | Присутствует | Непустых значений | "
            "Null | Пустых | Типы |"
        ),
        "|---|---:|---:|---:|---:|---|",
    ]

    for field_name in TARGET_FIELDS:
        profile = profiles[field_name]

        non_empty = (
            profile.present
            - profile.null_values
            - profile.empty_values
        )

        types = ", ".join(
            f"{value_type}: {count}"
            for value_type, count
            in profile.type_counts.most_common()
        )

        lines.append(
            f"| `{field_name}` "
            f"| {profile.present} ({profile.present / total * 100:.2f}%) "
            f"| {non_empty} ({non_empty / total * 100:.2f}%) "
            f"| {profile.null_values} "
            f"| {profile.empty_values} "
            f"| {types or '—'} |"
        )

    for field_name in TARGET_FIELDS:
        profile = profiles[field_name]

        lines.extend(
            [
                "",
                f"## Поле `{field_name}`",
                "",
            ]
        )

        if profile.list_lengths:
            lines.extend(
                [
                    "### Размер массивов",
                    "",
                    (
                        f"- Минимум элементов: "
                        f"**{min(profile.list_lengths)}**"
                    ),
                    (
                        f"- Среднее количество элементов: "
                        f"**{mean(profile.list_lengths):.2f}**"
                    ),
                    (
                        f"- Максимум элементов: "
                        f"**{max(profile.list_lengths)}**"
                    ),
                    "",
                ]
            )

        if profile.example_is_set:
            lines.extend(
                [
                    "### Первый непустой пример",
                    "",
                    "```json",
                    format_json_example(profile.example),
                    "```",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "Непустой пример не найден",
                    "",
                ]
            )

        lines.extend(
            [
                "### Обнаруженные вложенные пути",
                "",
                (
                    "| JSON-путь | Публикаций с путём | "
                    "Типы значений | Пример |"
                ),
                "|---|---:|---|---|",
            ]
        )

        sorted_paths = sorted(
            profile.path_presence,
            key=lambda path: (
                -profile.path_presence[path],
                path,
            ),
        )

        for path in sorted_paths:
            presence = profile.path_presence[path]

            types = ", ".join(
                f"{value_type}: {count}"
                for value_type, count
                in profile.path_types[path].most_common()
            )

            example = escape_markdown_cell(
                profile.path_examples.get(path, "")
            )

            lines.append(
                f"| `{path}` "
                f"| {presence} ({presence / total * 100:.2f}%) "
                f"| {types} "
                f"| {example} |"
            )

    lines.extend(
        [
            "",
            "## Как использовать результат",
            "",
            (
                "После анализа отчёта нужно определить точные пути "
                "к следующим значениям:"
            ),
            "",
            "1. UUID исследователя.",
            "2. Имя исследователя.",
            "3. Роль автора.",
            "4. Год публикации.",
            "5. Название публикации.",
            "6. Текст аннотации.",
            "7. Ключевые слова.",
            "8. Научные классификации.",
            "9. Организационное подразделение.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """Запустить исследование вложенных полей"""

    args = parse_arguments()

    input_file = args.input.resolve()
    output_file = args.output.resolve()

    records = load_records(input_file)

    profiles = {
        field_name: FieldProfile(name=field_name)
        for field_name in TARGET_FIELDS
    }

    for record in records:
        for field_name in TARGET_FIELDS:
            if field_name in record:
                profiles[field_name].add_value(
                    record[field_name]
                )

    report = build_report(
        input_file=input_file,
        records=records,
        profiles=profiles,
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        report,
        encoding="utf-8",
    )

    print(f"Исходный файл: {input_file}")
    print(f"Обработано публикаций: {len(records)}")
    print(f"Исследовано полей: {len(TARGET_FIELDS)}")
    print(f"Отчёт сохранён: {output_file}")


if __name__ == "__main__":
    main()