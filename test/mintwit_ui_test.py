"""
To run this test with a visible browser, the following dependencies have to be setup:

  * `pip install selenium`
  * `pip install pymongo`
  * `pip install pytest`
  * `wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz`
  * `tar xzvf geckodriver-v0.32.0-linux64.tar.gz`
  * After extraction, the downloaded artifact can be removed: `rm geckodriver-v0.32.0-linux64.tar.gz`

The application that it tests is the version of _ITU-MiniTwit_ that you got to know during the exercises on Docker:
https://github.com/itu-devops/flask-minitwit-mongodb/tree/Containerize (*OBS*: branch Containerize)

```bash
$ git clone https://github.com/HelgeCPH/flask-minitwit-mongodb.git
$ cd flask-minitwit-mongodb
$ git switch Containerize
```

After editing the `docker-compose.yml` file file where you replace `youruser` with your respective username, the
application can be started with `docker-compose up`.

Now, the test itself can be executed via: `pytest test_itu_minitwit_ui.py`.
"""
from shutil import which
from typing import Annotated
from fastapi import Depends
import pytest
from sqlmodel import SQLModel, Session, create_engine, select, text
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from user import User
from conftest import GUI_URL,TEST_DB_URL

def _get_browser():
    options = Options()
    options.add_argument("--headless")
    return webdriver.Firefox(service=Service(which("geckodriver")), options=options)


def _register_user_via_gui(driver,username, email, password):
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


def _get_user_by_name(session:Session, username):
    return session.exec(select(User).where(User.username == username)).first()


def _delete_user_by_name(db_session:Session, username):
    user = _get_user_by_name(db_session, username)
    if user:
        db_session.delete(user)
        db_session.commit()


def test_register_user_via_gui(db_session:Session):
    """UI test — only checks what the user sees in the browser."""
    with _get_browser() as driver:
        login_ui = _register_user_via_gui(driver, "TestUser", "test@example.com", "secure123")
        assert login_ui == "http://minitwit:5001/login_UI"

    # cleanup — ensures test is idempotent
    _delete_user_by_name(db_session, "TestUser")


def test_register_user_via_gui_and_check_db_entry(db_session:Session):
    """End-to-end test — verifies the UI action actually persisted to the DB."""
    assert _get_user_by_name(db_session, "TestUser") is None

    with _get_browser() as driver:
        login_ui = _register_user_via_gui(driver,"TestUser", "test@example.com", "secure123")
        assert login_ui == "http://minitwit:5001/login_UI"

    assert _get_user_by_name(db_session, "TestUser").username == "TestUser"

    # cleanup
    _delete_user_by_name(db_session, "TestUser")