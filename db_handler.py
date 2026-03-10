import os
from contextlib import closing
from typing import Annotated

from fastapi import Depends
from user import User
from message import Message
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

DEFAULT_DB_URL = "/tmp/minitwit.db"
DATABASE_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_URL)
if not DATABASE_PATH.startswith("sqlite:///"):
    sqlite_url = f"sqlite:///{DATABASE_PATH}"
else: 
    sqlite_url = DATABASE_PATH
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

def get_user_id(username,session:Session):
    """Convenience method to look up the id for a username."""
    statement = select(User.user_id).where(User.username == username)
    result = session.exec(statement).first()
    return result 

