from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer


EXPERIMENT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_FILE = (
    EXPERIMENT_DIR
    / "output"
    / "researcher_profiles.csv"
)

DEFAULT_OUTPUT_FILE = (
    EXPERIMENT_DIR
    / "output"
    / "researcher_tfidf_terms.csv"
)

DEFAULT_REPORT_FILE = (
    EXPERIMENT_DIR
    / "reports"
    / "tfidf_profiles_summary.md"
)

REQUIRED_COLUMNS = {
    "researcher_id",
    "researcher_name",
    "publication_count",
    "titles",
    "keywords",
    "abstracts",
}

STOP_WORDS = {
    # Russian
    "а",
    "без",
    "был",
    "была",
    "были",
    "было",
    "в",
    "во",
    "для",
    "до",
    "его",
    "ее",
    "её",
    "и",
    "из",
    "или",
    "их",
    "к",
    "как",
    "на",
    "не",
    "но",
    "о",
    "об",
    "от",
    "по",
    "при",
    "с",
    "со",
    "у",
    "что",
    "это",

    # English
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

BIBLIOGRAPHIC_STOP_WORDS = {
    # English bibliographic markers
    "isbn",
    "issn",
    "pp",
    "vol",
    "volume",
    "ed",
    "eds",
    "edition",

    # Russian bibliographic / review markers
    "рец",
    "рецензия",
    "рецензии",
    "кн",
}

ALL_STOP_WORDS = (
    STOP_WORDS
    | BIBLIOGRAPHIC_STOP_WORDS
)

@dataclass(frozen=True)
class ResearcherProfile:
    researcher_id: str
    researcher_name: str
    publication_count: int
    titles: str
    keywords: str
    abstracts: str

    @property
    def core_text(self) -> str:
        return " ".join(
            part
            for part in (
                self.titles,
                self.keywords,
            )
            if part
        )

    @property
    def full_text(self) -> str:
        return " ".join(
            part
            for part in (
                self.titles,
                self.keywords,
                self.abstracts,
            )
            if part
        )

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Построить TF-IDF-представления "
            "публикационных профилей исследователей"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_FILE,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_FILE,
    )

    parser.add_argument(
        "--min-df",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--max-df",
        type=float,
        default=0.95,
    )

    parser.add_argument(
        "--max-features",
        type=int,
        default=10_000,
    )

    parser.add_argument(
        "--top-terms",
        type=int,
        default=15,
    )

    return parser.parse_args()


def load_profiles(
    input_file: Path,
) -> list[ResearcherProfile]:
    if not input_file.exists():
        raise FileNotFoundError(
            f"Файл не найден: {input_file}\n"
            "Сначала запусти build-researcher-profiles"
        )

    profiles: list[ResearcherProfile] = []

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
            raise ValueError(
                "Отсутствуют поля: "
                + ", ".join(sorted(missing_columns))
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            researcher_id = row.get(
                "researcher_id",
                "",
            ).strip()

            if not researcher_id:
                raise ValueError(
                    f"Пустой researcher_id в строке {row_number}"
                )

            publication_count_text = row.get(
                "publication_count",
                "",
            ).strip()

            try:
                publication_count = int(
                    publication_count_text
                )
            except ValueError as error:
                raise ValueError(
                    "Некорректный publication_count "
                    f"в строке {row_number}: "
                    f"{publication_count_text!r}"
                ) from error

            profiles.append(
                ResearcherProfile(
                    researcher_id=researcher_id,
                    researcher_name=row.get(
                        "researcher_name",
                        "",
                    ).strip(),
                    publication_count=publication_count,
                    titles=row.get(
    			"titles",
   			 "",
		).strip(),
		keywords=row.get(
   		 "keywords",
   		 "",
		).strip(),
		abstracts=row.get(
    			"abstracts",
    			"",
		).strip(),
                )
            )

    if not profiles:
        raise ValueError(
            "Таблица не содержит профилей"
        )

    return profiles


def create_vectorizer(
    *,
    min_df: int,
    max_df: float,
    max_features: int,
) -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
        lowercase=True,
        stop_words=list(ALL_STOP_WORDS),
	token_pattern=r"(?u)\b[^\W\d_]{2,}\b",
        norm="l2",
        use_idf=True,
        smooth_idf=True,
        sublinear_tf=True,
    )

def fit_vectorizer(
    texts: list[str],
    *,
    min_df: int,
    max_df: float,
    max_features: int,
) -> tuple[TfidfVectorizer, Any]:
    if not any(texts):
        raise ValueError(
            "Все тексты корпуса пустые"
        )

    vectorizer = create_vectorizer(
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
    )

    matrix = vectorizer.fit_transform(texts)

    if matrix.shape[1] == 0:
        raise ValueError(
            "После фильтрации не осталось признаков"
        )

    return vectorizer, matrix


