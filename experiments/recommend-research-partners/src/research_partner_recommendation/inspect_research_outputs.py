from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


# Текущий файл расположен в:
# experiments/recommend-research-partners/src/
# research_partner_recommendation/inspect_research_outputs.py
EXPERIMENT_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]

DEFAULT_DATA_FILE = REPOSITORY_ROOT / "Data" / "research-outputs.json"
DEFAULT_REPORT_FILE = (
    EXPERIMENT_DIR
    / "reports"
    / "research_outputs_structure.md"
)


def parse_arguments() -> argparse.Namespace:
    """Прочитать аргументы кс"""

    parser = argparse.ArgumentParser(
        description=(
            "Исследовать верхнеуровневую структуру "
            "файла research-outputs.json."
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


def describe_value(value: Any) -> str:
    """Вернуть текстовое описание JSON-значения"""

    if value is None:
        return "null"

    if isinstance(value, dict):
        keys = list(value.keys())
        preview = ", ".join(str(key) for key in keys[:10])

        return f"object; keys: {preview or 'none'}"

    if isinstance(value, list):
        if not value:
            return "empty list"

        return (
            f"list with {len(value)} item(s); "
            f"first item type: {type(value[0]).__name__}"
        )

    preview = str(value).replace("\n", " ")[:100]

    return f"{type(value).__name__}: {preview}"


def find_records(data: Any) -> tuple[list[Any], str]:
    """
    Найти массив публикаций в корневой структуре JSON

    Файл может содержать массив непосредственно в корне либо
    хранить его в одном из распространённых полей
    """

    if isinstance(data, list):
        return data, "root list"

    if not isinstance(data, dict):
        raise TypeError(
            "Корневой элемент JSON должен быть массивом или объектом"
        )

    possible_container_keys = (
        "items",
        "results",
        "researchOutputs",
        "research_outputs",
    )

    for key in possible_container_keys:
        value = data.get(key)

        if isinstance(value, list):
            return value, f'field "{key}"'

    list_fields = [
        (key, value)
        for key, value in data.items()
        if isinstance(value, list)
    ]

    if len(list_fields) == 1:
        key, records = list_fields[0]
        return records, f'field "{key}"'

    available_keys = ", ".join(str(key) for key in data.keys())

    raise ValueError(
        "Не удалось однозначно определить массив публикаций"
        f"Доступные корневые поля: {available_keys}"
    )


def build_report(
    *,
    input_file: Path,
    root_location: str,
    records: list[Any],
) -> str:
    """Сформировать содержимое Markdown-отчёта"""

    lines = [
        "# Исследование структуры research-outputs.json",
        "",
        "## Исходный файл",
        "",
        f"`{input_file}`",
        "",
        "## Общая информация",
        "",
        f"- Расположение массива записей: `{root_location}`",
        f"- Количество записей: **{len(records)}**",
        "",
    ]

    if not records:
        lines.extend(
            [
                "Файл не содержит публикаций",
                "",
            ]
        )
        return "\n".join(lines)

    object_records = [
        record
        for record in records
        if isinstance(record, dict)
    ]

    lines.extend(
        [
            f"- JSON-объектов: **{len(object_records)}**",
            (
                "- Записей другого типа: "
                f"**{len(records) - len(object_records)}**"
            ),
            "",
        ]
    )

    if not object_records:
        lines.extend(
            [
                "Ни одна запись не является JSON-объектом",
                "",
            ]
        )
        return "\n".join(lines)

    first_record = object_records[0]

    lines.extend(
        [
            "## Поля первой публикации",
            "",
            "| Поле | Описание значения |",
            "|---|---|",
        ]
    )

    for key, value in first_record.items():
        description = describe_value(value).replace("|", "\\|")
        lines.append(f"| `{key}` | {description} |")

    key_frequency: Counter[str] = Counter()

    for record in object_records:
        key_frequency.update(record.keys())

    lines.extend(
        [
            "",
            "## Частота присутствия полей",
            "",
            "| Поле | Записей с полем | Доля |",
            "|---|---:|---:|",
        ]
    )

    total = len(object_records)

    for key, count in key_frequency.most_common():
        percentage = count / total * 100

        lines.append(
            f"| `{key}` | {count} из {total} | "
            f"{percentage:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Следующие действия",
            "",
            "1. Определить поле идентификатора публикации",
            "2. Исследовать структуру авторов",
            "3. Найти названия, аннотации и годы публикаций",
            "4. Найти ключевые слова и классификации",
            "5. Оценить количество пропущенных значений",
            (
                "6. Подготовить таблицу связей "
                "«исследователь — публикация»"
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """Запустить исследование исходного JSON-файла"""

    args = parse_arguments()

    input_file = args.input.resolve()
    output_file = args.output.resolve()

    if not input_file.exists():
        raise FileNotFoundError(
            f"Файл не найден: {input_file}\n"
            "Проверь имя файла и расположение папки Data"
        )

    if not input_file.is_file():
        raise ValueError(
            f"Указанный путь не является файлом: {input_file}"
        )

    try:
        with input_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Не удалось разобрать JSON-файл {input_file}: {error}"
        ) from error

    records, root_location = find_records(data)

    report = build_report(
        input_file=input_file,
        root_location=root_location,
        records=records,
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding="utf-8")

    print(f"Исходный файл: {input_file}")
    print(f"Обработано записей: {len(records)}")
    print(f"Отчёт сохранён: {output_file}")


if __name__ == "__main__":
    main()