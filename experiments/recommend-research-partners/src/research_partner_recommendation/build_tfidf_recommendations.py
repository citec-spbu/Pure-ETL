from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from research_partner_recommendation.build_tfidf_profiles import (
    ALL_STOP_WORDS,
)


EXPERIMENT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_PROFILES_PATH = (
    EXPERIMENT_DIR / "output" / "researcher_profiles.csv"
)

DEFAULT_PUBLICATIONS_PATH = (
    EXPERIMENT_DIR / "output" / "researcher_publications.csv"
)

DEFAULT_OUTPUT_PATH = (
    EXPERIMENT_DIR / "output" / "tfidf_recommendations.csv"
)

DEFAULT_REPORT_PATH = (
    EXPERIMENT_DIR / "reports" / "tfidf_recommendations_summary.md"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Построить рекомендации исследователей на основе TF-IDF"
            
        )
    )

    parser.add_argument(
        "--profiles",
        type=Path,
        default=DEFAULT_PROFILES_PATH,
    )

    parser.add_argument(
        "--publications",
        type=Path,
        default=DEFAULT_PUBLICATIONS_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
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
        "--explanation-terms",
        type=int,
        default=5,
    )

    return parser.parse_args()


def load_profiles(path: Path) -> list[ResearcherProfile]:
    profiles: list[ResearcherProfile] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            researcher_id = row.get(
                "researcher_id",
                "",
            ).strip()

            if not researcher_id:
                continue

            publication_count_raw = row.get(
                "publication_count",
                "0",
            ).strip()

            try:
                publication_count = int(
                    publication_count_raw
                )
            except ValueError:
                publication_count = 0

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

    return profiles


def load_coauthor_pairs(
    path: Path,
) -> dict[str, set[str]]:
    publication_researchers: dict[
        str,
        set[str],
    ] = defaultdict(set)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            researcher_id = row.get(
                "researcher_id",
                "",
            ).strip()

            publication_id = row.get(
                "publication_id",
                "",
            ).strip()

            if not researcher_id or not publication_id:
                continue

            publication_researchers[
                publication_id
            ].add(researcher_id)

    coauthors: dict[str, set[str]] = defaultdict(set)

    for researcher_ids in publication_researchers.values():
        ids = sorted(researcher_ids)

        for researcher_id in ids:
            coauthors[researcher_id].update(
                other_id
                for other_id in ids
                if other_id != researcher_id
            )

    return coauthors


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


def fit_tfidf(
    texts: list[str],
    *,
    min_df: int,
    max_df: float,
    max_features: int,
) -> tuple[
    TfidfVectorizer,
    csr_matrix,
]:
    vectorizer = create_vectorizer(
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
    )

    matrix = vectorizer.fit_transform(texts)

    return vectorizer, matrix.tocsr()


def shared_terms(
    matrix: csr_matrix,
    feature_names: np.ndarray,
    first_index: int,
    second_index: int,
    limit: int,
) -> list[tuple[str, float]]:
    first_row = matrix.getrow(first_index)
    second_row = matrix.getrow(second_index)

    product = first_row.multiply(second_row)

    if product.nnz == 0:
        return []

    pairs = [
        (
            feature_names[index],
            float(value),
        )
        for index, value in zip(
            product.indices,
            product.data,
        )
    ]

    pairs.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return pairs[:limit]


def format_shared_terms(
    terms: list[tuple[str, float]],
) -> str:
    return "; ".join(
        f"{term} ({weight:.4f})"
        for term, weight in terms
    )


