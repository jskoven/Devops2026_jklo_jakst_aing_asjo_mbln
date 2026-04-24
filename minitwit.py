# -*- coding: utf-8 -*-
"""
MiniTwit
~~~~~~~~

A microblogging application written with FastAPI and sqlite3.
"""

from contextlib import asynccontextmanager
import time
from hashlib import md5
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from db_handler import init_db, SessionDep, get_user_id
from follower import Follower
from message import Message
from user import User
from sqlmodel import desc, or_, select
from API_handler import router as API_handler
from prometheus_fastapi_instrumentator import Instrumentator
from urllib.parse import urlparse

# configuration
DATABASE = "/tmp/minitwit.db"
PER_PAGE = 30
DEBUG = True
SECRET_KEY = "development key"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    print("Shutting down...")


# create our little application :)
app = FastAPI(lifespan=lifespan)

instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app, endpoint="/metrics")
# This function tells fastAPI to add all the endpoints in API_handler to it's list of endpoints.
# When we run the minitwit.py file, it then also serves all those endpoints for the simulator.
app.include_router(API_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory="templates")


# Helper function to use flash messages with fastAPI setup
def flash(request: Request, message: str = "message"):
    request.session.setdefault("_flashes", []).append({"message": message})


def get_flashed_messages(request: Request):
    return request.session.pop("_flashes", [])


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d @ %H:%M")


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return "http://www.gravatar.com/avatar/%s?d=identicon&s=%d" % (
        md5(email.strip().lower().encode("utf-8")).hexdigest(),
        size,
    )


def is_safe_url(target):
    # Ensure the URL is relative and not absolute
    ref_url = urlparse(target)
    # netloc is the 'google.com' part. If it's empty, it's a local path.
    return not ref_url.scheme and not ref_url.netloc


# Register filters with the templates environment
templates.env.filters["datetimeformat"] = format_datetime
templates.env.filters["gravatar"] = gravatar_url


