import os
from typing import Annotated
from fastapi import Depends
from user import User
from message import Message
from sqlmodel import SQLModel, Session, create_engine, select

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables.")


engine = create_engine(DATABASE_URL)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_user_id(username, session: Session):
    """Convenience method to look up the id for a username."""
    statement = select(User.user_id).where(User.username == username)
    result = session.exec(statement).first()
    return result