def build_recommendations(
    *,
    profiles: list[ResearcherProfile],
    matrix: csr_matrix,
    vectorizer: TfidfVectorizer,
    coauthors: dict[str, set[str]],
    model_name: str,
    top_n: int,
    explanation_terms: int,
) -> tuple[
    list[dict[str, str]],
    list[float],
    int,
]:
    similarities = cosine_similarity(
        matrix,
        dense_output=True,
    )

    feature_names = (
        vectorizer.get_feature_names_out()
    )

    result_rows: list[dict[str, str]] = []
    selected_scores: list[float] = []

    researchers_without_enough_candidates = 0

    for source_index, source in enumerate(profiles):
        candidates: list[tuple[int, float]] = []

        existing_coauthors = coauthors.get(
            source.researcher_id,
            set(),
        )

        for target_index, target in enumerate(profiles):
            if source_index == target_index:
                continue

            if target.researcher_id in existing_coauthors:
                continue

            score = float(
                similarities[
                    source_index,
                    target_index,
                ]
            )

            candidates.append(
                (
                    target_index,
                    score,
                )
            )

        candidates.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        selected = candidates[:top_n]

        if len(selected) < top_n:
            researchers_without_enough_candidates += 1

        for rank, (
            target_index,
            score,
        ) in enumerate(
            selected,
            start=1,
        ):
            target = profiles[target_index]

            terms = shared_terms(
                matrix=matrix,
                feature_names=feature_names,
                first_index=source_index,
                second_index=target_index,
                limit=explanation_terms,
            )

            result_rows.append(
                {
                    "model": model_name,
                    "researcher_id": source.researcher_id,
                    "researcher_name": source.researcher_name,
                    "researcher_publication_count": str(
                        source.publication_count
                    ),
                    "rank": str(rank),
                    "recommended_researcher_id": (
                        target.researcher_id
                    ),
                    "recommended_researcher_name": (
                        target.researcher_name
                    ),
                    "recommended_publication_count": str(
                        target.publication_count
                    ),
                    "similarity": f"{score:.6f}",
                    "shared_terms": format_shared_terms(
                        terms
                    ),
                }
            )

            selected_scores.append(score)

    return (
        result_rows,
        selected_scores,
        researchers_without_enough_candidates,
    )


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "model",
        "researcher_id",
        "researcher_name",
        "researcher_publication_count",
        "rank",
        "recommended_researcher_id",
        "recommended_researcher_name",
        "recommended_publication_count",
        "similarity",
        "shared_terms",
    ]

    with path.open(
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


def score_stats(
    scores: list[float],
) -> tuple[float, float, float, float]:
    if not scores:
        return 0.0, 0.0, 0.0, 0.0

    return (
        min(scores),
        max(scores),
        mean(scores),
        median(scores),
    )


def write_report(
    *,
    path: Path,
    profiles: list[ResearcherProfile],
    coauthors: dict[str, set[str]],
    core_rows: list[dict[str, str]],
    full_rows: list[dict[str, str]],
    core_scores: list[float],
    full_scores: list[float],
    top_n: int,
    core_missing: int,
    full_missing: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    researchers_with_coauthors = sum(
        1
        for profile in profiles
        if coauthors.get(profile.researcher_id)
    )

    coauthor_links = (
        sum(
            len(values)
            for values in coauthors.values()
        )
        // 2
    )

    core_min, core_max, core_mean, core_median = (
        score_stats(core_scores)
    )

    full_min, full_max, full_mean, full_median = (
        score_stats(full_scores)
    )
core_exact_rows = [
    row
    for row in core_rows
    if float(row["similarity"]) >= 0.9999
]

full_exact_rows = [
    row
    for row in full_rows
    if float(row["similarity"]) >= 0.9999
]

core_exact_researchers = {
    row["researcher_id"]
    for row in core_exact_rows
}

full_exact_researchers = {
    row["researcher_id"]
    for row in full_exact_rows
}

    lines = [
        "# Отчёт о TF-IDF-рекомендациях",
        "",
        "## Метод",
        "",
        (
            "Для каждого исследователя рассчитывается "
            "косинусное сходство TF-IDF-профиля "
            "со всеми остальными профилями"
        ),
        "",
        (
            "Сам исследователь и его существующие "
            "соавторы исключаются из списка "
            "потенциальных новых партнёров"
        ),
        "",
        f"- Исследователей: **{len(profiles)}**",
        f"- Top-N: **{top_n}**",
        (
            "- Исследователей хотя бы с одним "
            f"соавтором: **{researchers_with_coauthors}**"
        ),
        (
            "- Уникальных связей соавторства: "
            f"**{coauthor_links}**"
        ),
        "",
        "## Core-рекомендации",
        "",
        (
            f"- Строк рекомендаций: "
            f"**{len(core_rows)}**"
        ),
        (
            "- Минимальное сходство среди Top-N: "
            f"**{core_min:.4f}**"
        ),
        (
            "- Максимальное сходство среди Top-N: "
            f"**{core_max:.4f}**"
        ),
        (
            "- Среднее сходство среди Top-N: "
            f"**{core_mean:.4f}**"
        ),
        (
            "- Медианное сходство среди Top-N: "
            f"**{core_median:.4f}**"
        ),
        (
            "- Профилей, для которых не удалось "
            f"найти {top_n} кандидатов: "
            f"**{core_missing}**"
        ),
	(
    "- Рекомендаций с косинусным сходством "
    "не ниже 0.9999: "
    f"**{len(core_exact_rows)}**"
),
(
    "- Исследователей хотя бы с одной такой "
    "рекомендацией: "
    f"**{len(core_exact_researchers)}**"
),
        "",
        "## Full-рекомендации",
        "",
        (
            f"- Строк рекомендаций: "
            f"**{len(full_rows)}**"
        ),
        (
            "- Минимальное сходство среди Top-N: "
            f"**{full_min:.4f}**"
        ),
        (
            "- Максимальное сходство среди Top-N: "
            f"**{full_max:.4f}**"
        ),
        (
            "- Среднее сходство среди Top-N: "
            f"**{full_mean:.4f}**"
        ),
        (
            "- Медианное сходство среди Top-N: "
            f"**{full_median:.4f}**"
        ),
        (
            "- Профилей, для которых не удалось "
            f"найти {top_n} кандидатов: "
            f"**{full_missing}**"
        ),
        "",
        "## Интерпретация",
        "",
        (
            "Core-модель использует названия "
            "публикаций и ключевые слова"
        ),
        "",
        (
            "Full-модель дополнительно использует "
            "аннотации, когда они доступны"
        ),
        "",
        (
            "Поле `shared_terms` показывает признаки "
            "TF-IDF, которые одновременно присутствуют "
            "в профилях исследователя и рекомендованного "
            "кандидата"
        ),
        "",
        "## Ограничения",
        "",
        (
            "TF-IDF используется как baseline и "
            "оценивает совпадение лексики"
        ),
        "",
    ]

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()

    profiles = load_profiles(args.profiles)

    if not profiles:
        raise ValueError(
            "Не найдено ни одного профиля исследователя"
        )

    coauthors = load_coauthor_pairs(
        args.publications
    )

    core_vectorizer, core_matrix = fit_tfidf(
        [
            profile.core_text
            for profile in profiles
        ],
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features,
    )

    full_vectorizer, full_matrix = fit_tfidf(
        [
            profile.full_text
            for profile in profiles
        ],
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features,
    )

    (
        core_rows,
        core_scores,
        core_missing,
    ) = build_recommendations(
        profiles=profiles,
        matrix=core_matrix,
        vectorizer=core_vectorizer,
        coauthors=coauthors,
        model_name="core",
        top_n=args.top_n,
        explanation_terms=args.explanation_terms,
    )

    (
        full_rows,
        full_scores,
        full_missing,
    ) = build_recommendations(
        profiles=profiles,
        matrix=full_matrix,
        vectorizer=full_vectorizer,
        coauthors=coauthors,
        model_name="full",
        top_n=args.top_n,
        explanation_terms=args.explanation_terms,
    )

    rows = core_rows + full_rows

    write_csv(
        args.output,
        rows,
    )

    write_report(
        path=args.report,
        profiles=profiles,
        coauthors=coauthors,
        core_rows=core_rows,
        full_rows=full_rows,
        core_scores=core_scores,
        full_scores=full_scores,
        top_n=args.top_n,
        core_missing=core_missing,
        full_missing=full_missing,
    )

    print(
        f"Профилей прочитано: {len(profiles)}"
    )

    print(
        f"Core-рекомендаций: {len(core_rows)}"
    )

    print(
        f"Full-рекомендаций: {len(full_rows)}"
    )

    print(
        f"CSV сохранён: {args.output.resolve()}"
    )

    print(
        f"Отчёт сохранён: {args.report.resolve()}"
    )


if __name__ == "__main__":
    main()