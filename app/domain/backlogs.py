from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from litestar.contrib.sqlalchemy.base import AuditBase
from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository
from litestar.dto.factory import DTOConfig
from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column as m_col

from app.domain.projects import Project
from app.domain.users import User
from app.lib import service

__all__ = [
    "Backlog",
    "ReadDTO",
    "Repository",
    "Service",
    "WriteDTO",
]


class PriorityEnum(Enum):
    low = "🟢"
    med = "🟡"
    hi = "🔴"


class ProgressEnum(Enum):
    empty = "🟨🟨🟨"
    a_third = "🟩🟨🟨"
    two_third = "🟩🟩🟨"
    full = "🟩🟩🟩"


class StatusEnum(Enum):
    new = "🔅"
    started = "🚧"
    checked_in = "✔️"
    completed = "✅"
    cancelled = "🚫"


class TagEnum(Enum):
    ideas = "💡"
    issues = "⚠️"
    maintenance = "🔨"
    finances = "💰"
    innovation = "🚀"
    bugs = "🐞"
    features = "🎁"
    security = "🔒"
    attention = "🚩"
    backend = "📡"
    database = "💾"
    desktop = "🖥️"
    mobile = "📱"
    intl = "🌍"
    design = "🎨"
    analytics = "📈"
    automation = "🤖"


class Backlog(AuditBase):
    title: Mapped[str]
    description: Mapped[str | None]
    ref_id: Mapped[str | None]
    progress: Mapped[ProgressEnum | None]
    sprint_number: Mapped[int]
    priority: Mapped[PriorityEnum | None]
    status: Mapped[StatusEnum | None]
    is_task: Mapped[bool]
    category: Mapped[TagEnum | None]
    est_days: Mapped[float | None]
    beg_date: Mapped[datetime] = m_col(default=datetime.now(tz=UTC))
    end_date: Mapped[datetime] = m_col(default=datetime.now(tz=UTC))
    due_date: Mapped[datetime] = m_col(default=datetime.now(tz=UTC))
    # Relationships
    assignee_id: Mapped[UUID | None] = m_col(ForeignKey(User.id))
    owner_id: Mapped[UUID] = m_col(ForeignKey(User.id))
    project_slug: Mapped[str] = m_col(ForeignKey(Project.slug))
    audits: Mapped[list["BacklogAudit"]] = relationship("BacklogAudit", back_populates="backlog", lazy="joined")

    @property
    def assignee_link(self) -> str | None:
        return f"/user/{self.assignee_id}/backlog" if self.assignee_id else None

    @property
    def owner_link(self) -> str | None:
        return f"/user/{self.owner_id}/backlog"

    @property
    def project_link(self) -> str | None:
        return f"/project/{self.project_slug}/backlog"

    def gen_ref_id(self) -> str | None:
        slug = self.project_slug
        sprint_number = self.sprint_number
        uuid_str = str(self.id)
        # Take the first 8 characters of the UUID and remove any hyphens
        uuid_short = uuid_str[:8].replace("-", "")
        return f"{slug}-S{sprint_number}-{uuid_short}"

    def gen_due_date(self, beg_date: datetime, est_days: int) -> datetime:
        return beg_date + timedelta(days=est_days)


class BacklogAudit(AuditBase):
    backlog_id: Mapped[UUID] = m_col(ForeignKey(Backlog.id))
    field_name: Mapped[str]
    old_value: Mapped[str]
    new_value: Mapped[str]

    backlog: Mapped["Backlog"] = relationship(
        "Backlog",
        single_parent=True,
        back_populates="audits",
        foreign_keys=[backlog_id],
        lazy="joined",
        cascade="all, delete-orphan",
    )


@event.listens_for(Backlog, "before_update")
def track_changes_before_update(mapper: Any, connection: Any, backlog: Backlog) -> None:
    changed_attrs = {}
    for attr in mapper.attrs:
        history = attr.history
        if history.has_changes():
            changed_attrs[attr.key] = {
                "old": str(history.deleted[0]) if history.deleted else None,
                "new": str(history.added[0]) if history.added else None,
            }
    if changed_attrs:
        for key, values in changed_attrs.items():
            audit = BacklogAudit(
                backlog=backlog,
                field_name=key,
                old_value=values["old"],
                new_value=values["new"],
            )
            connection.add(audit)
            backlog.ref_id = backlog.gen_ref_id()
            connection.add(backlog)


@event.listens_for(Backlog, "after_insert")
def track_changes_before_insert(mapper: Any, connection: Any, backlog: Backlog) -> None:
    backlog.ref_id = backlog.gen_ref_id()
    connection.add(backlog)
    connection.commit()


class Repository(SQLAlchemyAsyncRepository[Backlog]):
    model_type = Backlog


class Service(service.Service[Backlog]):
    repository_type = Backlog


WriteDTO = SQLAlchemyDTO[Annotated[Backlog, DTOConfig(exclude={"id", "created", "updated"})]]
ReadDTO = SQLAlchemyDTO[Annotated[Backlog, DTOConfig(exclude={"backlog_audit"})]]