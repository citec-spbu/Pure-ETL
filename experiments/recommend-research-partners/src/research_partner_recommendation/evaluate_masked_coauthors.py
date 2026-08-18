from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from research_partner_recommendation.build_tfidf_profiles import (
    create_vectorizer,
)


DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-small"


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(value.split())


def publication_text(
    row: dict[str, str],
    *,
    include_abstract: bool,
) -> str:
    parts = [
        clean_text(row.get("publication_title")),
        clean_text(row.get("keywords")),
    ]

    if include_abstract:
        parts.append(
            clean_text(row.get("abstract"))
        )

    return ". ".join(
        part
        for part in parts
        if part
    )


def embedding_publication_text(
    row: dict[str, str],
    *,
    include_abstract: bool,
) -> str:
    text = publication_text(
        row,
        include_abstract=include_abstract,
    )

    return f"query: {text}"


def load_data(
    path: Path,
) -> tuple[
    dict[str, dict[str, str]],
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, str],
]:
    publication_rows: dict[
        str,
        dict[str, str],
    ] = {}

    researcher_publications: dict[
        str,
        set[str],
    ] = defaultdict(set)

    publication_researchers: dict[
        str,
        set[str],
    ] = defaultdict(set)

    researcher_names: dict[
        str,
        str,
    ] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            researcher_id = clean_text(
                row.get("researcher_id")
            )

            publication_id = clean_text(
                row.get("publication_id")
            )

            researcher_name = clean_text(
                row.get("researcher_name")
            )

            if not researcher_id or not publication_id:
                continue

            publication_rows.setdefault(
                publication_id,
                row,
            )

            researcher_publications[
                researcher_id
            ].add(publication_id)

            publication_researchers[
                publication_id
            ].add(researcher_id)

            if researcher_name:
                researcher_names[
                    researcher_id
                ] = researcher_name

    return (
        publication_rows,
        researcher_publications,
        publication_researchers,
        researcher_names,
    )


def build_coauthor_pairs(
    publication_researchers: dict[
        str,
        set[str],
    ],
) -> dict[
    tuple[str, str],
    set[str],
]:
    """
    Map each coauthor pair to all publications
    shared by that pair
    """
    pairs: dict[
        tuple[str, str],
        set[str],
    ] = defaultdict(set)

    for publication_id, researchers in (
        publication_researchers.items()
    ):
        researcher_ids = sorted(researchers)

        for i in range(
            len(researcher_ids)
        ):
            for j in range(
                i + 1,
                len(researcher_ids),
            ):
                pair = (
                    researcher_ids[i],
                    researcher_ids[j],
                )

                pairs[pair].add(
                    publication_id
                )

    return pairs


def eligible_pairs(
    pairs: dict[
        tuple[str, str],
        set[str],
    ],
    researcher_publications: dict[
        str,
        set[str],
    ],
) -> list[
    tuple[str, str, set[str]]
]:
    result = []

    for (
        researcher_a,
        researcher_b,
    ), shared_publications in pairs.items():
        remaining_a = (
            researcher_publications[
                researcher_a
            ]
            - shared_publications
        )

        remaining_b = (
            researcher_publications[
                researcher_b
            ]
            - shared_publications
        )

        if remaining_a and remaining_b:
            result.append(
                (
                    researcher_a,
                    researcher_b,
                    shared_publications,
                )
            )

    result.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return result


def build_profile_texts(
    researcher_ids: list[str],
    researcher_publications: dict[
        str,
        set[str],
    ],
    publication_rows: dict[
        str,
        dict[str, str],
    ],
    hidden_publications: set[str],
    *,
    include_abstract: bool,
) -> list[str]:
    """
    Build researcher profiles while excluding
    the held-out publications globally
    """
    texts = []

    for researcher_id in researcher_ids:
        publication_ids = sorted(
            researcher_publications[
                researcher_id
            ]
            - hidden_publications
        )

        parts = [
            publication_text(
                publication_rows[
                    publication_id
                ],
                include_abstract=(
                    include_abstract
                ),
            )
            for publication_id in publication_ids
        ]

        texts.append(
            " ".join(
                part
                for part in parts
                if part
            )
        )

    return texts


