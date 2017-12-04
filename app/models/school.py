from sqlalchemy import func

from app.exceptions import ValidationError
from .user_school import UserSchool
from .role import Role
from .user import User
from .. import db

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=True)
    name = db.Column(db.String(254))
    address = db.Column(db.String(254))
    email = db.Column(db.String(64), unique=True, index=True)
    description = db.Column(db.Text())
    created = db.Column(db.DateTime, default=func.now())
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    users = db.relationship('User', secondary='users_schools', viewonly=True)

    @staticmethod
    def generate_fake(count=10):
        from random import seed, randint, sample
        import forgery_py

        seed()
        for i in range(count):
            s = School(name=forgery_py.internet.user_name(),
                       description=forgery_py.lorem_ipsum.sentences(5),
                       created=forgery_py.date.date(True))
            db.session.add(s)

    @property
    def teachers(self):
        role = Role.get('Teacher')
        return User.query.join(UserSchool, UserSchool.user_id == User.id) \
            .filter(User.role_id == role.id) \
            .filter(UserSchool.school_id == self.id)

    @property
    def students(self):
        role = Role.get('Student')
        return User.query.join(UserSchool, UserSchool.user_id == User.id) \
            .filter(User.role_id == role.id) \
            .filter(UserSchool.school_id == self.id)

    def add_teacher(self, user):
        if not user.is_teacher():
            raise ValidationError('User is not a teacher')
        self.users_schools.append(UserSchool(user=user, school=self))

    def add_student(self, user):
        if not user.is_student():
            raise ValidationError('User is not a student')
        self.users_schools.append(UserSchool(user=user, school=self))

    def to_json(self):
        json_school = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created': self.created,
            'updated': self.updated,
        }
        return json_school

    @staticmethod
    def from_json(json_school):
        name = json_school.get('name')
        if name is None or name == '':
            raise ValidationError('school does not have a name')
        return School(name=name)


