from uuid import UUID

import sqlalchemy
from sqlalchemy import CTE, cast, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models import (
    ResearchOutput,
)


def research_outputs_publication_statuses() -> sqlalchemy.Select[tuple[UUID, dict]]:
    """
    Destructures json `publication_statuses` list into many rows for all research outputs

    Columns returned:
    - `research_output_id` - `uuid`
    - `publication_status` - `jsonb`
    """
    return (
        sqlalchemy.select(
            ResearchOutput.id.label("research_output_id"),
            sqlalchemy.column("publication_status", JSONB).label("publication_status"),
        )
        .select_from(ResearchOutput)
        .outerjoin(
            func.jsonb_array_elements(
                sqlalchemy.case(
                    (
                        func.jsonb_typeof(ResearchOutput.publication_statuses) == "array",
                        ResearchOutput.publication_statuses,
                    ),
                    else_=sqlalchemy.literal("[]", type_=sqlalchemy.String),
                )
            ).lateral("publication_status"),
            sqlalchemy.true(),
        )
    )


def add_current_publication_status(research_outputs: CTE) -> sqlalchemy.Select:
    """
    Columns expected in the provided cte:
    - `research_output_id` - `uuid`

    Columns returned:
    - All from provided `research_outputs` cte
    - `current_publication_status` - `jsonb` or `null`
    """

    statuses = research_outputs_publication_statuses().cte()

    current_statuses = (
        sqlalchemy.select(statuses).where(cast(statuses.c.publication_status["current"], sqlalchemy.Boolean)).cte()
    )

    return (
        sqlalchemy.select(
            research_outputs,
            current_statuses.c.publication_status,
        )
        .select_from(research_outputs)
        .outerjoin(
            current_statuses,
            research_outputs.c.research_output_id == current_statuses.c.research_output_id,
        )
    )