@app.get("/")
def timeline(request: Request, session: SessionDep):
    """Shows a users timeline or if no user is logged in it will redirect to public."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/public", status_code=303)

    user = session.get(User, user_id)

    followed_ids_query = select(Follower.whom_id).where(Follower.who_id == user_id)
    followed_ids = session.exec(followed_ids_query).all()

    statement = (
        select(Message, User)
        .join(User, Message.author_id == User.user_id)
        .where(Message.flagged == 0)
        .where(or_(Message.author_id == user_id, Message.author_id.in_(followed_ids)))
        .order_by(desc(Message.pub_date))
        .limit(PER_PAGE)
    )

    results = session.exec(statement).all()
    flash_msg = get_flashed_messages(request)

    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "messages": results,
            "flashes": flash_msg,
            "user": user,
            "endpoint": "timeline",
        },
    )


@app.get("/public")
def public_timeline(request: Request, session: SessionDep):
    """Displays the latest messages of all users."""
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None

    statement = (
        select(Message, User)
        .join(User, Message.author_id == User.user_id)
        .where(Message.flagged == 0)
        .order_by(desc(Message.pub_date))
        .limit(PER_PAGE)
    )

    result = session.exec(statement).all()
    flash_msgs = get_flashed_messages(request)

    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "flashes": flash_msgs,
            "messages": result,
            "user": user,
            "endpoint": "public_timeline",
        },
    )


@app.post("/add_message")
def add_message(
    session: SessionDep,
    text: str = Form(...),
    request: Request = None,
):

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Log in to post")

    if text.strip():
        new_msg = Message(
            author_id=user_id, text=text, pub_date=int(time.time()), flagged=0
        )

    session.add(new_msg)
    session.commit()
    flash(request, "Your message was recorded")

    return RedirectResponse(url="/", status_code=303)


@app.api_route("/login_UI", methods=["GET", "POST"])
def login_UI(
    request: Request,
    session: SessionDep,
    username: str = Form(None),
    password: str = Form(None),
):
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/", status_code=303)
    error = None
    if request.method == "POST":
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        if user is None:
            error = "Invalid username"
        elif not check_password_hash(user.pw_hash, password):
            error = "Invalid password"
        else:
            flash(request, "You were logged in")
            request.session["user_id"] = user.user_id
            return RedirectResponse(url="/", status_code=303)
    flash_msgs = get_flashed_messages(request)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "flashes": flash_msgs,
            "error": error,
            "username": username,
            "user": None,
        },
    )


@app.api_route("/register_UI", methods=["GET", "POST"])
def register_UI(
    request: Request,
    session: SessionDep,
    username: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    password2: str = Form(None),
):
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/", status_code=303)

    error = None
    if request.method == "POST":
        if not username:
            error = "You have to enter a username"
        elif not email or "@" not in email:
            error = "You have to enter a valid email address"
        elif not password:
            error = "You have to enter a password"
        elif password != password2:
            error = "The two passwords do not match"
        elif get_user_id(username, session) is not None:
            error = "The username is already taken"
        else:
            new_usr = User(
                username=username, email=email, pw_hash=generate_password_hash(password)
            )
            session.add(new_usr)
            session.commit()

            flash(request, "You were successfully registered and can login now")
            return RedirectResponse(url="/login_UI", status_code=303)

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "error": error,
            "username": username,
            "email": email,
            "user": None,
        },
    )


@app.get("/logout_UI")
def logout_UI(request: Request):
    flash(request, "You were logged out")
    request.session.pop("user_id", None)
    return RedirectResponse(url="/public", status_code=303)


@app.get("/{username}")
def user_timeline(username: str, request: Request, session: SessionDep):
    """Displays a user's tweets."""
    profile_user = session.exec(select(User).where(User.username == username)).first()

    if profile_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None

    followed_res = False
    if user_id:

        followed = select(Follower).where(
            Follower.who_id == user_id, Follower.whom_id == profile_user.user_id
        )

        followed_res = session.exec(followed).first() is not None

    msg = (
        select(Message, User)
        .join(User, Message.author_id == User.user_id)
        .where(User.user_id == profile_user.user_id)
        .order_by(desc(Message.pub_date))
        .limit(PER_PAGE)
    )

    msg_res = session.exec(msg).all()

    flash_msgs = get_flashed_messages(request)

    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "flashes": flash_msgs,
            "messages": msg_res,
            "followed": followed_res,
            "profile_user": profile_user,
            "user": user,
            "endpoint": "user_timeline",
        },
    )


@app.get("/{username}/follow")
def follow_user(username: str, request: Request, session: SessionDep):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in first")

    whom_id = get_user_id(username, session)

    if whom_id is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_followr = Follower(who_id=user_id, whom_id=whom_id)

    session.add(new_followr)
    session.commit()
    flash(request, 'You are now following "%s"' % username)
    target_url = f"/{username}"
    if not is_safe_url(target_url):
        target_url = "/public"  # Fallback
    return RedirectResponse(url=target_url, status_code=303)


@app.get("/{username}/unfollow")
def unfollow_user(username: str, request: Request, session: SessionDep):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Log in to unfollow")

    whom_id = get_user_id(username, session)
    if whom_id is None:
        raise HTTPException(status_code=404, detail="User not found")

    unfollow = select(Follower).where(
        Follower.who_id == user_id, Follower.whom_id == whom_id
    )

    record_to_unfollow = session.exec(unfollow).first()
    if record_to_unfollow:
        session.delete(record_to_unfollow)
        session.commit()

    flash(request, 'You are no longer following "%s"' % username)

    target_url = f"/{username}"
    if not is_safe_url(target_url):
        target_url = "/public"  # Fallback
    return RedirectResponse(url=target_url, status_code=303)


@app.get("/health")
def health_check(request: Request):
    return {"status": "latest"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
