import unittest
import time
from datetime import datetime
from app import create_app, db
from app.models import Role, Lesson


class LessonModelTestCase(unittest.TestCase):
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

    def test_to_json(self):
        l = Lesson()
        db.session.add(l)
        db.session.commit()
        json_ = l.to_json()
        expected_keys = ['id', 'user_id', 'lesson', 'total_pages_viewed',
                         'clicks_forward', 'clicks_backward', 'clicks_menu',
                         'clicks_lesson_repeat', 'way_exit', 'is_finished',
                         'time', 'created']
        self.assertEqual(sorted(json_.keys()), sorted(expected_keys))

    def test_get_finished_lessons(self):
        ls = [Lesson(lesson="lesson1", user_id=1, is_finished=False),
              Lesson(lesson="lesson1", user_id=1, is_finished=False),
              Lesson(lesson="lesson2", user_id=1, is_finished=False),
              Lesson(lesson="lesson2", user_id=1, is_finished=True),
              Lesson(lesson="lesson3", user_id=1, is_finished=True),
              Lesson(lesson="lesson3", user_id=1, is_finished=True),
              Lesson(lesson="lesson1", user_id=2, is_finished=True),
              Lesson(lesson="lesson1", user_id=2, is_finished=True),
              Lesson(lesson="lesson4", user_id=2, is_finished=False),
              Lesson(lesson="lesson4", user_id=2, is_finished=False)]

        for l in ls:
            db.session.add(l)

        db.session.commit()

        finished_lessons = Lesson.get_finished_lessons(1)

        expected = {
            "lesson1": False,
            "lesson2": True,
            "lesson3": True,
        }

        self.assertEqual(finished_lessons, expected)

