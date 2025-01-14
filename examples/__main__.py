"""Example project using diwrappers."""

from diwrappers import contextual_dependency, dependency
import contextlib
from collections import abc

import sqlmodel as sql
import pydantic_settings as ps
import typing as t


class DBSettings(ps.BaseSettings):
    db_kind: t.Literal["sqlite"] = "sqlite"
    db_path: str = "/database.db"

    @property
    def db_string(self):
        return f"{self.db_kind}://{self.db_path}"


class User(sql.SQLModel, table=True):
    """User table."""

    id: int | None = sql.Field(default=None, primary_key=True)
    name: str
    email: str = sql.Field(unique=True)
    age: int | None = None


@dependency
def db_settings():
    return DBSettings()


@dependency
@db_settings.inject
def db_string(db_settings: DBSettings):
    return db_settings.db_string


@contextual_dependency
@contextlib.contextmanager
@db_string.inject
def db_session(db_string: str) -> abc.Generator[sql.Session]:
    """Construct and manage lifetime of a session."""
    engine = sql.create_engine(db_string)
    sql.SQLModel.metadata.create_all(engine)
    with sql.Session(engine) as session:
        yield session


@db_session.inject
def create_user(session: sql.Session, user: User) -> None:
    """Create a new user."""
    session.add(user)
    session.commit()


@db_session.inject
def get_all_users(session: sql.Session) -> list[User]:
    """Fetch all users."""
    users = session.exec(sql.select(User)).all()
    return list(users)


@db_session.inject
def get_user(session: sql.Session, name: str) -> User | None:
    """Get a specific user."""
    query = sql.select(User).where(User.name == name)
    users = session.exec(query)
    return users.first()


@db_session.inject
def update_user(session: sql.Session, user: User) -> None:
    """Update user."""
    session.add(user)
    session.commit()


@db_session.ensure
def main() -> None:
    """Entrypoint."""
    john = User(name="John Doe", email="john.doe@example.com")
    create_user(user=john)

    users = get_all_users()

    assert john in users

    john.age = 25
    update_user(john)

    user = get_user(name=john.name)
    assert user is not None
    assert user == john


if __name__ == "__main__":
    main()
