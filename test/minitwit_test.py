# -*- coding: utf-8 -*-
"""
MiniTwit Tests
~~~~~~~~~~~~~~

Tests the MiniTwit application.

:copyright: (c) 2010 by Armin Ronacher.
:license: BSD, see LICENSE for more details.
"""

import unittest
import requests
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from follower import Follower
from user import User
from message import Message
from conftest import GUI_URL


class MiniTwitTestCase(unittest.TestCase):

    def setUp(self):
        self.session = requests.Session()

    def tearDown(self):
        self.session.close()

    def register(self, username, password, password2=None, email=None):
        """Helper function to register a user"""
        if password2 is None:
            password2 = password
        if email is None:
            email = username + "@example.com"

        return self.session.post(
            f"{GUI_URL}/register_UI",
            data={
                "username": username,
                "password": password,
                "password2": password2,
                "email": email,
            },
            allow_redirects=True,
        )

    def login(self, username, password):
        """Helper function to login"""
        return self.session.post(
            f"{GUI_URL}/login_UI",
            data={"username": username, "password": password},
            allow_redirects=True,
        )

    def register_and_login(self, username, password):
        """Registers and logs in in one go"""
        self.register(username, password)
        return self.login(username, password)

    def logout(self):
        """Helper function to logout"""
        return self.session.get(f"{GUI_URL}/logout_UI", allow_redirects=True)

    def add_message(self, text):
        """Records a message"""
        rv = self.session.post(f"{GUI_URL}/add_message", data={"text": text})
        if text:
            assert "Your message was recorded" in rv.text
        return rv

    # testing functions

    def test_register(self):
        """Make sure registering works"""
        rv = self.register("user1", "default")
        assert "You were successfully registered and can login now" in rv.text
        rv = self.register("user1", "default")
        assert "The username is already taken" in rv.text
        rv = self.register("", "default")
        assert "You have to enter a username" in rv.text
        rv = self.register("meh", "")
        assert "You have to enter a password" in rv.text
        rv = self.register("meh", "x", "y")
        assert "The two passwords do not match" in rv.text
        rv = self.register("meh", "foo", email="broken")
        assert "You have to enter a valid email address" in rv.text

    def test_login_logout(self):
        """Make sure logging in and logging out works"""
        # register first since each fixture is indpendent
        rv = self.register("user2", "default")
        assert "You were successfully registered and can login now" in rv.text
        rv = self.login("user2", "default")
        assert "You were logged in" in rv.text
        rv = self.logout()
        assert "You were logged out" in rv.text
        rv = self.login("user2", "wrongpassword")
        assert "Invalid password" in rv.text
        rv = self.login("user1", "wrongpassword")
        assert "Invalid username" in rv.text

    def test_message_recording(self):
        """Check if adding messages works"""
        self.register_and_login("foo", "default")
        self.add_message("test message 1")
        self.add_message("<test message 2>")
        rv = self.session.get(f"{GUI_URL}/")
        assert "test message 1" in rv.text
        assert "&lt;test message 2&gt;" in rv.text

    def test_timelines(self):
        """Make sure that timelines work"""
        self.register_and_login("foo", "default")
        self.add_message("the message by foo")
        self.logout()
        self.register_and_login("bar", "default")
        self.add_message("the message by bar")
        rv = self.session.get(f"{GUI_URL}/public", allow_redirects=True)

        assert "the message by foo" in rv.text
        assert "the message by bar" in rv.text

        # bar's timeline should just show bar's message
        rv = self.session.get(f"{GUI_URL}/bar", allow_redirects=True)

        assert "the message by foo" not in rv.text
        assert "the message by bar" in rv.text

        # now let's follow foo
        rv = self.session.get(f"{GUI_URL}/foo/follow", allow_redirects=True)
        assert "You are now following &#34;foo&#34;" in rv.text

        # we should now see foo's message
        rv = self.session.get(f"{GUI_URL}")
        assert "the message by foo" in rv.text
        assert "the message by bar" in rv.text

        # but on the user's page we only want the user's message
        rv = self.session.get(f"{GUI_URL}/bar")
        assert "the message by foo" not in rv.text
        assert "the message by bar" in rv.text
        rv = self.session.get(f"{GUI_URL}/foo")
        assert "the message by foo" in rv.text
        assert "the message by bar" not in rv.text

        # now unfollow and check if that worked
        rv = self.session.get(f"{GUI_URL}/foo/unfollow", allow_redirects=True)
        assert "You are no longer following &#34;foo&#34;" in rv.text
        rv = self.session.get(f"{GUI_URL}/")
        assert "the message by foo" not in rv.text
        assert "the message by bar" in rv.text


if __name__ == "__main__":

    unittest.main()
