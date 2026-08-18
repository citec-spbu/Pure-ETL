from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


def load_coauthors(
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
            researcher_id = (
                row.get("researcher_id") or ""
            ).strip()

            publication_id = (
                row.get("publication_id") or ""
            ).strip()

            if not researcher_id or not publication_id:
                continue

            publication_researchers[
                publication_id
            ].add(researcher_id)

    coauthors: dict[str, set[str]] = defaultdict(set)

    for researcher_ids in publication_researchers.values():
        researcher_ids = sorted(researcher_ids)

        for index, researcher_id in enumerate(
            researcher_ids
        ):
            for coauthor_id in researcher_ids[
                index + 1 :
            ]:
                coauthors[researcher_id].add(
                    coauthor_id
                )
                coauthors[coauthor_id].add(
                    researcher_id
                )

    return coauthors


def build_recommendations(
    embeddings: np.ndarray,
    researcher_ids: list[str],
    researcher_names: list[str],
    publication_counts: np.ndarray,
    coauthors: dict[str, set[str]],
    *,
    model: str,
    top_n: int,
) -> list[dict[str, object]]:
    similarities = embeddings @ embeddings.T

    recommendations: list[
        dict[str, object]
    ] = []

    for researcher_index, researcher_id in enumerate(
        researcher_ids
    ):
        existing_coauthors = coauthors.get(
            researcher_id,
            set(),
        )

        candidates = [
            candidate_index
            for candidate_index in range(
                len(researcher_ids)
            )
            if candidate_index != researcher_index
            and researcher_ids[candidate_index]
            not in existing_coauthors
        ]

        candidates.sort(
            key=lambda candidate_index: (
                -float(
                    similarities[
                        researcher_index,
                        candidate_index,
                    ]
                ),
                researcher_ids[candidate_index],
            )
        )

        selected = candidates[:top_n]

        for rank, candidate_index in enumerate(
            selected,
            start=1,
        ):
            recommendations.append(
                {
                    "model": model,
                    "researcher_id": researcher_id,
                    "researcher_name": (
                        researcher_names[
                            researcher_index
                        ]
                    ),
                    "researcher_publication_count": (
                        int(
                            publication_counts[
                                researcher_index
                            ]
                        )
                    ),
                    "rank": rank,
                    "recommended_researcher_id": (
                        researcher_ids[
                            candidate_index
                        ]
                    ),
                    "recommended_researcher_name": (
                        researcher_names[
                            candidate_index
                        ]
                    ),
                    "recommended_publication_count": (
                        int(
                            publication_counts[
                                candidate_index
                            ]
                        )
                    ),
                    "similarity": (
                        f"{float(similarities[
                            researcher_index,
                            candidate_index
                        ]):.6f}"
                    ),
                }
            )

    return recommendations


def validate_recommendations(
    rows: list[dict[str, object]],
    coauthors: dict[str, set[str]],
) -> None:
    for row in rows:
        researcher_id = str(
            row["researcher_id"]
        )
        recommended_id = str(
            row["recommended_researcher_id"]
        )

        if researcher_id == recommended_id:
            raise RuntimeError(
                "Обнаружена рекомендация исследователя самому себе"
            )

        if recommended_id in coauthors.get(
            researcher_id,
            set(),
        ):
            raise RuntimeError(
                "Обнаружен существующий соавтор среди рекомендаций"
            )


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
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


def write_report(
    path: Path,
    *,
    model_name: str,
    researcher_count: int,
    top_n: int,
    coauthors: dict[str, set[str]],
    core_count: int,
    full_count: int,
) -> None:
    researchers_with_coauthors = sum(
        1
        for values in coauthors.values()
        if values
    )

    coauthor_links = (
        sum(
            len(values)
            for values in coauthors.values()
        )
        // 2
    )

    lines = [
        "# Отчёт о семантических рекомендациях",
        "",
        "## Метод",
        "",
        f"- Модель: `{model_name}`",
        "- Метрика сходства: cosine similarity",
        (
            "- Существующие соавторы "
            "исключаются из рекомендаций"
        ),
        f"- Top-N: **{top_n}**",
        "",
        "## Результат",
        "",
        (
            "- Исследователей: "
            f"**{researcher_count}**"
        ),
        (
            "- Исследователей с существующими "
            f"соавторами: **{researchers_with_coauthors}**"
        ),
        (
            "- Уникальных связей соавторства: "
            f"**{coauthor_links}**"
        ),
        (
            "- Core-рекомендаций: "
            f"**{core_count}**"
        ),
        (
            "- Full-рекомендаций: "
            f"**{full_count}**"
        ),
        "",
    ]

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
            "Рекомендации научных "
            "партнёров на основе embeddings"
        )
    )

    parser.add_argument(
        "--embeddings",
        type=Path,
        default=Path(
            "output/researcher_embeddings.npz"
        ),
    )

    parser.add_argument(
        "--publications",
        type=Path,
        default=Path(
            "output/researcher_publications.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "output/embedding_recommendations.csv"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/"
            "embedding_recommendations_summary.md"
        ),
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    data = np.load(
        args.embeddings,
        allow_pickle=False,
    )

    researcher_ids = (
        data["researcher_ids"]
        .astype(str)
        .tolist()
    )

    researcher_names = (
        data["researcher_names"]
        .astype(str)
        .tolist()
    )

    publication_counts = data[
        "publication_counts"
    ]

    core_embeddings = data[
        "core_embeddings"
    ]

    full_embeddings = data[
        "full_embeddings"
    ]

    model_name = str(
        data["model_name"][0]
    )

    if core_embeddings.shape != full_embeddings.shape:
        raise RuntimeError(
            "Core и Full embeddings имеют "
            "разную форму"
        )

    if core_embeddings.shape[0] != len(
        researcher_ids
    ):
        raise RuntimeError(
            "Количество embeddings не совпадает "
            "с количеством исследователей"
        )

    coauthors = load_coauthors(
        args.publications
    )

    print(
        f"Модель: {model_name}"
    )
    print(
        f"Исследователей: "
        f"{len(researcher_ids)}"
    )

    core_rows = build_recommendations(
        core_embeddings,
        researcher_ids,
        researcher_names,
        publication_counts,
        coauthors,
        model="core",
        top_n=args.top_n,
    )

    full_rows = build_recommendations(
        full_embeddings,
        researcher_ids,
        researcher_names,
        publication_counts,
        coauthors,
        model="full",
        top_n=args.top_n,
    )

    all_rows = core_rows + full_rows

    validate_recommendations(
        all_rows,
        coauthors,
    )

    write_csv(
        args.output,
        all_rows,
    )

    write_report(
        args.report,
        model_name=model_name,
        researcher_count=len(
            researcher_ids
        ),
        top_n=args.top_n,
        coauthors=coauthors,
        core_count=len(core_rows),
        full_count=len(full_rows),
    )

    print(
        f"Core-рекомендаций: "
        f"{len(core_rows)}"
    )
    print(
        f"Full-рекомендаций: "
        f"{len(full_rows)}"
    )
    print(
        "Проверка self/coauthor: OK"
    )
    print(
        f"CSV сохранён: {args.output}"
    )
    print(
        f"Отчёт сохранён: {args.report}"
    )


if __name__ == "__main__":
    main()