def build_known_coauthors(
    researcher_id: str,
    researcher_publications: dict[
        str,
        set[str],
    ],
    publication_researchers: dict[
        str,
        set[str],
    ],
    hidden_publications: set[str],
) -> set[str]:
    """
    Coauthors visible after the held-out publications
    have been removed
    """
    coauthors: set[str] = set()

    visible_publications = (
        researcher_publications[
            researcher_id
        ]
        - hidden_publications
    )

    for publication_id in visible_publications:
        coauthors.update(
            publication_researchers[
                publication_id
            ]
        )

    coauthors.discard(
        researcher_id
    )

    return coauthors


def normalize_vector(
    vector: np.ndarray,
) -> np.ndarray:
    norm = np.linalg.norm(vector)

    if norm > 0:
        return vector / norm

    return vector


def aggregate_embedding(
    researcher_id: str,
    researcher_publications: dict[
        str,
        set[str],
    ],
    publication_index: dict[str, int],
    publication_embeddings: np.ndarray,
    hidden_publications: set[str],
) -> np.ndarray:
    publication_ids = sorted(
        researcher_publications[
            researcher_id
        ]
        - hidden_publications
    )

    indices = [
        publication_index[
            publication_id
        ]
        for publication_id in publication_ids
    ]

    vectors = publication_embeddings[
        indices
    ]

    mean_vector = vectors.mean(
        axis=0
    )

    return normalize_vector(
        mean_vector
    )


def build_embedding_matrix(
    researcher_ids: list[str],
    researcher_publications: dict[
        str,
        set[str],
    ],
    publication_index: dict[str, int],
    publication_embeddings: np.ndarray,
    hidden_publications: set[str],
) -> tuple[
    np.ndarray,
    set[str],
]:
    """
    Aggregate publication embeddings into researcher
    embeddings for the current masked evaluation
    """
    dimension = (
        publication_embeddings.shape[1]
    )

    matrix = np.zeros(
        (
            len(researcher_ids),
            dimension,
        ),
        dtype=np.float32,
    )

    valid_researchers: set[str] = set()

    for index, researcher_id in enumerate(
        researcher_ids
    ):
        remaining = (
            researcher_publications[
                researcher_id
            ]
            - hidden_publications
        )

        if not remaining:
            continue

        matrix[index] = aggregate_embedding(
            researcher_id,
            researcher_publications,
            publication_index,
            publication_embeddings,
            hidden_publications,
        )

        valid_researchers.add(
            researcher_id
        )

    return (
        matrix,
        valid_researchers,
    )


def target_rank(
    similarities: np.ndarray,
    *,
    source_id: str,
    target_id: str,
    researcher_ids: list[str],
    researcher_index: dict[str, int],
    valid_researchers: set[str],
    known_coauthors: set[str],
) -> tuple[int, int]:
    """
    Rank the hidden target among all eligible
    recommendation candidates
    """
    candidates = []

    source_index = researcher_index[
        source_id
    ]

    for candidate_id in researcher_ids:
        if candidate_id == source_id:
            continue

        if candidate_id not in valid_researchers:
            continue

        if candidate_id in known_coauthors:
            continue

        candidate_index = researcher_index[
            candidate_id
        ]

        score = float(
            similarities[
                source_index,
                candidate_index,
            ]
        )

        candidates.append(
            (
                candidate_id,
                score,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[1],
            item[0],
        )
    )

    for rank, (
        candidate_id,
        _,
    ) in enumerate(
        candidates,
        start=1,
    ):
        if candidate_id == target_id:
            return (
                rank,
                len(candidates),
            )

    raise RuntimeError(
        "Скрытый соавтор отсутствует "
        "в списке кандидатов"
    )


def result_row(
    *,
    method: str,
    profile: str,
    source_id: str,
    target_id: str,
    researcher_names: dict[str, str],
    shared_publication_count: int,
    source_remaining_publications: int,
    target_remaining_publications: int,
    rank: int,
    candidate_count: int,
) -> dict[str, object]:
    return {
        "method": method,
        "profile": profile,
        "source_researcher_id": (
            source_id
        ),
        "source_researcher_name": (
            researcher_names.get(
                source_id,
                "",
            )
        ),
        "target_researcher_id": (
            target_id
        ),
        "target_researcher_name": (
            researcher_names.get(
                target_id,
                "",
            )
        ),
        "shared_publication_count": (
            shared_publication_count
        ),
        "source_remaining_publications": (
            source_remaining_publications
        ),
        "target_remaining_publications": (
            target_remaining_publications
        ),
        "candidate_count": (
            candidate_count
        ),
        "target_rank": rank,
        "hit_at_5": int(
            rank <= 5
        ),
        "hit_at_10": int(
            rank <= 10
        ),
        "reciprocal_rank": (
            f"{1 / rank:.8f}"
        ),
    }