def get_top_terms(
    matrix: Any,
    feature_names: list[str],
    row_index: int,
    limit: int,
) -> list[tuple[str, float]]:
    row = matrix.getrow(row_index)

    terms = [
        (
            feature_names[index],
            float(weight),
        )
        for index, weight in zip(
            row.indices,
            row.data,
        )
    ]

    terms.sort(
        key=lambda item: (
            -item[1],
            item[0],
        )
    )

    return terms[:limit]


def format_terms(
    terms: list[tuple[str, float]],
) -> str:
    return "; ".join(
        f"{term} ({weight:.4f})"
        for term, weight in terms
    )


def get_nonzero_counts(
    matrix: Any,
) -> list[int]:
    return [
        int(matrix.getrow(index).nnz)
        for index in range(matrix.shape[0])
    ]


def matrix_density(
    matrix: Any,
) -> float:
    total_cells = (
        matrix.shape[0]
        * matrix.shape[1]
    )

    if total_cells == 0:
        return 0.0

    return (
        matrix.nnz
        / total_cells
        * 100
    )


def get_global_top_terms(
    matrix: Any,
    feature_names: list[str],
    limit: int = 20,
) -> list[tuple[str, float]]:
    mean_weights = (
        matrix.mean(axis=0)
        .A1
    )

    terms = [
        (
            feature_names[index],
            float(weight),
        )
        for index, weight in enumerate(
            mean_weights
        )
        if weight > 0
    ]

    terms.sort(
        key=lambda item: (
            -item[1],
            item[0],
        )
    )

    return terms[:limit]


