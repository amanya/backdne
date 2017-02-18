import unittest
import time
from datetime import datetime
from app import create_app, db
from app.models import User, AnonymousUser, Role, Permission, UserSchool


class UserModelTestCase(unittest.TestCase):
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

    def test_password_setter(self):
        u = User(password='cat')
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self):
        u = User(password='cat')
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(password='cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self):
        u = User(password='cat')
        u2 = User(password='cat')
        self.assertTrue(u.password_hash != u2.password_hash)

    def test_valid_confirmation_token(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm(token))

    def test_invalid_confirmation_token(self):
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm(token))

    def test_expired_confirmation_token(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token(1)
        time.sleep(2)
        self.assertFalse(u.confirm(token))

    def test_valid_reset_token(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_reset_token()
        self.assertTrue(u.reset_password(token, 'dog'))
        self.assertTrue(u.verify_password('dog'))

    def test_invalid_reset_token(self):
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_reset_token()
        self.assertFalse(u2.reset_password(token, 'horse'))
        self.assertTrue(u2.verify_password('dog'))

    def test_valid_email_change_token(self):
        u = User(email='john@example.com', password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_email_change_token('susan@example.org')
        self.assertTrue(u.change_email(token))
        self.assertTrue(u.email == 'susan@example.org')

    def test_invalid_email_change_token(self):
        u1 = User(email='john@example.com', password='cat')
        u2 = User(email='susan@example.org', password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_email_change_token('david@example.net')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'susan@example.org')

    def test_duplicate_email_change_token(self):
        u1 = User(email='john@example.com', password='cat')
        u2 = User(email='susan@example.org', password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u2.generate_email_change_token('john@example.com')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'susan@example.org')

    def test_roles_and_permissions(self):
        u = User(email='john@example.com', password='cat')
        self.assertTrue(u.can(Permission.EXIST))
        self.assertFalse(u.can(Permission.CREATE_USERS))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.CREATE_USERS))

    def test_timestamps(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        self.assertTrue(
            (datetime.utcnow() - u.created).total_seconds() < 3)
        self.assertTrue(
            (datetime.utcnow() - u.updated).total_seconds() < 3)

    def test_ping(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        time.sleep(2)
        last_seen_before = u.updated
        u.ping()
        self.assertTrue(u.updated > last_seen_before)

    def test_tutorial(self):
        u = User(username='felix', password='cat')
        u.tutorial_completed = True
        db.session.add(u)
        db.session.commit()
        u = User.query.filter_by(username='felix').first()
        self.assertTrue(u.tutorial_completed)

    def test_exam_points(self):
        u = User(username='felix', password='cat')
        u.exam_points = 10
        db.session.add(u)
        db.session.commit()
        u = User.query.filter_by(username='felix').first()
        self.assertEquals(u.exam_points, 10)

    def test_gravatar(self):
        u = User(email='john@example.com', password='cat')
        with self.app.test_request_context('/'):
            gravatar = u.gravatar()
            gravatar_256 = u.gravatar(size=256)
            gravatar_pg = u.gravatar(rating='pg')
            gravatar_retro = u.gravatar(default='retro')
        with self.app.test_request_context('/', base_url='https://example.com'):
            gravatar_ssl = u.gravatar()
        self.assertTrue('http://www.gravatar.com/avatar/' +
                        'd4c74594d841139328695756648b6bd6' in gravatar)
        self.assertTrue('s=256' in gravatar_256)
        self.assertTrue('r=pg' in gravatar_pg)
        self.assertTrue('d=retro' in gravatar_retro)
        self.assertTrue('https://secure.gravatar.com/avatar/' +
                        'd4c74594d841139328695756648b6bd6' in gravatar_ssl)

    def test_to_json(self):
        u = User(email='john@example.com', password='cat')
        db.session.add(u)
        db.session.commit()
        json_user = u.to_json()
        expected_keys = ['username', 'id', 'created', 'updated', 'tutorial_completed', 'exam_points', 'gender']
        self.assertEqual(sorted(json_user.keys()), sorted(expected_keys))

    def test_is_teacher(self):
        role = Role.query.filter_by(name='Teacher').first()
        u = User(email='john@example.com', password='cat')
        u.role = role
        self.assertTrue(u.is_teacher())

    def test_is_not_teacher(self):
        role = Role.query.filter_by(name='Student').first()
        u = User(email='john@example.com', password='cat')
        u.role = role
        self.assertFalse(u.is_teacher())

    def test_is_student(self):
        role = Role.query.filter_by(name='Student').first()
        u = User(email='john@example.com', password='cat')
        u.role = role
        self.assertTrue(u.is_student())

    def test_is_not_student(self):
        role = Role.query.filter_by(name='Teacher').first()
        u = User(email='john@example.com', password='cat')
        u.role = role
        self.assertFalse(u.is_student())

    def test_user_is_teacher_by_default(self):
        u = User(email='john@example.com', password='cat')
        role = Role.query.filter_by(name='Student').first()
        self.assertEquals(role, u.role)

    def test_get_students(self):
        role = Role.query.filter_by(name='Teacher').first()
        student = User(email='student@example.com', password='cat')
        teacher = User(email='teacher@example.com', password='cat')
        teacher.role = role
        db.session.add(teacher)
        db.session.add(student)
        db.session.commit()
        self.assertIn(student, User.students().all())
        self.assertNotIn(teacher, User.students().all())

    def test_get_teachers(self):
        role = Role.query.filter_by(name='Teacher').first()
        student = User(email='student@example.com', password='cat')
        teacher = User(email='teacher@example.com', password='cat')
        teacher.role = role
        db.session.add(teacher)
        db.session.add(student)
        db.session.commit()
        self.assertIn(teacher, User.teachers().all())
        self.assertNotIn(student, User.teachers().all())

    def test_update(self):
        u = User(email='student@example.com', password='cat')
        u.update({'username': 'pepe'})
        self.assertEquals(u.username, 'pepe')
        with self.assertRaises(ValueError):
            u.update({'non_existend_field': 'asdf'})

    def test_gender(self):
        u = User(email='student@example.com', password='cat')
        self.assertEquals(u.gender, 'undefined')
        u.update({'gender': 'female'})
        self.assertEquals(u.gender, 'female')
