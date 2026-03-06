import os
from contextlib import closing
from typing import Annotated

from fastapi import Depends
from user import User
from message import Message
from sqlmodel import SQLModel, Session, create_engine

# DATABASE = os.getenv("DATABASE_PATH", "/tmp/minitwit.db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./minitwit.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# def init_db():
#     """Creates the database tables."""
#     with closing(connect_db()) as db:
#         with open('schema.sql', mode='r', encoding='utf-8') as f:
#             db.cursor().executescript(f.read())
#         db.commit()

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

# def get_db():
#     db = connect_db()
#     db.row_factory = sqlite3.Row
#     try:
#         yield db
#     finally:
#         db.close()



# def query_db(db, query, args=(), one=False):
#     """Queries the database and returns a list of dictionaries."""
#     cur = db.execute(query, args)
#     rv = [dict(row) for row in cur.fetchall()]
#     return (rv[0] if rv else None) if one else rv

# def get_user_id(db, username):
#     rv = db.execute('select user_id from user where username = ?', [username]).fetchone()
#     return rv[0] if rv else None

