# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application written with FastAPI and sqlite3.
"""

import time
import sqlite3
from hashlib import md5
from datetime import datetime
from contextlib import closing
from werkzeug.security import check_password_hash, generate_password_hash

from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# configuration
DATABASE = '/tmp/minitwit.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory="templates")

def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(DATABASE)

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
    """Convenience method to look up the id for a username."""
    rv = db.execute('select user_id from user where username = ?',
                       [username]).fetchone()
    return rv[0] if rv else None

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')

def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)

# Register filters with the templates environment
templates.env.filters['datetimeformat'] = format_datetime
templates.env.filters['gravatar'] = gravatar_url

@app.get('/')
def timeline(
    request: Request, 
    db = Depends(get_db)
):
    """Shows a users timeline or if no user is logged in it will redirect to public."""
    user_id = request.session.get('user_id')
    if not user_id:
        return RedirectResponse(url='/public', status_code=303)

    user = query_db(db, 'select * from user where user_id = ?', [user_id], one=True)

    return templates.TemplateResponse('timeline.html', {
        "request": request, 
        "messages": query_db(db, '''
            select message.*, user.* from message, user
            where message.flagged = 0 and message.author_id = user.user_id and (
                user.user_id = ? or
                user.user_id in (select whom_id from follower
                                        where who_id = ?))
            order by message.pub_date desc limit ?''',
            [user_id, user_id, PER_PAGE]),
        "user": user,
        "endpoint": 'timeline'
    })

@app.get('/public')
def public_timeline(
    request: Request, 
    db = Depends(get_db)
):
    """Displays the latest messages of all users."""
    user_id = request.session.get('user_id')
    user = query_db(db, 'select * from user where user_id = ?', [user_id], one=True) if user_id else None

    messages = query_db(db, '''
        select message.*, user.* from message, user
        where message.flagged = 0 and message.author_id = user.user_id
        order by message.pub_date desc limit ?''', [PER_PAGE])

    return templates.TemplateResponse('timeline.html', {
        "request": request, 
        "messages": messages,
        "user": user,
        "endpoint": 'public_timeline'
    })


@app.post('/add_message')
def add_message(
    text: str = Form(...), 
    request: Request = None, 
    db = Depends(get_db)
):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Log in to post")

    if text.strip():
        db.execute('''insert into message (author_id, text, pub_date, flagged)
            values (?, ?, ?, 0)''', (user_id, text, int(time.time())))
        db.commit()
    return RedirectResponse(url='/', status_code=303)

@app.api_route('/login', methods=['GET', 'POST'])
def login(
    request: Request, 
    db = Depends(get_db),
    username: str = Form(None), 
    password: str = Form(None)
):
    if request.session.get('user_id'):
        return RedirectResponse(url='/', status_code=303)
    
    error = None
    if request.method == 'POST':
        user = query_db(db, 'select * from user where username = ?', [username], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'], password):
            error = 'Invalid password'
        else:
            request.session['user_id'] = user['user_id']
            return RedirectResponse(url='/', status_code=303)

    return templates.TemplateResponse('login.html', {
        "request": request, 
        "error": error,
        "username": username,
        "user": None
    })

@app.api_route('/register', methods=['GET', 'POST'])
def register(
    request: Request,
    db = Depends(get_db),
    username: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    password2: str = Form(None)
):
    if request.session.get('user_id'):
        return RedirectResponse(url='/', status_code=303)
        
    error = None
    if request.method == 'POST':
        if not username:
            error = 'You have to enter a username'
        elif not email or '@' not in email:
            error = 'You have to enter a valid email address'
        elif not password:
            error = 'You have to enter a password'
        elif password != password2:
            error = 'The two passwords do not match'
        elif get_user_id(db, username) is not None:
            error = 'The username is already taken'
        else:
            db.execute('''insert into user (
                username, email, pw_hash) values (?, ?, ?)''',
                [username, email, generate_password_hash(password)])
            db.commit()
            return RedirectResponse(url='/login', status_code=303)

    return templates.TemplateResponse('register.html', {
        "request": request, 
        "error": error,
        "username": username,
        "email": email,
        "user": None
    })

@app.get('/{username}')
def user_timeline(
    username: str,
    request: Request, 
    db = Depends(get_db)
):
    """Displays a user's tweets."""
    profile_user = query_db(db, 'select * from user where username = ?',
                            [username], one=True)
    
    if profile_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = request.session.get('user_id')
    user = query_db(db, 'select * from user where user_id = ?', [user_id], one=True) if user_id else None
    
    followed = False
    if user_id:
        followed = query_db(db, '''select 1 from follower where
            follower.who_id = ? and follower.whom_id = ?''',
            [user_id, profile_user['user_id']], one=True) is not None

    return templates.TemplateResponse('timeline.html', {
        "request": request,
        "messages": query_db(db, '''
            select message.*, user.* from message, user where
            user.user_id = message.author_id and user.user_id = ?
            order by message.pub_date desc limit ?''',
            [profile_user['user_id'], PER_PAGE]),
        "followed": followed,
        "profile_user": profile_user,
        "user": user,
        "endpoint": 'user_timeline'
    })

@app.get('/{username}/follow')
def follow_user(
    username: str, 
    request: Request, 
    db = Depends(get_db)
):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in first")

    whom_id = get_user_id(db, username)
    if whom_id is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute('insert into follower (who_id, whom_id) values (?, ?)',
                [user_id, whom_id])
    db.commit()
    return RedirectResponse(url=f"/{username}", status_code=303)

@app.get('/{username}/unfollow')
def unfollow_user(
    username: str, 
    request: Request, 
    db = Depends(get_db)
):
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Log in to unfollow")

    whom_id = get_user_id(db, username)
    if whom_id is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute('delete from follower where who_id=? and whom_id=?',
                [user_id, whom_id])
    db.commit()
    return RedirectResponse(url=f"/{username}", status_code=303)

@app.get('/logout')
def logout(request: Request):
    request.session.pop('user_id', None)
    return RedirectResponse(url='/public', status_code=303)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)