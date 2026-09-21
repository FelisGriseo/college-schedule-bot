from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Replacement(Base):
    __tablename__ = "replacements"
    __table_args__ = (UniqueConstraint("replacement_date", "group_name", "pair_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    replacement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    group_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pair_number: Mapped[int] = mapped_column(Integer, nullable=False)
    new_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teacher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
