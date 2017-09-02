import re
import unittest

from flask import url_for

from app import db, create_app
from app.models import User, Role


class UserViewTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client(use_cookies=True)
        u = User(username='foo', password='bar')
        u.confirmed = True
        u.role = Role.get('Administrator')
        db.session.add(u)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_should_not_be_visible_if_logged_out(self):
        response = self.client.get(url_for('main.user', username='foo'), follow_redirects=True)

        self.assertTrue(re.search(b'Login', response.data))
