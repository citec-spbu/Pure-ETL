from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from statistics import mean, median


def load_recommendations(
    path: Path,
) -> tuple[
    dict[tuple[str, str], list[dict[str, str]]],
    dict[str, str],
]:
    grouped: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = {}

    researcher_names: dict[str, str] = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            model = (row.get("model") or "").strip()
            researcher_id = (
                row.get("researcher_id") or ""
            ).strip()

            if not model or not researcher_id:
                continue

            key = (
                model,
                researcher_id,
            )

            grouped.setdefault(
                key,
                [],
            ).append(row)

            researcher_name = (
                row.get("researcher_name") or ""
            ).strip()

            if researcher_name:
                researcher_names[
                    researcher_id
                ] = researcher_name

    for rows in grouped.values():
        rows.sort(
            key=lambda row: int(
                row["rank"]
            )
        )

    return grouped, researcher_names


def validate_inputs(
    tfidf: dict[
        tuple[str, str],
        list[dict[str, str]],
    ],
    embeddings: dict[
        tuple[str, str],
        list[dict[str, str]],
    ],
    *,
    top_n: int,
) -> None:
    """
    Check that both methods contain the same
    researcher/model combinations and Top-N size.
    """
    tfidf_keys = set(tfidf)
    embedding_keys = set(embeddings)

    if tfidf_keys != embedding_keys:
        missing_in_embeddings = (
            tfidf_keys - embedding_keys
        )

        missing_in_tfidf = (
            embedding_keys - tfidf_keys
        )

        raise RuntimeError(
            "Наборы исследователей не совпадают. "
            f"Нет в embeddings: "
            f"{len(missing_in_embeddings)}; "
            f"нет в TF-IDF: "
            f"{len(missing_in_tfidf)}."
        )

    for key in sorted(tfidf_keys):
        if len(tfidf[key]) != top_n:
            raise RuntimeError(
                f"TF-IDF {key}: ожидалось "
                f"{top_n} рекомендаций, "
                f"получено {len(tfidf[key])}."
            )

        if len(embeddings[key]) != top_n:
            raise RuntimeError(
                f"Embeddings {key}: ожидалось "
                f"{top_n} рекомендаций, "
                f"получено {len(embeddings[key])}."
            )


