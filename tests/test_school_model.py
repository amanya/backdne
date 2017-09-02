import unittest

from app import create_app, db
from app.exceptions import ValidationError
from app.models import School, User, Role


class SchoolModelTestCase(unittest.TestCase):
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

    def test_add_teacher(self):
        s = School(name="Test")
        u = User(username="test")
        with self.assertRaises(ValidationError):
            s.add_teacher(u)
        u.role = Role.get('Teacher')
        s.add_teacher(u)
        db.session.add(s)
        db.session.commit()
        self.assertEquals([u], s.teachers.all())

    def test_add_student(self):
        s = School(name="Test")
        u = User(username="test")
        u.role = Role.get('Teacher')
        with self.assertRaises(ValidationError):
            s.add_student(u)
        u.role = Role.get('Student')
        s.add_student(u)
        db.session.add(s)
        db.session.commit()
        self.assertEquals([u], s.students.all())

    def test_teachers_only_returns_teachers(self):
        s = School(name="Test")
        u1 = User(username="u1", email='student1@example.com')
        u2 = User(username="u2", email='student2@example.com')
        u3 = User(username="u3", email='teacher1@example.com')
        u3.role = Role.get('Teacher')
        u4 = User(username="u4", email='teacher2@example.com')
        u4.role = Role.get('Teacher')
        s.add_student(u1)
        s.add_student(u2)
        s.add_teacher(u3)
        s.add_teacher(u4)
        db.session.add(s)
        db.session.commit()
        self.assertListEqual([u3, u4], s.teachers.all())

    def test_students_only_returns_students(self):
        s = School(name="Test")
        u1 = User(username="u1", email='student1@example.com')
        u2 = User(username="u2", email='student2@example.com')
        u3 = User(username="u3", email='teacher1@example.com')
        u3.role = Role.get('Teacher')
        u4 = User(username="u4", email='teacher2@example.com')
        u4.role = Role.get('Teacher')
        s.add_student(u1)
        s.add_student(u2)
        s.add_teacher(u3)
        s.add_teacher(u4)
        db.session.add(s)
        db.session.commit()
        self.assertListEqual([u1, u2], s.students.all())
