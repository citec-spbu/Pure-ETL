from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[UUID] = mapped_column(name="person_id", primary_key=True)
    name: Mapped[Optional[str]]
