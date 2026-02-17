from fastapi import APIRouter, Depends, HTTPException, Request, Response
from werkzeug.security import generate_password_hash
import time
from db_handler import get_db, query_db, get_user_id

router = APIRouter()

# Used by the test file we got from Helge, I believe it's there to ensure synchronization between our app and
# the simulator, or something along those lines
LATEST_COMMAND = 0

def update_latest(request: Request):
    global LATEST_COMMAND
    latest = request.query_params.get("latest")
    if latest:
        LATEST_COMMAND = int(latest)

@router.get("/latest")
async def get_latest():
    return {"latest": LATEST_COMMAND}



@router.post("/register")
async def register(request: Request, db = Depends(get_db)):
    update_latest(request)
    data = await request.json()
    
    username = data.get("username")
    email = data.get("email")
    pwd = data.get("pwd")

    error = None
    if not username:
        error = "You have to enter a username"
    elif not email or "@" not in email:
        error = "You have to enter a valid email address"
    elif not pwd:
        error = "You have to enter a password"
    elif get_user_id(db, username) is not None:
        error = "The username is already taken"

    if error:
        raise HTTPException(status_code=400, detail=error)

    db.execute("INSERT INTO user (username, email, pw_hash) VALUES (?, ?, ?)",
               [username, email, generate_password_hash(pwd)])
    db.commit()
    return Response(status_code=204)

@router.get("/msgs")
async def messages(request: Request, db = Depends(get_db)):
    update_latest(request)
    no_msgs = int(request.query_params.get("no", 20))
    
    msgs = query_db(db, """
        SELECT message.*, user.* FROM message, user
        WHERE message.flagged = 0 AND message.author_id = user.user_id
        ORDER BY message.pub_date DESC LIMIT ?""", [no_msgs])
    
    return [{"content": m["text"], "pub_date": m["pub_date"], "user": m["username"]} for m in msgs]

@router.get("/msgs/{username}")
async def user_messages(username: str, request: Request, db = Depends(get_db)):
    update_latest(request)
    user_id = get_user_id(db, username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
        
    no_msgs = int(request.query_params.get("no", 20))
    msgs = query_db(db, """
        SELECT message.*, user.* FROM message, user
        WHERE message.flagged = 0 AND user.user_id = message.author_id AND user.user_id = ?
        ORDER BY message.pub_date DESC LIMIT ?""", [user_id, no_msgs])
    
    return [{"content": m["text"], "pub_date": m["pub_date"], "user": m["username"]} for m in msgs]

@router.post("/msgs/{username}")
async def post_message(username: str, request: Request, db = Depends(get_db)):
    update_latest(request)
    user_id = get_user_id(db, username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
        
    data = await request.json()
    db.execute("""INSERT INTO message (author_id, text, pub_date, flagged)
                  VALUES (?, ?, ?, 0)""", (user_id, data['content'], int(time.time())))
    db.commit()
    return Response(status_code=204)

@router.get("/fllws/{username}")
async def get_followers(username: str, request: Request, db = Depends(get_db)):
    update_latest(request)
    user_id = get_user_id(db, username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    no_followers = int(request.query_params.get("no", 20))
    res = query_db(db, """
        SELECT user.username FROM user
        INNER JOIN follower ON follower.whom_id = user.user_id
        WHERE follower.who_id = ? LIMIT ?
    """, [user_id, no_followers])
    
    return {"follows": [r["username"] for r in res]}

@router.post("/fllws/{username}")
async def follow_unfollow_user(username: str, request: Request, db = Depends(get_db)):
    update_latest(request)
    user_id = get_user_id(db, username)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    data = await request.json()
    if "follow" in data:
        whom_id = get_user_id(db, data["follow"])
        if whom_id:
            db.execute("INSERT INTO follower (who_id, whom_id) VALUES (?, ?)", [user_id, whom_id])
            db.commit()
    elif "unfollow" in data:
        whom_id = get_user_id(db, data["unfollow"])
        if whom_id:
            db.execute("DELETE FROM follower WHERE who_id = ? AND whom_id = ?", [user_id, whom_id])
            db.commit()

    return Response(status_code=204)