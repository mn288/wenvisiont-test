from datetime import datetime

from sqlmodel import Field, SQLModel


class StepLog(SQLModel, table=True):
    __tablename__ = "step_logs"

    id: int | None = Field(default=None, primary_key=True)
    thread_id: str = Field(index=True)
    step_name: str
    log_type: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    checkpoint_id: str | None = None


class StepLogResponse(SQLModel):
    id: int
    thread_id: str
    step_name: str
    log_type: str
    content: str
    created_at: datetime
    checkpoint_id: str | None = None
    parent_checkpoint_id: str | None = None
