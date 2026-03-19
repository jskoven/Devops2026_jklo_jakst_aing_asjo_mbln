import os
import json
import base64
import sqlite3
import requests
from pathlib import Path
from contextlib import closing
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from follower import Follower
from user import User
from message import Message
from sqlmodel import SQLModel, Session, create_engine
import pytest
from conftest import GUI_URL

# GUI_URL = os.getenv('TEST_URL', 'http://localhost:5001')
# DATABASE = "/tmp/minitwit_test.db"
USERNAME = "simulator"
PWD = "super_safe!"
CREDENTIALS = ":".join([USERNAME, PWD]).encode("ascii")
ENCODED_CREDENTIALS = base64.b64encode(CREDENTIALS).decode()
HEADERS = {
    "Connection": "close",
    "Content-Type": "application/json",
    f"Authorization": f"Basic {ENCODED_CREDENTIALS}",
}
# test_db_url = f"sqlite:///{DATABASE}"
# test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})

# def init_db():
#     """Creates the database tables."""
#     SQLModel.metadata.create_all(test_engine)

# @pytest.fixture(scope="module", autouse=True)
# def cleanup_database():
#     yield
#     if os.path.exists(DATABASE):
#         os.remove(DATABASE)


def test_latest():
    # post something to update LATEST
    url = f"{GUI_URL}/register"
    data = {"username": "test", "email": "test@test", "pwd": "foo"}
    params = {"latest": 1337}
    response = requests.post(url, data=json.dumps(data), params=params, headers=HEADERS)
    assert response.ok

    # verify that latest was updated
    url = f"{GUI_URL}/latest"
    response = requests.get(url, headers=HEADERS)
    assert response.ok
    assert response.json()["latest"] == 1337


def test_register():
    username = "a"
    email = "a_test@a.a"
    pwd = "a"
    data = {"username": username, "email": email, "pwd": pwd}
    params = {"latest": 1}
    response = requests.post(
        f"{GUI_URL}/register", data=json.dumps(data), headers=HEADERS, params=params
    )
    assert response.ok
    # TODO: add another assertion that it is really there

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 1


def test_create_msg():
    username = "a"
    data = {"content": "Blub!"}
    url = f"{GUI_URL}/msgs/{username}"
    params = {"latest": 2}
    response = requests.post(url, data=json.dumps(data), headers=HEADERS, params=params)
    assert response.ok

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 2


def test_get_latest_user_msgs():
    username = "a"

    query = {"no": 20, "latest": 3}
    url = f"{GUI_URL}/msgs/{username}"
    response = requests.get(url, headers=HEADERS, params=query)
    assert response.status_code == 200

    got_it_earlier = False
    for msg in response.json():
        if msg["content"] == "Blub!" and msg["user"] == username:
            got_it_earlier = True

    assert got_it_earlier

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 3


def test_get_latest_msgs():
    username = "a"
    query = {"no": 20, "latest": 4}
    url = f"{GUI_URL}/msgs"
    response = requests.get(url, headers=HEADERS, params=query)
    assert response.status_code == 200

    got_it_earlier = False
    for msg in response.json():
        if msg["content"] == "Blub!" and msg["user"] == username:
            got_it_earlier = True

    assert got_it_earlier

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 4


def test_register_b():
    username = "b"
    email = "b@b.b"
    pwd = "b"
    data = {"username": username, "email": email, "pwd": pwd}
    params = {"latest": 5}
    response = requests.post(
        f"{GUI_URL}/register", data=json.dumps(data), headers=HEADERS, params=params
    )
    assert response.ok
    # TODO: add another assertion that it is really there

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 5


def test_register_c():
    username = "c"
    email = "c@c.c"
    pwd = "c"
    data = {"username": username, "email": email, "pwd": pwd}
    params = {"latest": 6}
    response = requests.post(
        f"{GUI_URL}/register", data=json.dumps(data), headers=HEADERS, params=params
    )
    assert response.ok

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 6


def test_follow_user():
    username = "a"
    url = f"{GUI_URL}/fllws/{username}"
    data = {"follow": "b"}
    params = {"latest": 7}
    response = requests.post(url, data=json.dumps(data), headers=HEADERS, params=params)
    assert response.ok

    data = {"follow": "c"}
    params = {"latest": 8}
    response = requests.post(url, data=json.dumps(data), headers=HEADERS, params=params)
    assert response.ok

    query = {"no": 20, "latest": 9}
    response = requests.get(url, headers=HEADERS, params=query)
    assert response.ok

    json_data = response.json()
    assert "b" in json_data["follows"]
    assert "c" in json_data["follows"]

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 9


def test_a_unfollows_b():
    username = "a"
    url = f"{GUI_URL}/fllws/{username}"

    #  first send unfollow command
    data = {"unfollow": "b"}
    params = {"latest": 10}
    response = requests.post(url, data=json.dumps(data), headers=HEADERS, params=params)
    assert response.ok

    # then verify that b is no longer in follows list
    query = {"no": 20, "latest": 11}
    response = requests.get(url, params=query, headers=HEADERS)
    assert response.ok
    assert "b" not in response.json()["follows"]

    # verify that latest was updated
    response = requests.get(f"{GUI_URL}/latest", headers=HEADERS)
    assert response.json()["latest"] == 11
