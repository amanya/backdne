import unittest
import json
import re
from base64 import b64encode

import datetime
from flask import url_for
from app import create_app, db
from app.models import User, Role, School, Lesson, Score, Screen


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
        r = Role.get('Student')
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
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Student'))
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
            headers=self.get_api_headers('john', 'cat'))
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

    def test_schools(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        # create a school
        response = self.client.post(
            url_for('api.new_school'),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps({'name': 'school'}))
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIsNotNone(url)

        # get the new school
        response = self.client.get(
            url,
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['name'] == 'school')

        # edit school
        response = self.client.put(
            url,
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps({'name': 'updated_name'}))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['name'] == 'updated_name')

        # add student to school
        school_id = json_response['id']
        student = User(email='student@example.com', password='dog', username='student', confirmed=True,
                       role=Role.get('Student'))
        db.session.add(student)
        db.session.commit()

        response = self.client.put(
            url_for('api.add_student_to_school', id=school_id),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps({'id': student.id})
        )
        self.assertTrue(response.status_code == 200)

        response = self.client.get(
            url_for('api.get_students', id=school_id),
            headers=self.get_api_headers('john', 'cat')
        )
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(len(json_response['students']) == 1)
        self.assertTrue(json_response['students'][0]['username'] == 'student')

        # add teacher to school
        teacher = User(email='teacher@example.com', password='dog', username='teacher', confirmed=True,
                       role=Role.get('Teacher'))
        db.session.add(teacher)
        db.session.commit()

        response = self.client.put(
            url_for('api.add_teacher_to_school', id=school_id),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps({'id': teacher.id})
        )
        self.assertTrue(response.status_code == 200)

        response = self.client.get(
            url_for('api.get_teachers', id=school_id),
            headers=self.get_api_headers('john', 'cat')
        )
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(len(json_response['teachers']) == 1)
        self.assertTrue(json_response['teachers'][0]['username'] == 'teacher')

    def test_users(self):
        # add two users
        r = Role.get('Student')
        self.assertIsNotNone(r)
        u1 = User(email='john@example.com', username='john',
                  password='cat', confirmed=True, role=r)
        u2 = User(email='susan@example.com', username='susan',
                  password='dog', confirmed=True, role=r)
        db.session.add_all([u1, u2])
        db.session.commit()

        # get users
        response = self.client.get(
            url_for('api.get_user', username=u1.username),
            headers=self.get_api_headers('susan', 'dog'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['username'] == 'john')
        response = self.client.get(
            url_for('api.get_user', username=u2.username),
            headers=self.get_api_headers('susan', 'dog'))
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

    def test_cant_login_if_user_disabled(self):
        u = User(username='john', password='cat', confirmed=True, enabled=False)
        db.session.add(u)
        db.session.commit()

        response = self.client.post(
            url_for('api.login'),
            data=json.dumps({'username': 'john', 'password': 'cat'})
        )
        self.assertTrue(response.status_code == 401)

    def test_create_score(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        # create a score
        response = self.client.post(
            url_for('api.create_score'),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps(
                {"game": "game_test", "score": "17", "max_score": "32", "duration": "64", "state": "running"}))
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIsNotNone(url)

        # get the new score
        response = self.client.get(
            url,
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['game'] == 'game_test')

    def test_get_user_game_max_score_not_found(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        response = self.client.get(
            url_for('api.get_user_game_max_score', username=u.username, game='some-test'),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 404)

    def test_get_user_game_max_score(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        # create some scores
        response = self.client.post(
            url_for('api.create_score'),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps(
                {"game": "game_test", "score": "17", "max_score": "32", "duration": "64", "state": "running"}))

        response = self.client.post(
            url_for('api.create_score'),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps(
                {"game": "game_test", "score": "21", "max_score": "32", "duration": "64", "state": "running"}))

        # get the new score
        response = self.client.get(
            url_for('api.get_user_game_max_score', username=u.username, game='game_test'),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['max_score'] == 21)

    def test_get_user_game_scores(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        scores = [
            (datetime.datetime(2017, 1, 3, 0, 0, 0),
             {"user_id": u.id, "game": "game_test", "score": 17, "max_score": 32, "duration": 64, "state": "running",
              "is_exam": True},),
            (datetime.datetime(2017, 1, 2, 0, 0, 0),
             {"user_id": u.id, "game": "game_test", "score": 7, "max_score": 32, "duration": 64, "state": "running",
              "is_exam": True},),
            (datetime.datetime(2017, 1, 1, 0, 0, 0),
             {"user_id": u.id, "game": "game_test", "score": 27, "max_score": 32, "duration": 64, "state": "running",
              "is_exam": True},),
            (datetime.datetime(2017, 1, 1, 0, 0, 0),
             {"user_id": u.id, "game": "game_test_2", "score": 27, "max_score": 32, "duration": 64, "state": "running",
              "is_exam": True},),
        ]

        for d, s in scores:
            s = Score(**s)
            s.created = d
            db.session.add(s)
        db.session.commit()

        # get the new score
        response = self.client.get(
            url_for('api.last_scores_game') + '?game=game_test',
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        expected = [s[1] for s in sorted(scores, key=lambda k: k[0]) if s[1]["game"] == "game_test"]
        scores = json_response["scores"]

        for a, b in zip(expected, scores):
            self.assertEquals(a["score"], b["score"])

    def test_create_lesson(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        lesson = {"lesson": "the_lesson", "total_pages_viewed": 1, "clicks_forward": 2, "clicks_backward": 3,
                  "clicks_menu": 4, "clicks_lesson_repeat": 5, "way_exit": "asdf", "is_finished": True, "time": 6}

        # create a lesson
        response = self.client.post(
            url_for('api.create_lesson'),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps(lesson))
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIsNotNone(url)

        # get the new lesson
        response = self.client.get(
            url,
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        for k, v in lesson.items():
            self.assertEquals(json_response[k], v)

    def test_get_finished_lessons(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True,
                 role=Role.get('Administrator'))
        db.session.add(u)
        db.session.commit()

        ls = [
            Lesson(lesson="lesson1", user_id=u.id, is_finished=False),
            Lesson(lesson="lesson1", user_id=u.id, is_finished=False),
            Lesson(lesson="lesson2", user_id=u.id, is_finished=False),
            Lesson(lesson="lesson2", user_id=u.id, is_finished=True),
            Lesson(lesson="lesson3", user_id=u.id, is_finished=True),
            Lesson(lesson="lesson3", user_id=u.id, is_finished=True)
        ]

        for l in ls:
            db.session.add(l)

        db.session.commit()

        response = self.client.get(
            url_for('api.get_finished_lessons'),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        expected = {
            "lesson1": False,
            "lesson2": True,
            "lesson3": True,
        }

        self.assertEqual(json_response, expected)

    def test_update(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        response = self.client.post(
            url_for('api.post_user', username=u.username),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps({"username": "pepe"})
        )

        response = self.client.get(
            url_for('api.get_user', username=u.username),
            headers=self.get_api_headers('pepe', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        self.assertEqual(json_response["username"], "pepe")


    def test_last_scores(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        scores = [
            (datetime.datetime(2017, 1, 1, 0, 0, 0),
            {"game": "game1", "score": 10}),
            (datetime.datetime(2017, 1, 2, 0, 0, 0),
            {"game": "game1", "score": 12}),
            (datetime.datetime(2017, 1, 3, 0, 0, 0),
            {"game": "game2", "score": 13}),
            (datetime.datetime(2017, 1, 4, 0, 0, 0),
            {"game": "game3", "score": 14}),
        ]
        for d, s in scores:
            s = Score(user_id=u.id, state='finished', **s)
            s.created = d
            db.session.add(s)
        db.session.commit()

        response = self.client.get(
            url_for('api.last_scores'),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        items = []
        for item in json_response["scores"]:
            items.append(item["score"])

        expected = [12, 13, 14]

        self.assertEqual(items, expected)


    def test_best_scores(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        scores = [
            Score(user_id=u.id, state='finished', game='game1', score=10),
            Score(user_id=u.id, state='finished', game='game1', score=12),
            Score(user_id=u.id, state='finished', game='game1', score=14),
            Score(user_id=u.id, state='finished', game='game2', score=12),
            Score(user_id=u.id, state='finished', game='game2', score=14),
            Score(user_id=u.id, state='finished', game='game3', score=15),
            Score(user_id=u.id, state='finished', game='game3', score=16),
        ]
        for s in scores:
            db.session.add(s)

        db.session.commit()

        response = self.client.get(
            url_for('api.best_scores'),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        items = []
        for item in json_response["scores"]:
            items.append(item["score"])
        items.sort()

        expected = [14, 14, 16]

        self.assertEqual(items, expected)

    def test_best_scores_by_game(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        scores = [
            Score(user_id=u.id, state='finished', game='game1', score=10),
            Score(user_id=u.id, state='finished', game='game1', score=12),
            Score(user_id=u.id, state='finished', game='game1', score=14),
            Score(user_id=u.id, state='finished', game='game2', score=12),
            Score(user_id=u.id, state='finished', game='game2', score=14),
            Score(user_id=u.id, state='finished', game='game3', score=15),
            Score(user_id=u.id, state='finished', game='game3', score=16),
        ]
        for s in scores:
            db.session.add(s)

        db.session.commit()

        response = self.client.get(
            url_for('api.best_scores') + '?game=game1',
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        items = []
        for item in json_response["scores"]:
            items.append(item["score"])
        items.sort()

        expected = [14]

        self.assertEqual(items, expected)


    def test_all_scores(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        scores = [
            {"game": "game1", "score": 10, "is_exam": True},
            {"game": "game1", "score": 12, "is_exam": True},
            {"game": "game2", "score": 13, "is_exam": True},
            {"game": "game3", "score": 14, "is_exam": False},
        ]
        for s in scores:
            s = Score(user_id=u.id, state='finished', **s)
            db.session.add(s)
        db.session.commit()

        response = self.client.get(
            url_for('api.all_scores'),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        items = []
        for item in json_response["scores"]:
            items.append(item["score"])

        expected = [10, 12, 13, 14]

        self.assertEqual(items, expected)

    def test_create_screen(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        screen = {
                'name': 'screen1',
                'action': 'action1',
                'duration': 12
        }

        response = self.client.post(
            url_for('api.create_screen'),
            headers=self.get_api_headers('john', 'cat'),
            data=json.dumps(screen))
        self.assertTrue(response.status_code == 201)

        data = json.loads(response.data.decode('utf-8'))

        s = Screen.query.filter_by(name=screen['name']).first()

        self.assertEquals(s.id, data['id'])
        self.assertEquals(u.id, data['user_id'])
        self.assertEquals(screen['name'], data['name'])
        self.assertEquals(screen['action'], data['action'])
        self.assertEquals(screen['duration'], data['duration'])


    def test_get_screen(self):
        # add a user
        u = User(username='john', password='cat', confirmed=True)
        db.session.add(u)
        db.session.commit()

        screen = {
                'name': 'screen1',
                'action': 'action1',
                'duration': 12
        }

        s = Screen(user_id=u.id, **screen)
        db.session.add(s)
        db.session.commit()

        response = self.client.get(
            url_for('api.get_screen', id = s.id),
            headers=self.get_api_headers('john', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))

        self.assertEquals(json_response['id'], s.id)
        self.assertEquals(json_response['user_id'], u.id)
        self.assertEquals(json_response['name'], screen['name'])
        self.assertEquals(json_response['action'], screen['action'])
        self.assertEquals(json_response['duration'], screen['duration'])
