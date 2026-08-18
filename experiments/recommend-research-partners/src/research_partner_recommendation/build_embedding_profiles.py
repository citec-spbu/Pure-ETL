from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-small"


def clean_text(value: str | None) -> str:
    """Normalize whitespace in a text field."""
    if not value:
        return ""

    return " ".join(value.split())


def build_publication_text(
    row: dict[str, str],
    *,
    include_abstract: bool,
) -> str:
    parts = [
        clean_text(row.get("publication_title")),
        clean_text(row.get("keywords")),
    ]

    if include_abstract:
        parts.append(clean_text(row.get("abstract")))

    text = ". ".join(
        part
        for part in parts
        if part
    )

    return f"query: {text}"


def load_publications(
    path: Path,
) -> tuple[
    dict[str, dict[str, str]],
    list[tuple[str, str]],
    dict[str, str],
]:
    publication_rows: dict[str, dict[str, str]] = {}
    associations: list[tuple[str, str]] = []
    researcher_names: dict[str, str] = {}

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
            researcher_name = clean_text(
                row.get("researcher_name")
            )
            publication_id = clean_text(
                row.get("publication_id")
            )

            if not researcher_id or not publication_id:
                continue

            publication_rows.setdefault(
                publication_id,
                row,
            )

            associations.append(
                (
                    researcher_id,
                    publication_id,
                )
            )

            if researcher_name:
                researcher_names[researcher_id] = (
                    researcher_name
                )

    return (
        publication_rows,
        associations,
        researcher_names,
    )


def build_researcher_embeddings(
    publication_embeddings: np.ndarray,
    publication_ids: list[str],
    associations: list[tuple[str, str]],
) -> tuple[
    list[str],
    np.ndarray,
    np.ndarray,
]:

    publication_index = {
        publication_id: index
        for index, publication_id in enumerate(publication_ids)
    }

    researcher_publications: dict[str, set[str]] = defaultdict(set)

    for researcher_id, publication_id in associations:
        researcher_publications[researcher_id].add(publication_id)

    researcher_ids = sorted(researcher_publications)

    embedding_dimension = publication_embeddings.shape[1]

    researcher_embeddings = np.zeros(
        (
            len(researcher_ids),
            embedding_dimension,
        ),
        dtype=np.float32,
    )

    publication_counts = np.zeros(
        len(researcher_ids),
        dtype=np.int32,
    )

    for researcher_index, researcher_id in enumerate(researcher_ids):
        researcher_publication_ids = sorted(
            researcher_publications[researcher_id]
        )

        indices = [
            publication_index[publication_id]
            for publication_id in researcher_publication_ids
        ]

        vectors = publication_embeddings[indices]

        mean_vector = vectors.mean(axis=0)

        norm = np.linalg.norm(mean_vector)

        if norm > 0:
            mean_vector = mean_vector / norm

        researcher_embeddings[researcher_index] = mean_vector
        publication_counts[researcher_index] = len(indices)

    return (
        researcher_ids,
        researcher_embeddings,
        publication_counts,
    )
def write_report(
    path: Path,
    *,
    model_name: str,
    association_count: int,
    publication_count: int,
    researcher_count: int,
    embedding_dimension: int,
) -> None:
    lines = [
        "# Отчёт о семантических профилях",
        "",
        "## Метод",
        "",
        (
            f"- Модель: `{model_name}`"
        ),
        (
            "- Core: название публикации + "
            "ключевые слова"
        ),
        (
            "- Full: название публикации + "
            "ключевые слова + аннотация"
        ),
        (
            "- Embedding исследователя: среднее "
            "embeddings его публикаций"
        ),
        (
            "- Итоговые embeddings исследователей "
            "нормализуются по L2"
        ),
        "",
        "## Результат",
        "",
        (
            "- Связей «исследователь — публикация»: "
            f"**{association_count}**"
        ),
        (
            "- Уник публикаций: "
            f"**{publication_count}**"
        ),
        (
            "- Исследователей: "
            f"**{researcher_count}**"
        ),
        (
            "- Размерность embedding: "
            f"**{embedding_dimension}**"
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
            "Построить семантические"
            "профили исследователей"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "output/researcher_publications.csv"
        ),
        help=(
            "CSV со связями"
            "«исследователь — публикация»"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "output/researcher_embeddings.npz"
        ),
        help=(
            "файл с embeddings"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/embedding_profiles_summary.md"
        ),
        help="Markdown-отчёт",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help="Название embedding-модели",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Размер batch при кодировании",
    )

    args = parser.parse_args()

    (
        publication_rows,
        associations,
        researcher_names,
    ) = load_publications(args.input)

    publication_ids = sorted(publication_rows)

    core_texts = [
        build_publication_text(
            publication_rows[publication_id],
            include_abstract=False,
        )
        for publication_id in publication_ids
    ]

    full_texts = [
        build_publication_text(
            publication_rows[publication_id],
            include_abstract=True,
        )
        for publication_id in publication_ids
    ]

    print(
        f"Модель: {args.model}"
    )
    print(
        f"Уникальных публикаций: "
        f"{len(publication_ids)}"
    )
    print(
        f"Связей исследователь-публикация: "
        f"{len(associations)}"
    )

    model = SentenceTransformer(args.model)

    core_publication_embeddings = model.encode(
        core_texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    full_publication_embeddings = model.encode(
        full_texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    (
        researcher_ids,
        core_researcher_embeddings,
        publication_counts,
    ) = build_researcher_embeddings(
        core_publication_embeddings,
        publication_ids,
        associations,
    )

    (
        full_researcher_ids,
        full_researcher_embeddings,
        full_publication_counts,
    ) = build_researcher_embeddings(
        full_publication_embeddings,
        publication_ids,
        associations,
    )

    if researcher_ids != full_researcher_ids:
        raise RuntimeError(
            "Core и Full содержат разные наборы исследователей"
        )

    if not np.array_equal(
        publication_counts,
        full_publication_counts,
    ):
        raise RuntimeError(
            "Core и Full содержат разные количества публикаций"
        )

    researcher_names_array = np.array(
        [
            researcher_names.get(
                researcher_id,
                "",
            )
            for researcher_id in researcher_ids
        ],
        dtype=str,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.savez_compressed(
        args.output,
        researcher_ids=np.array(
            researcher_ids,
            dtype=str,
        ),
        researcher_names=researcher_names_array,
        publication_counts=publication_counts,
        core_embeddings=core_researcher_embeddings,
        full_embeddings=full_researcher_embeddings,
        model_name=np.array(
            [args.model],
            dtype=str,
        ),
    )

    embedding_dimension = (
        core_researcher_embeddings.shape[1]
    )

    write_report(
        args.report,
        model_name=args.model,
        association_count=len(associations),
        publication_count=len(publication_ids),
        researcher_count=len(researcher_ids),
        embedding_dimension=embedding_dimension,
    )

    print(
        f"Исследователей: {len(researcher_ids)}"
    )
    print(
        f"Размерность embedding: "
        f"{embedding_dimension}"
    )
    print(
        f"Embeddings сохранены: {args.output}"
    )
    print(
        f"Отчёт сохранён: {args.report}"
    )


if __name__ == "__main__":
    main()