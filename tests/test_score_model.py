import unittest

from app import create_app, db
from app.models import User, AnonymousUser, Role, Permission, UserSchool, Score


class ScoreModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_score(self):
        u = User(email='john@example.com', password='cat')
        s = Score(user_id=u.id, game="test", score=10, max_score=20, duration=2, state="state", is_exam=True)
        self.assertIn('is_exam', s.to_json().keys())
