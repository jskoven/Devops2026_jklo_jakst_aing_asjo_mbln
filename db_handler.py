import sqlite3
import os
from contextlib import closing

DATABASE = os.getenv("DATABASE_PATH", "/tmp/minitwit.db")

def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(DATABASE, check_same_thread=False)

def get_db():
    db = connect_db()
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with open('schema.sql', mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(db, query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = db.execute(query, args)
    rv = [dict(row) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

def get_user_id(db, username):
    rv = db.execute('select user_id from user where username = ?', [username]).fetchone()
    return rv[0] if rv else None

