import polars as pl

pure_id = pl.Int64

classification_type = pl.Struct(
    {
        "pureId": pure_id,
    }
)


def parse_classification_type(expr: pl.Expr) -> pl.Expr:
    return expr.struct.field("pureId").alias("type_id")


text = pl.Struct(
    {
        "text": pl.List(
            pl.Struct(
                {
                    "locale": pl.String,
                    "value": pl.String,
                }
            )
        ),
        "formatted": pl.Boolean,
    }
)


def parse_text(expr: pl.Expr, name: str) -> pl.Expr:
    return pl.struct(
        expr.struct.field("text")
        .list.filter(pl.element().struct.field("locale") == "en_US")
        .list.first()
        .struct.field("value")
        .alias(f"{name}_en"),
        expr.struct.field("text")
        .list.filter(pl.element().struct.field("locale") == "ru_RU")
        .list.first()
        .struct.field("value")
        .alias(f"{name}_ru"),
    )


ids_id = pl.Struct(
    {
        "pureId": pure_id,
        "type": classification_type,
        "value": pl.Struct(
            {
                "value": pl.String,
                "formatted": pl.Boolean,
            }
        ),
        "externalId": pl.String,
        "externalIdSource": pl.String,
        "externallyManaged": pl.Boolean,
    }
)

ids = pl.List(ids_id)


def parse_ids(expr: pl.Expr) -> pl.Expr:
    return expr.list.eval(
        pl.struct(
            pl.element().struct.field("pureId").alias("pure_id"),
            pl.element().struct.field("type").struct.field("pureId").alias("type_id"),
            pl.element().struct.field("value").struct.field("value"),
            pl.element().struct.field("externalId").alias("external_id"),
            pl.element().struct.field("externalIdSource").alias("external_id_source"),
            pl.element().struct.field("externallyManaged").alias("externally_managed"),
        )
    )


titles_title = pl.Struct(
    {
        "pureId": pure_id,
        "type": classification_type,
        "value": text,
    }
)


titles = pl.List(titles_title)


def parse_titles(expr: pl.Expr) -> pl.Expr:
    return expr.list.eval(
        pl.struct(
            pl.element().struct.field("pureId").alias("pure_id"),
            pl.element().struct.field("type").struct.field("pureId").alias("type_id"),
            parse_text(pl.element().struct.field("value"), "value").struct.unnest(),
        )
    )