def evaluate_direction(
    *,
    method: str,
    profile: str,
    source_id: str,
    target_id: str,
    similarities: np.ndarray,
    researcher_ids: list[str],
    researcher_index: dict[str, int],
    valid_researchers: set[str],
    known_coauthors: set[str],
    researcher_names: dict[str, str],
    researcher_publications: dict[
        str,
        set[str],
    ],
    hidden_publications: set[str],
) -> dict[str, object]:
    rank, candidate_count = target_rank(
        similarities,
        source_id=source_id,
        target_id=target_id,
        researcher_ids=researcher_ids,
        researcher_index=researcher_index,
        valid_researchers=valid_researchers,
        known_coauthors=known_coauthors,
    )

    source_remaining = len(
        researcher_publications[
            source_id
        ]
        - hidden_publications
    )

    target_remaining = len(
        researcher_publications[
            target_id
        ]
        - hidden_publications
    )

    return result_row(
        method=method,
        profile=profile,
        source_id=source_id,
        target_id=target_id,
        researcher_names=researcher_names,
        shared_publication_count=len(
            hidden_publications
        ),
        source_remaining_publications=(
            source_remaining
        ),
        target_remaining_publications=(
            target_remaining
        ),
        rank=rank,
        candidate_count=candidate_count,
    )