def compare_methods(
    tfidf: dict[
        tuple[str, str],
        list[dict[str, str]],
    ],
    embeddings: dict[
        tuple[str, str],
        list[dict[str, str]],
    ],
    researcher_names: dict[str, str],
    *,
    top_n: int,
) -> list[dict[str, object]]:
    comparison_rows: list[
        dict[str, object]
    ] = []

    for model, researcher_id in sorted(
        tfidf
    ):
        tfidf_rows = tfidf[
            (
                model,
                researcher_id,
            )
        ]

        embedding_rows = embeddings[
            (
                model,
                researcher_id,
            )
        ]

        tfidf_ids = [
            row[
                "recommended_researcher_id"
            ]
            for row in tfidf_rows
        ]

        embedding_ids = [
            row[
                "recommended_researcher_id"
            ]
            for row in embedding_rows
        ]

        tfidf_names = [
            row[
                "recommended_researcher_name"
            ]
            for row in tfidf_rows
        ]

        embedding_names = [
            row[
                "recommended_researcher_name"
            ]
            for row in embedding_rows
        ]

        common_ids = (
            set(tfidf_ids)
            & set(embedding_ids)
        )

        common_names = [
            row[
                "recommended_researcher_name"
            ]
            for row in tfidf_rows
            if row[
                "recommended_researcher_id"
            ] in common_ids
        ]

        overlap_count = len(
            common_ids
        )

        same_rank_count = sum(
            tfidf_id == embedding_id
            for tfidf_id, embedding_id
            in zip(
                tfidf_ids,
                embedding_ids,
            )
        )

        top1_match = (
            tfidf_ids[0]
            == embedding_ids[0]
        )

        comparison_rows.append(
            {
                "model": model,
                "researcher_id": (
                    researcher_id
                ),
                "researcher_name": (
                    researcher_names.get(
                        researcher_id,
                        "",
                    )
                ),
                "top_n": top_n,
                "overlap_count": (
                    overlap_count
                ),
                "overlap_fraction": (
                    f"{overlap_count / top_n:.4f}"
                ),
                "top1_match": (
                    int(top1_match)
                ),
                "same_rank_count": (
                    same_rank_count
                ),
                "tfidf_recommendations": (
                    " | ".join(
                        tfidf_names
                    )
                ),
                "embedding_recommendations": (
                    " | ".join(
                        embedding_names
                    )
                ),
                "common_recommendations": (
                    " | ".join(
                        common_names
                    )
                ),
            }
        )

    return comparison_rows


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    fieldnames = [
        "model",
        "researcher_id",
        "researcher_name",
        "top_n",
        "overlap_count",
        "overlap_fraction",
        "top1_match",
        "same_rank_count",
        "tfidf_recommendations",
        "embedding_recommendations",
        "common_recommendations",
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


def model_statistics(
    rows: list[dict[str, object]],
    model: str,
    *,
    top_n: int,
) -> dict[str, object]:
    selected = [
        row
        for row in rows
        if row["model"] == model
    ]

    overlap_counts = [
        int(row["overlap_count"])
        for row in selected
    ]

    top1_matches = sum(
        int(row["top1_match"])
        for row in selected
    )

    same_rank_counts = [
        int(row["same_rank_count"])
        for row in selected
    ]

    distribution = Counter(
        overlap_counts
    )

    return {
        "researcher_count": len(
            selected
        ),
        "mean_overlap": mean(
            overlap_counts
        ),
        "median_overlap": median(
            overlap_counts
        ),
        "mean_overlap_fraction": (
            mean(overlap_counts)
            / top_n
        ),
        "top1_matches": (
            top1_matches
        ),
        "top1_fraction": (
            top1_matches
            / len(selected)
        ),
        "mean_same_rank": mean(
            same_rank_counts
        ),
        "distribution": (
            distribution
        ),
    }


def write_report(
    path: Path,
    rows: list[dict[str, object]],
    *,
    top_n: int,
) -> None:
    lines = [
        "# Сравнение TF-IDF и semantic embeddings",
        "",
        "## Метод",
        "",
        (
            "Для каждого исследователя сравниваются "
            f"Top-{top_n} рекомендаций TF-IDF "
            "и семантической модели"
        ),
        "",
    ]

    for model in (
        "core",
        "full",
    ):
        stats = model_statistics(
            rows,
            model,
            top_n=top_n,
        )

        lines.extend(
            [
                f"## {model.capitalize()}",
                "",
                (
                    "- Исследователей: "
                    f"**{stats['researcher_count']}**"
                ),
                (
                    "- Среднее число совпадающих "
                    "кандидатов: "
                    f"**{stats['mean_overlap']:.2f} "
                    f"из {top_n}**"
                ),
                (
                    "- Медианное число совпадающих "
                    "кандидатов: "
                    f"**{stats['median_overlap']:.2f} "
                    f"из {top_n}**"
                ),
                (
                    "- Средняя доля совпадения "
                    "Top-N: "
                    f"**{stats['mean_overlap_fraction']:.2%}**"
                ),
                (
                    "- Совпадение кандидата "
                    "на первом месте: "
                    f"**{stats['top1_matches']} "
                    f"({stats['top1_fraction']:.2%})**"
                ),
                (
                    "- Среднее число кандидатов "
                    "на одинаковой позиции: "
                    f"**{stats['mean_same_rank']:.2f} "
                    f"из {top_n}**"
                ),
                "",
                "### Распределение Top-N overlap",
                "",
            ]
        )

        distribution = stats[
            "distribution"
        ]

        for overlap in range(
            top_n + 1
        ):
            lines.append(
                f"- {overlap}/{top_n}: "
                f"**{distribution.get(overlap, 0)}**"
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
            "Сравнить Top-N рекомендации "
            "TF-IDF и semantic embeddings"
        )
    )

    parser.add_argument(
        "--tfidf",
        type=Path,
        default=Path(
            "output/"
            "tfidf_recommendations.csv"
        ),
    )

    parser.add_argument(
        "--embeddings",
        type=Path,
        default=Path(
            "output/"
            "embedding_recommendations.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "output/"
            "recommendation_comparison.csv"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/"
            "recommendation_comparison_summary.md"
        ),
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    (
        tfidf,
        tfidf_names,
    ) = load_recommendations(
        args.tfidf
    )

    (
        embeddings,
        embedding_names,
    ) = load_recommendations(
        args.embeddings
    )

    researcher_names = {
        **tfidf_names,
        **embedding_names,
    }

    validate_inputs(
        tfidf,
        embeddings,
        top_n=args.top_n,
    )

    rows = compare_methods(
        tfidf,
        embeddings,
        researcher_names,
        top_n=args.top_n,
    )

    write_csv(
        args.output,
        rows,
    )

    write_report(
        args.report,
        rows,
        top_n=args.top_n,
    )

    print(
        f"Сравнено профилей: "
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