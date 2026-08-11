# models.py
from sqlalchemy import ForeignKey, CheckConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("role IN ('requester','ehs','admin')", name="valid_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    hash: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    phone_number: Mapped[str | None] = mapped_column(unique=True)
    email: Mapped[str | None] = mapped_column(unique=True)
    role: Mapped[str]

    permits: Mapped[list["Permit"]] = relationship(back_populates="requester")
    actions: Mapped[list["PermitAction"]] = relationship(back_populates="actor")


class Permit(Base):
    __tablename__ = "permits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','submitted','approved','rejected','closed')",
            name="valid_status",
        ),
        CheckConstraint(
            "type IN ('hot_work','confined_space','electrical','work_at_height','excavation','cold_work','lifting')",
            name="valid_type"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    requester_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    type: Mapped[str]
    location: Mapped[str]
    valid_from: Mapped[datetime]
    valid_until: Mapped[datetime]
    status: Mapped[str] = mapped_column(default="draft")
    description: Mapped[str]

    requester: Mapped["Employee"] = relationship(back_populates="permits")
    actions: Mapped[list["PermitAction"]] = relationship(back_populates="permit")


class PermitAction(Base):
    __tablename__ = "permit_actions"
    __table_args__ = (
        CheckConstraint(
            "action IN ('submitted','approved','rejected','closed')",
            name="valid_action",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    permit_id: Mapped[int] = mapped_column(ForeignKey("permits.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    action: Mapped[str]
    comment: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    permit: Mapped["Permit"] = relationship(back_populates="actions")
    actor: Mapped["Employee"] = relationship(back_populates="actions")