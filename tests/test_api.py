import unittest
import json
import re
from base64 import b64encode
from flask import url_for
from app import create_app, db
from app.models import User, Role, School


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def get_api_headers(self, username, password):
        return {
            'Authorization': 'Basic ' + b64encode(
                (username + ':' + password).encode('utf-8')).decode('utf-8'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def test_404(self):
        response = self.client.get(
            '/wrong/url',
            headers=self.get_api_headers('email', 'password'))
        self.assertTrue(response.status_code == 404)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['error'] == 'not found')

    def test_no_auth(self):
        response = self.client.get(url_for('api.get_schools'),
                                   content_type='application/json')
        self.assertTrue(response.status_code == 200)

    def test_bad_auth(self):
        # add a user
        r = Role.query.filter_by(name='Student').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=True,
                 role=r)
        db.session.add(u)
        db.session.commit()

        # authenticate with bad password
        response = self.client.get(
            url_for('api.get_schools'),
            headers=self.get_api_headers('john@example.com', 'dog'))
        self.assertTrue(response.status_code == 401)

    def test_token_auth(self):
        # add a user
        r = Role.query.filter_by(name='Student').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=True,
                 role=r)
        db.session.add(u)
        db.session.commit()

        # issue a request with a bad token
        response = self.client.get(
            url_for('api.get_schools'),
            headers=self.get_api_headers('bad-token', ''))
        self.assertTrue(response.status_code == 401)

        # get a token
        response = self.client.get(
            url_for('api.get_token'),
            headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(json_response.get('token'))
        token = json_response['token']

        # issue a request with the token
        response = self.client.get(
            url_for('api.get_schools'),
            headers=self.get_api_headers(token, ''))
        self.assertTrue(response.status_code == 200)

    def test_anonymous(self):
        response = self.client.get(
            url_for('api.get_schools'),
            headers=self.get_api_headers('', ''))
        self.assertTrue(response.status_code == 200)

    def test_unconfirmed_account(self):
        # add an unconfirmed user
        r = Role.query.filter_by(name='Student').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=False,
                 role=r)
        db.session.add(u)
        db.session.commit()

        # get list of posts with the unconfirmed account
        response = self.client.get(
            url_for('api.get_schools'),
            headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 403)

    def test_schools(self):
        # add a user
        r = Role.query.filter_by(name='Administrator').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=True,
                 role=r)
        db.session.add(u)
        db.session.commit()

        # create a school
        response = self.client.post(
            url_for('api.new_school'),
            headers=self.get_api_headers('john@example.com', 'cat'),
            data=json.dumps({'name': 'school'}))
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIsNotNone(url)

        # get the new school
        response = self.client.get(
            url,
            headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['name'] == 'school')

        # edit school
        response = self.client.put(
            url,
            headers=self.get_api_headers('john@example.com', 'cat'),
            data=json.dumps({'name': 'updated_name'}))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['name'] == 'updated_name')

        # add student to school
        school_id = json_response['id']
        student_role = Role.query.filter_by(name='Student').first()
        student = User(email='student@example.com', password='dog', username='student', confirmed=True, role=student_role)
        db.session.add(student)
        db.session.commit()

        response = self.client.put(
            url_for('api.add_student_to_school', id=school_id),
            headers=self.get_api_headers('john@example.com', 'cat'),
            data=json.dumps({'id': student.id})
        )
        self.assertTrue(response.status_code == 200)

        response = self.client.get(
            url_for('api.get_students', id=school_id),
            headers=self.get_api_headers('john@example.com', 'cat')
        )
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(len(json_response['students']) == 1)
        self.assertTrue(json_response['students'][0]['username'] == 'student')

        # add teacher to school
        teacher_role = Role.query.filter_by(name='Teacher').first()
        teacher = User(email='teacher@example.com', password='dog', username='teacher', confirmed=True, role=teacher_role)
        db.session.add(teacher)
        db.session.commit()

        response = self.client.put(
            url_for('api.add_teacher_to_school', id=school_id),
            headers=self.get_api_headers('john@example.com', 'cat'),
            data=json.dumps({'id': teacher.id})
        )
        self.assertTrue(response.status_code == 200)

        response = self.client.get(
            url_for('api.get_teachers', id=school_id),
            headers=self.get_api_headers('john@example.com', 'cat')
        )
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(len(json_response['teachers']) == 1)
        self.assertTrue(json_response['teachers'][0]['username'] == 'teacher')

    def test_users(self):
        # add two users
        r = Role.query.filter_by(name='Student').first()
        self.assertIsNotNone(r)
        u1 = User(email='john@example.com', username='john',
                  password='cat', confirmed=True, role=r)
        u2 = User(email='susan@example.com', username='susan',
                  password='dog', confirmed=True, role=r)
        db.session.add_all([u1, u2])
        db.session.commit()

        # get users
        response = self.client.get(
            url_for('api.get_user', id=u1.id),
            headers=self.get_api_headers('susan@example.com', 'dog'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['username'] == 'john')
        response = self.client.get(
            url_for('api.get_user', id=u2.id),
            headers=self.get_api_headers('susan@example.com', 'dog'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['username'] == 'susan')

    def test_login(self):
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        response = self.client.post(
            url_for('api.login'),
            data=json.dumps({'username': 'john', 'password': 'dog'})
        )
        self.assertTrue(response.status_code == 401)

        response = self.client.post(
            url_for('api.login'),
            data=json.dumps({'username': 'john', 'password': 'cat'})
        )
        self.assertTrue(response.status_code == 200)

        response = self.client.post(
            url_for('api.login'),
            data=json.dumps({'username': 'pepe', 'password': 'cat'})
        )
        self.assertTrue(response.status_code == 401)

