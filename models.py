"""Модели для базы данных"""
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

Base = declarative_base()


class User(Base):
    """Задание необходимых столбцов в БД."""

    __tablename__ = "users_bot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(255), nullable=False)
    place_of_study = Column(String(255), nullable=False)
    school = Column(String(255), nullable=False)
    grade = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    points = Column(Integer, default=0)

    login_id = Column(String(255), unique=True)
    plain_password = Column(String(255))

    is_banned = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)


class BannedUser(Base):
    """Таблица забаненных участников."""

    __tablename__ = "users_banned_bot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    reason = Column(Text, nullable=False)

    admin_who_banned = Column(String(255), nullable=False)

    proof = Column(Text, nullable=True)

    admin_who_unbanned = Column(String(255), nullable=True)


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
    )


async def init_db():
    """Инициализируем БД."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