def evaluate_pair(
    researcher_a: str,
    researcher_b: str,
    hidden_publications: set[str],
    *,
    researcher_ids: list[str],
    researcher_index: dict[str, int],
    researcher_publications: dict[
        str,
        set[str],
    ],
    publication_researchers: dict[
        str,
        set[str],
    ],
    publication_rows: dict[
        str,
        dict[str, str],
    ],
    researcher_names: dict[str, str],
    publication_index: dict[str, int],
    core_publication_embeddings: np.ndarray,
    full_publication_embeddings: np.ndarray,
) -> list[dict[str, object]]:
    rows: list[
        dict[str, object]
    ] = []

    known_a = build_known_coauthors(
        researcher_a,
        researcher_publications,
        publication_researchers,
        hidden_publications,
    )

    known_b = build_known_coauthors(
        researcher_b,
        researcher_publications,
        publication_researchers,
        hidden_publications,
    )

    # ---------- TF-IDF ----------

    for profile, include_abstract in (
        ("core", False),
        ("full", True),
    ):
        texts = build_profile_texts(
            researcher_ids,
            researcher_publications,
            publication_rows,
            hidden_publications,
            include_abstract=(
                include_abstract
            ),
        )

        vectorizer = create_vectorizer(
            min_df=2,
            max_df=0.95,
            max_features=10000,
        )

        matrix = vectorizer.fit_transform(
            texts
        )

        valid_researchers = {
            researcher_id
            for researcher_id, text
            in zip(
                researcher_ids,
                texts,
            )
            if text.strip()
        }

        similarities = cosine_similarity(
            matrix,
            dense_output=True,
        )

        rows.append(
            evaluate_direction(
                method="tfidf",
                profile=profile,
                source_id=researcher_a,
                target_id=researcher_b,
                similarities=similarities,
                researcher_ids=researcher_ids,
                researcher_index=researcher_index,
                valid_researchers=(
                    valid_researchers
                ),
                known_coauthors=known_a,
                researcher_names=(
                    researcher_names
                ),
                researcher_publications=(
                    researcher_publications
                ),
                hidden_publications=(
                    hidden_publications
                ),
            )
        )

        rows.append(
            evaluate_direction(
                method="tfidf",
                profile=profile,
                source_id=researcher_b,
                target_id=researcher_a,
                similarities=similarities,
                researcher_ids=researcher_ids,
                researcher_index=researcher_index,
                valid_researchers=(
                    valid_researchers
                ),
                known_coauthors=known_b,
                researcher_names=(
                    researcher_names
                ),
                researcher_publications=(
                    researcher_publications
                ),
                hidden_publications=(
                    hidden_publications
                ),
            )
        )

    # ---------- EMBEDDINGS ----------

    for (
        profile,
        publication_embeddings,
    ) in (
        (
            "core",
            core_publication_embeddings,
        ),
        (
            "full",
            full_publication_embeddings,
        ),
    ):
        (
            matrix,
            valid_researchers,
        ) = build_embedding_matrix(
            researcher_ids,
            researcher_publications,
            publication_index,
            publication_embeddings,
            hidden_publications,
        )

        similarities = (
            matrix @ matrix.T
        )

        rows.append(
            evaluate_direction(
                method="embedding",
                profile=profile,
                source_id=researcher_a,
                target_id=researcher_b,
                similarities=similarities,
                researcher_ids=researcher_ids,
                researcher_index=researcher_index,
                valid_researchers=(
                    valid_researchers
                ),
                known_coauthors=known_a,
                researcher_names=(
                    researcher_names
                ),
                researcher_publications=(
                    researcher_publications
                ),
                hidden_publications=(
                    hidden_publications
                ),
            )
        )

        rows.append(
            evaluate_direction(
                method="embedding",
                profile=profile,
                source_id=researcher_b,
                target_id=researcher_a,
                similarities=similarities,
                researcher_ids=researcher_ids,
                researcher_index=researcher_index,
                valid_researchers=(
                    valid_researchers
                ),
                known_coauthors=known_b,
                researcher_names=(
                    researcher_names
                ),
                researcher_publications=(
                    researcher_publications
                ),
                hidden_publications=(
                    hidden_publications
                ),
            )
        )

    return rows


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    fieldnames = [
        "method",
        "profile",
        "source_researcher_id",
        "source_researcher_name",
        "target_researcher_id",
        "target_researcher_name",
        "shared_publication_count",
        "source_remaining_publications",
        "target_remaining_publications",
        "candidate_count",
        "target_rank",
        "hit_at_5",
        "hit_at_10",
        "reciprocal_rank",
    ]

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def calculate_statistics(
    rows: list[dict[str, object]],
    *,
    method: str,
    profile: str,
) -> dict[str, float]:
    selected = [
        row
        for row in rows
        if row["method"] == method
        and row["profile"] == profile
    ]

    ranks = [
        int(row["target_rank"])
        for row in selected
    ]

    hit_5 = [
        int(row["hit_at_5"])
        for row in selected
    ]

    hit_10 = [
        int(row["hit_at_10"])
        for row in selected
    ]

    reciprocal_ranks = [
        float(
            row["reciprocal_rank"]
        )
        for row in selected
    ]

    return {
        "cases": float(
            len(selected)
        ),
        "hit_at_5": mean(
            hit_5
        ),
        "hit_at_10": mean(
            hit_10
        ),
        "mrr": mean(
            reciprocal_ranks
        ),
        "mean_rank": mean(
            ranks
        ),
        "median_rank": median(
            ranks
        ),
    }


