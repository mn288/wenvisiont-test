from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class Configuration(SQLModel, table=True):
    __tablename__ = "configurations"

    key: str = Field(primary_key=True)
    value: dict = Field(sa_column=Column(JSON, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.now)
