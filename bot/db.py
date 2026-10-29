from datetime import date, datetime

from sqlalchemy import (BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint,
                        func)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot.config import settings

engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cycle: Mapped[int] = mapped_column(Integer, default=1)
    last_issue: Mapped[date | None] = mapped_column(Date)
    remind_hour: Mapped[int | None] = mapped_column(Integer, default=10)
    reminded_on: Mapped[date | None] = mapped_column(Date)
    last_active: Mapped[date | None] = mapped_column(Date)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    en: Mapped[str] = mapped_column(String(64), unique=True)
    ru: Mapped[str] = mapped_column(String(128))


class UserWord(Base):
    __tablename__ = "user_words"
    __table_args__ = (UniqueConstraint("user_id", "word_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    cycle: Mapped[int] = mapped_column(Integer, index=True)
    introduced_on: Mapped[date] = mapped_column(Date)
    known: Mapped[bool] = mapped_column(Boolean, default=False)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    wrong: Mapped[int] = mapped_column(Integer, default=0)