def write_report(
    path: Path,
    rows: list[dict[str, object]],
    *,
    total_pairs: int,
    eligible_pair_count: int,
    researcher_count: int,
    model_name: str,
) -> None:
    lines = [
        "# Оценка восстановления скрытых связей соавторства",
        "",
        "## Метод",
        "",
        (
            "Для каждой тестируемой пары все её "
            "совместные публикации временно исключаются "
            "из данных, после чего оценивается ранг "
            "скрытого соавтора"
        ),
        "",
        f"- Embedding-модель: `{model_name}`",
        (
            "- Всего связей соавторства: "
            f"**{total_pairs}**"
        ),
        (
            "- Подходящих тестовых пар: "
            f"**{eligible_pair_count}**"
        ),
        (
            "- Направленных тестовых случаев: "
            f"**{eligible_pair_count * 2}**"
        ),
        (
            "- Исследователей в исходных профилях: "
            f"**{researcher_count}**"
        ),
        "",
        "## Результаты",
        "",
        (
            "| Метод | Профиль | Hit@5 | "
            "Hit@10 | MRR | Median rank |"
        ),
        (
            "|---|---|---:|---:|---:|---:|"
        ),
    ]

    for method in (
        "tfidf",
        "embedding",
    ):
        for profile in (
            "core",
            "full",
        ):
            stats = calculate_statistics(
                rows,
                method=method,
                profile=profile,
            )

            lines.append(
                "| "
                f"{method} | "
                f"{profile} | "
                f"{stats['hit_at_5']:.2%} | "
                f"{stats['hit_at_10']:.2%} | "
                f"{stats['mrr']:.4f} | "
                f"{stats['median_rank']:.1f} |"
            )

    lines.append("")

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Оценить TF-IDF и semantic embeddings "
            "через восстановление скрытых "
            "соавторских связей"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "output/"
            "researcher_publications.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "output/"
            "masked_coauthor_evaluation.csv"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/"
            "masked_coauthor_evaluation_summary.md"
        ),
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
    )

    args = parser.parse_args()

    (
        publication_rows,
        researcher_publications,
        publication_researchers,
        researcher_names,
    ) = load_data(
        args.input
    )

    pairs = build_coauthor_pairs(
        publication_researchers
    )

    test_pairs = eligible_pairs(
        pairs,
        researcher_publications,
    )

    researcher_ids = sorted(
        researcher_publications
    )

    researcher_index = {
        researcher_id: index
        for index, researcher_id
        in enumerate(researcher_ids)
    }

    publication_ids = sorted(
        publication_rows
    )

    publication_index = {
        publication_id: index
        for index, publication_id
        in enumerate(publication_ids)
    }

    print(
        f"Всего связей соавторства: "
        f"{len(pairs)}"
    )

    print(
        f"Подходящих тестовых пар: "
        f"{len(test_pairs)}"
    )

    print(
        f"Направленных тестовых случаев: "
        f"{len(test_pairs) * 2}"
    )

    print(
        f"Загружается модель: "
        f"{args.model}"
    )

    model = SentenceTransformer(
        args.model
    )

    core_texts = [
        embedding_publication_text(
            publication_rows[
                publication_id
            ],
            include_abstract=False,
        )
        for publication_id
        in publication_ids
    ]

    full_texts = [
        embedding_publication_text(
            publication_rows[
                publication_id
            ],
            include_abstract=True,
        )
        for publication_id
        in publication_ids
    ]

    core_publication_embeddings = (
        model.encode(
            core_texts,
            batch_size=args.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    )

    full_publication_embeddings = (
        model.encode(
            full_texts,
            batch_size=args.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    )

    rows: list[
        dict[str, object]
    ] = []

    for pair_index, (
        researcher_a,
        researcher_b,
        shared_publications,
    ) in enumerate(
        test_pairs,
        start=1,
    ):
        rows.extend(
            evaluate_pair(
                researcher_a,
                researcher_b,
                shared_publications,
                researcher_ids=(
                    researcher_ids
                ),
                researcher_index=(
                    researcher_index
                ),
                researcher_publications=(
                    researcher_publications
                ),
                publication_researchers=(
                    publication_researchers
                ),
                publication_rows=(
                    publication_rows
                ),
                researcher_names=(
                    researcher_names
                ),
                publication_index=(
                    publication_index
                ),
                core_publication_embeddings=(
                    core_publication_embeddings
                ),
                full_publication_embeddings=(
                    full_publication_embeddings
                ),
            )
        )

        if (
            pair_index % 10 == 0
            or pair_index
            == len(test_pairs)
        ):
            print(
                f"Обработано пар: "
                f"{pair_index}/"
                f"{len(test_pairs)}"
            )

    write_csv(
        args.output,
        rows,
    )

    write_report(
        args.report,
        rows,
        total_pairs=len(pairs),
        eligible_pair_count=len(
            test_pairs
        ),
        researcher_count=len(
            researcher_ids
        ),
        model_name=args.model,
    )

    print(
        f"Строк оценки: "
        f"{len(rows)}"
    )

    print(
        f"CSV сохранён: "
        f"{args.output}"
    )

    print(
        f"Отчёт сохранён: "
        f"{args.report}"
    )


if __name__ == "__main__":
    main()