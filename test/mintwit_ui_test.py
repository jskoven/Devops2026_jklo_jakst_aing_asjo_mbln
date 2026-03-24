from shutil import which
from sqlmodel import Session, select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from werkzeug.security import generate_password_hash
from sqlalchemy import desc # Add this to your imports at the top
from message import Message
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from user import User
from conftest import GUI_URL


def _get_browser():
    options = Options()  
    options.add_argument("--headless") 
    return webdriver.Firefox(service=Service(which("geckodriver")), options=options)


def _register_user_via_gui(driver, username, email, password):
    driver.get(f"{GUI_URL}/register_UI")

    wait = WebDriverWait(driver, 5) 
    wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "actions"))) 
    input_fields = driver.find_elements(By.TAG_NAME, "input") 

    data = [username, email, password, password]
    for idx, value in enumerate(data):  
        input_fields[idx].send_keys(value) 
    input_fields[-1].send_keys(Keys.RETURN) 

    wait = WebDriverWait(driver, 5)
    wait.until(EC.url_contains("/login_UI"))
    return driver.current_url 


def _get_user_by_name(session: Session, username):
    return session.exec(select(User).where(User.username == username)).first()


def _delete_user_by_name(db_session: Session, username: str):
    user = _get_user_by_name(db_session, username)
    if user:
        # delete messsages first
        statement = select(Message).where(Message.author_id == user.user_id)
        messages = db_session.exec(statement).all()
        for msg in messages:
            db_session.delete(msg)
        
        # then delete the user
        db_session.delete(user)
        db_session.commit()

def _login_user_via_gui(driver, username, password):
    driver.get(f"{GUI_URL}/login_UI")

    wait = WebDriverWait(driver, 5) 
    wait.until(EC.presence_of_element_located((By.NAME, "username")))  
    
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)

    wait.until(EC.url_to_be(f"{GUI_URL}/"))
    return driver.current_url


def _post_message_via_gui(driver, message_text):
    wait = WebDriverWait(driver, 5) 
    
    input_field = wait.until(EC.presence_of_element_located((By.NAME, "text")))
    input_field.send_keys(message_text) 
    input_field.send_keys(Keys.RETURN)

    
    wait.until(EC.text_to_be_present_in_element((By.CLASS_NAME, "flashes"), "Your message was recorded"))


def _get_latest_message_by_user(session: Session, username: str):
    # find the user first to get their user_id
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        return None
    
    # query for the latest message by that user
    statement = (
        select(Message)
        .where(Message.author_id == user.user_id)
        .order_by(desc(Message.pub_date))
    )
    result = session.exec(statement).first()
    
    # Return the text of the message if found
    return result.text if result else None 

def _follow_user_via_gui(driver, username):
    wait = WebDriverWait(driver, 5) 
    driver.get(f"{GUI_URL}/{username}")
    
    follow_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Follow user")))
    follow_button.click()

def _unfollow_user_via_gui(driver, username):
    wait = WebDriverWait(driver, 5) 
    driver.get(f"{GUI_URL}/{username}")
    
    unfollow_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Unfollow user")))
    unfollow_button.click()


def test_register_user_via_gui(db_session: Session):
    """UI test — only checks what the user sees in the browser."""
    with _get_browser() as driver:
        login_ui = _register_user_via_gui(
            driver, "TestUser", "test@example.com", "secure123"
        )
        assert login_ui == "http://minitwit:5001/login_UI"

    # cleanup — ensures test is idempotent
    _delete_user_by_name(db_session, "TestUser")


def test_register_user_via_gui_and_check_db_entry(db_session: Session):
    """End-to-end test — verifies the UI action actually persisted to the DB."""
    assert _get_user_by_name(db_session, "TestUser") is None

    with _get_browser() as driver:
        login_ui = _register_user_via_gui(
            driver, "TestUser", "test@example.com", "secure123"
        )
        assert login_ui == "http://minitwit:5001/login_UI"

    assert _get_user_by_name(db_session, "TestUser").username == "TestUser"

    # cleanup
    _delete_user_by_name(db_session, "TestUser")

def test_login_user_via_gui(db_session: Session):
    test_username = "LoginTester"
    test_password = "secure123"

    _delete_user_by_name(db_session, test_username)
    new_user = User(
        username=test_username, 
        email="login@test.com", 
        pw_hash=generate_password_hash(test_password)
    )
    db_session.add(new_user)
    db_session.commit()
    with _get_browser() as driver:
        current_url = _login_user_via_gui(driver, test_username, test_password)
        assert current_url == "http://minitwit:5001/"
        # cleanup
        _delete_user_by_name(db_session, test_username)


def test_post_message_via_gui_and_check_db_entry(db_session: Session):
    test_username = "PostTester"
    test_password = "secure123"
    test_message = "Hello, this is a test message!"


    _delete_user_by_name(db_session, test_username)
    new_user = User(
        username=test_username, 
        email="post@test.com", 
        pw_hash=generate_password_hash(test_password)
    )
    db_session.add(new_user)
    db_session.commit()

    with _get_browser() as driver:
        # ui login and post a message
        _login_user_via_gui(driver, test_username, test_password)
        _post_message_via_gui(driver, test_message)  # <--- Using the helper now!
        
        #varify the message appears in the ui
        assert test_message in driver.page_source

    # verify the message was persisted in the database
    db_session.expire_all() 
    db_text = _get_latest_message_by_user(db_session, test_username)
    assert db_text == test_message

    # cleanup
    _delete_user_by_name(db_session, test_username)