def build_result_rows(
    profiles: list[ResearcherProfile],
    core_matrix: Any,
    core_features: list[str],
    full_matrix: Any,
    full_features: list[str],
    top_terms_limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for index, profile in enumerate(profiles):
        core_terms = get_top_terms(
            core_matrix,
            core_features,
            index,
            top_terms_limit,
        )

        full_terms = get_top_terms(
            full_matrix,
            full_features,
            index,
            top_terms_limit,
        )

        rows.append(
            {
                "researcher_id": profile.researcher_id,
                "researcher_name": profile.researcher_name,
                "publication_count": profile.publication_count,
                "core_nonzero_features": int(
                    core_matrix.getrow(index).nnz
                ),
                "core_top_terms": format_terms(
                    core_terms
                ),
                "full_nonzero_features": int(
                    full_matrix.getrow(index).nnz
                ),
                "full_top_terms": format_terms(
                    full_terms
                ),
            }
        )

    return rows


def write_result_csv(
    output_file: Path,
    rows: list[dict[str, Any]],
) -> None:
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "researcher_id",
        "researcher_name",
        "publication_count",
        "core_nonzero_features",
        "core_top_terms",
        "full_nonzero_features",
        "full_top_terms",
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
    *,
    input_file: Path,
    output_file: Path,
    profiles: list[ResearcherProfile],
    core_matrix: Any,
    core_features: list[str],
    full_matrix: Any,
    full_features: list[str],
    min_df: int,
    max_df: float,
    max_features: int,
) -> str:
    core_counts = get_nonzero_counts(
        core_matrix
    )

    full_counts = get_nonzero_counts(
        full_matrix
    )

    core_zero_profiles = sum(
        count == 0
        for count in core_counts
    )

    full_zero_profiles = sum(
        count == 0
        for count in full_counts
    )

    core_vocabulary = set(
        core_features
    )

    full_vocabulary = set(
        full_features
    )

    common_features = (
        core_vocabulary
        & full_vocabulary
    )

    core_global_terms = get_global_top_terms(
        core_matrix,
        core_features,
    )

    full_global_terms = get_global_top_terms(
        full_matrix,
        full_features,
    )

    lines = [
        "# Отчёт о TF-IDF-векторизации",
        "",
        "## Файлы",
        "",
        f"- Исходные профили: `{input_file}`",
        f"- Таблица терминов: `{output_file}`",
        "",
        "## Параметры",
        "",
        "- Анализатор: **слова**",
        "- N-граммы: **униграммы и биграммы**",
        f"- `min_df`: **{min_df}**",
        f"- `max_df`: **{max_df}**",
        f"- `max_features`: **{max_features}**",
        "- Нормализация: **L2**",
        "- Сублинейное масштабирование TF: **включено**",
        "- Стоп-слова: **используются**",
	"- Чисто цифровые токены: **исключены**",
        "",
        "## Общая статистика",
        "",
        f"- Профилей: **{len(profiles)}**",
        "",
        "## Core-профили",
        "",
        (
            "- Размер матрицы: "
            f"**{core_matrix.shape[0]} × "
            f"{core_matrix.shape[1]}**"
        ),
        (
            "- Размер словаря: "
            f"**{len(core_features)}**"
        ),
        (
            "- Ненулевых значений: "
            f"**{core_matrix.nnz}**"
        ),
        (
            "- Плотность матрицы: "
            f"**{matrix_density(core_matrix):.4f}%**"
        ),
        (
            "- Профилей с нулевым вектором: "
            f"**{core_zero_profiles}**"
        ),
        (
            "- Среднее число ненулевых признаков: "
            f"**{mean(core_counts):.2f}**"
        ),
        (
            "- Медианное число ненулевых признаков: "
            f"**{median(core_counts):.2f}**"
        ),
        "",
        "## Full-профили",
        "",
        (
            "- Размер матрицы: "
            f"**{full_matrix.shape[0]} × "
            f"{full_matrix.shape[1]}**"
        ),
        (
            "- Размер словаря: "
            f"**{len(full_features)}**"
        ),
        (
            "- Ненулевых значений: "
            f"**{full_matrix.nnz}**"
        ),
        (
            "- Плотность матрицы: "
            f"**{matrix_density(full_matrix):.4f}%**"
        ),
        (
            "- Профилей с нулевым вектором: "
            f"**{full_zero_profiles}**"
        ),
        (
            "- Среднее число ненулевых признаков: "
            f"**{mean(full_counts):.2f}**"
        ),
        (
            "- Медианное число ненулевых признаков: "
            f"**{median(full_counts):.2f}**"
        ),
        "",
        "## Сравнение словарей",
        "",
        (
            "- Общих признаков: "
            f"**{len(common_features)}**"
        ),
        (
            "- Только в core: "
            f"**{len(core_vocabulary - full_vocabulary)}**"
        ),
        (
            "- Только в full: "
            f"**{len(full_vocabulary - core_vocabulary)}**"
        ),
        "",
        "## Наиболее заметные core-термины",
        "",
    ]

    for term, weight in core_global_terms:
        lines.append(
            f"- `{term}`: {weight:.6f}"
        )

    lines.extend(
        [
            "",
            "## Наиболее заметные full-термины",
            "",
        ]
    )

    for term, weight in full_global_terms:
        lines.append(
            f"- `{term}`: {weight:.6f}"
        )

    lines.extend(
        [
            "",
            "## Интерпретация",
            "",
            (
                "TF-IDF представляет каждый профиль "
                "исследователя как разреженный числовой вектор"
            ),
            "",
            (
                "Core-профиль использует названия публикаций "
                "и ключевые слова"
            ),
            "",
            (
                "Full-профиль дополнительно содержит "
                "аннотации публикаций"
            ),
            "",
            (
                "На следующем этапе TF-IDF-векторы могут "
                "использоваться для расчёта косинусного "
                "сходства между исследователями"
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    args = parse_arguments()

    input_file = args.input.resolve()
    output_file = args.output.resolve()
    report_file = args.report.resolve()

    profiles = load_profiles(
        input_file
    )

    core_texts = [
        profile.core_text
        for profile in profiles
    ]

    full_texts = [
        profile.full_text
        for profile in profiles
    ]

    core_vectorizer, core_matrix = (
        fit_vectorizer(
            core_texts,
            min_df=args.min_df,
            max_df=args.max_df,
            max_features=args.max_features,
        )
    )

    full_vectorizer, full_matrix = (
        fit_vectorizer(
            full_texts,
            min_df=args.min_df,
            max_df=args.max_df,
            max_features=args.max_features,
        )
    )

    core_features = (
        core_vectorizer
        .get_feature_names_out()
        .tolist()
    )

    full_features = (
        full_vectorizer
        .get_feature_names_out()
        .tolist()
    )

    rows = build_result_rows(
        profiles,
        core_matrix,
        core_features,
        full_matrix,
        full_features,
        args.top_terms,
    )

    write_result_csv(
        output_file,
        rows,
    )

    report = build_report(
        input_file=input_file,
        output_file=output_file,
        profiles=profiles,
        core_matrix=core_matrix,
        core_features=core_features,
        full_matrix=full_matrix,
        full_features=full_features,
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features,
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
    print(f"Профилей прочитано: {len(profiles)}")

    print(
        "Core TF-IDF-матрица: "
        f"{core_matrix.shape[0]} × "
        f"{core_matrix.shape[1]}"
    )

    print(
        "Full TF-IDF-матрица: "
        f"{full_matrix.shape[0]} × "
        f"{full_matrix.shape[1]}"
    )

    print(f"CSV сохранён: {output_file}")
    print(f"Отчёт сохранён: {report_file}")


if __name__ == "__main__":
    main()