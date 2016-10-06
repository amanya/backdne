import hashlib
from datetime import datetime

from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

from app.exceptions import ValidationError
from . import db, login_manager


class Permission:
    EXIST = 0x01
    CREATE_USERS = 0x02
    CREATE_SCHOOLS = 0x04
    ADMINISTER = 0x08


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'Student': (Permission.EXIST, True),
            'Teacher': (Permission.EXIST |
                        Permission.CREATE_USERS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.get(r)
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    @staticmethod
    def get(item):
        role = Role.query.filter_by(name=item).first()
        if role and role.name == item:
            return role

    def __repr__(self):
        return '<Role %r>' % self.name


class UserSchool(db.Model):
    __tablename__ = 'users_schools'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), primary_key=True)
    created = db.Column(db.DateTime, default=func.now())
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    user = db.relationship('User', back_populates='schools')
    school = db.relationship('School', back_populates='users')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    avatar_hash = db.Column(db.String(32))
    created = db.Column(db.DateTime, default=func.now())
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    schools = db.relationship('UserSchool', back_populates="user")


    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for role in [Role.get('Student'), Role.get('Teacher')]:
            for i in range(count):
                u = User(email=forgery_py.internet.email_address(),
                         username=forgery_py.internet.user_name(True),
                         password=forgery_py.lorem_ipsum.word(),
                         confirmed=True,
                         name=forgery_py.name.full_name(),
                         created=forgery_py.date.date(True),
                         role=role)
                db.session.add(u)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['BACKEND_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def is_student(self):
        return self.role.name == 'Student'

    def is_teacher(self):
        return self.role.name == 'Teacher'

    def ping(self):
        self.updated = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def add_to_school(self, school):
        if not self.member_of_school(school):
            f = UserSchool(user=self, school=school)
            db.session.add(f)

    def remove_from_school(self, school):
        f = self.schools.filter_by(school_id=school.id).first()
        if f:
            db.session.delete(f)

    def member_of_school(self, school):
        return self.schools.filter_by(
            school_id=school.id).first() is not None

    def to_json(self):
        json_user = {
            'username': self.username,
            'created': self.created,
            'updated': self.updated,
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    @staticmethod
    def teachers():
        role = Role.get('Teacher')
        return User.query.filter(User.role_id == role.id)

    @staticmethod
    def students():
        role = Role.get('Student')
        return User.query.filter(User.role_id == role.id)

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
    users = db.relationship('UserSchool', back_populates="school", lazy="dynamic")

    @staticmethod
    def generate_fake(count=10):
        from random import seed, randint, sample
        import forgery_py

        seed()
        for i in range(count):
            teachers = sample(list(User.teachers()), randint(5, 10))
            students = sample(list(User.students()), randint(10, 30))
            s = School(name=forgery_py.internet.user_name(),
                       description=forgery_py.lorem_ipsum.sentences(5),
                       created=forgery_py.date.date(True))
            for teacher in teachers:
                s.add_teacher(teacher)
            for student in students:
                s.add_student(student)
            db.session.add(s)
            db.session.commit()

    @property
    def teachers(self):
        role = Role.get('Teacher')
        return User.query.join(UserSchool, UserSchool.user_id == User.id)\
            .filter(User.role_id == role.id)\
            .filter(UserSchool.school_id == self.id)

    @property
    def students(self):
        role = Role.get('Student')
        return User.query.join(UserSchool, UserSchool.user_id == User.id)\
            .filter(User.role_id == role.id)\
            .filter(UserSchool.school_id == self.id)

    def add_teacher(self, user):
        if not user.is_teacher():
            raise ValidationError('User is not a teacher')
        u2s = UserSchool()
        u2s.user = user
        self.users.append(u2s)
        db.session.add(u2s)

    def add_student(self, user):
        if not user.is_student():
            raise ValidationError('User is not a student')
        u2s = UserSchool(user=user, school=self)
        db.session.add(u2s)

    def to_json(self):
        json_school = {
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