def test_follow_and_unfollow_user_via_gui(db_session: Session):
    # making two users
    follower_name = "FollowerUser"
    following_name = "FollowingUser"
    password = "secure123"
    pw_hash = generate_password_hash(password)

    # clean up
    _delete_user_by_name(db_session, follower_name)
    _delete_user_by_name(db_session, following_name)

    # create the users in the db
    user1 = User(username=follower_name, email="follower@example.com", pw_hash=pw_hash)
    user2 = User(username=following_name, email="following@example.com", pw_hash=pw_hash)
    
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    try:
        with _get_browser() as driver:
            _login_user_via_gui(driver, follower_name, password)
            _follow_user_via_gui(driver, following_name)
            
            wait = WebDriverWait(driver, 5)
            wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Unfollow user")))
            
            # varify the button text changed to "Unfollow user"
            assert "Unfollow user" in driver.page_source

            # now unfollow and varify the button text changes back to "Follow user"
            _unfollow_user_via_gui(driver, following_name)
            wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Follow user")))
            assert "Follow user" in driver.page_source
            
    finally:
        _delete_user_by_name(db_session, follower_name)
        _delete_user_by_name(db_session, following_name)




def test_publicTimeline_shows_messages_of_all_users(db_session: Session):
    u1_name = "user1"
    u2_name = "user2"
    password = "secure123"
    pw_hash = generate_password_hash(password)

    _delete_user_by_name(db_session, u1_name)
    _delete_user_by_name(db_session, u2_name)

    user1_obj = User(username=u1_name, email="user1@example.com", pw_hash=pw_hash)
    user2_obj = User(username=u2_name, email="user2@example.com", pw_hash=pw_hash)

    db_session.add(user1_obj)
    db_session.add(user2_obj)
    db_session.commit()

    test_message = "This is a message from user2."
    message = Message(
        text=test_message, 
        author_id=user2_obj.user_id,
        pub_date=int(datetime.now().timestamp()), 
        flagged=0
    )
    db_session.add(message)
    db_session.commit()

    try:
        with _get_browser() as driver:
         
            _login_user_via_gui(driver, u1_name, password)

    
            driver.get(f"{GUI_URL}/public")
            
            # Verify the message from User 2 is visible
         
            assert test_message in driver.page_source
            assert u2_name in driver.page_source

    finally:
        _delete_user_by_name(db_session, u1_name)
        _delete_user_by_name(db_session, u2_name)


def test_userTimeline_shows_only_messages_of_followed_users(db_session: Session):
    follower_name = "followerUser"
    following_name = "followingUser"
    password = "secure123"
    pw_hash = generate_password_hash(password)

    _delete_user_by_name(db_session, follower_name)
    _delete_user_by_name(db_session, following_name)

    follower_obj = User(username=follower_name, email="follower@example.com", pw_hash=pw_hash)
    following_obj = User(username=following_name, email="following@example.com", pw_hash=pw_hash)

    db_session.add(follower_obj)
    db_session.add(following_obj)
    db_session.commit()

    test_message = "This is a message from the followed user."
    message = Message(
        text=test_message, 
        author_id=following_obj.user_id,
        pub_date=int(datetime.now().timestamp()), 
        flagged=0
    )
    db_session.add(message)
    db_session.commit()

    try:
        with _get_browser() as driver:
            _login_user_via_gui(driver, follower_name, password)

            # Initially, the message from the followed user should not be visible
            driver.get(f"{GUI_URL}/")
            assert test_message not in driver.page_source
            assert following_name not in driver.page_source

            _follow_user_via_gui(driver, following_name)

            driver.get(f"{GUI_URL}/")
            
            # Verify the message from the followed user is visible
            assert test_message in driver.page_source
            assert following_name in driver.page_source
    finally:
        _delete_user_by_name(db_session, follower_name)
        _delete_user_by_name(db_session, following_name)


def test_users_Timeline_only_shows_users_messages(db_session: Session):
    user1_name = "user1"
    user2_name = "user2"

    password = "secure123"
    pw_hash = generate_password_hash(password)

    _delete_user_by_name(db_session, user1_name)
    _delete_user_by_name(db_session, user2_name)

    user1_obj = User(username=user1_name, email="user1@example.com", pw_hash=pw_hash)
    user2_obj = User(username=user2_name, email="user2@example.com", pw_hash=pw_hash)

    db_session.add(user1_obj)
    db_session.add(user2_obj)
    db_session.commit()

    test_message_user1 = "Message from user1."
    test_message_user2 = "Message from user2."

    message1 = Message(
        text=test_message_user1, 
        author_id=user1_obj.user_id,
        pub_date=int(datetime.now().timestamp()), 
        flagged=0
    )
    message2 = Message(
        text=test_message_user2, 
        author_id=user2_obj.user_id,
        pub_date=int(datetime.now().timestamp()), 
        flagged=0
    )
    db_session.add(message1)
    db_session.add(message2)
    db_session.commit()

    try:
        with _get_browser() as driver:
            _login_user_via_gui(driver, user1_name, password)

            driver.get(f"{GUI_URL}/{user1_name}")
            
            # Verify only user1's message is visible
            assert test_message_user1 in driver.page_source
            assert test_message_user2 not in driver.page_source

            driver.get(f"{GUI_URL}/{user2_name}")
            assert test_message_user2 in driver.page_source
            assert test_message_user1 not in driver.page_source 
            
    finally:
        _delete_user_by_name(db_session, user1_name)
        _delete_user_by_name(db_session, user2_name)
