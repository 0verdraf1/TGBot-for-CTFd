"""Модели для базы данных"""
from passlib.hash import bcrypt_sha256

from config import DATABASE_URL
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, text, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

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


class CTFdUser(Base):
    """Модель таблицы пользователей CTFd."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128))
    email = Column(String(128), unique=True)
    password = Column(String(128))
    type = Column(String(80), default="user")
    hidden = Column(Boolean, default=False)
    banned = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    created = Column(DateTime)
    change_password = Column(Boolean, default=False)


def hash_password(plaintext):
    return bcrypt_sha256.hash(str(plaintext))


async def update_all_users_scores():
    """
    Пересчитывает баллы для всех пользователей бота на основе данных CTFd
    и записывает их в таблицу users_bot.
    """

    sql = text("""
    UPDATE users_bot ub
    JOIN users u ON ub.email = u.email
    SET ub.points = (
        COALESCE((
            SELECT SUM(c.value)
            FROM solves s
            JOIN challenges c ON s.challenge_id = c.id
            WHERE s.user_id = u.id
        ), 0)
        +
        COALESCE((
            SELECT SUM(a.value)
            FROM awards a
            WHERE a.user_id = u.id
        ), 0)
    );
    """)

    async with async_session() as session:
        await session.execute(sql)
        await session.commit()


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
