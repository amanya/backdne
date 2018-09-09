import re
import unittest

from flask import url_for

from app import db, create_app
from app.main.views import edit_profile_admin
from app.models import User, Role


class EditProfileAdminTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client(use_cookies=True)
        u = User(username='foo', password='bar')
        u.confirmed = True
        u.enabled = True
        r = Role.query.filter_by(name='Administrator').first()
        u.role = r
        db.session.add(u)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_admin_login(self):
        response = self.client.post(url_for('auth.login'), data={
            'username': 'foo',
            'password': 'bar'
        }, follow_redirects=True)

        self.assertTrue(re.search(b'Hello,\s+foo!', response.data))

    def test_edit_admin_profile(self):
        response = self.client.post(url_for('auth.login'), data={
            'username': 'foo',
            'password': 'bar'
        }, follow_redirects=True)

        u1 = User(username='user1', password='bar')
        u2 = User(username='user2', password='bar')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        response = self.client.post(url_for('main.edit_profile_admin', id=u1.id), data={
            'username': u1.username,
            'email': u1.email,
            'confirmed': u1.confirmed,
            'enabled': u1.enabled,
            'role': u1.role_id,
            'name': u1.name,
        }, follow_redirects=True)

        response = self.client.post(url_for('main.edit_profile_admin', id=u2.id), data={
            'username': u2.username,
            'email': u2.email,
            'confirmed': u2.confirmed,
            'enabled': u2.enabled,
            'role': u2.role_id,
            'name': u2.name,
        }, follow_redirects=True)

        self.assertTrue(re.search(b'user2', response.data))
        self.assertTrue(re.search(b'Edit Profile', response.data))

