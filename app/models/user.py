import hashlib
from datetime import datetime

import boto3
from flask import current_app, request
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import func
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash, check_password_hash

from app.exceptions import ValidationError
from .role import Role
from .login_info import LoginInfo
from .permission import Permission
from .score import Score
from .. import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    tutorial_completed = db.Column(db.Boolean, default=False)
    exam_points = db.Column(db.Integer, default=0)
    name = db.Column(db.String(64))
    gender = db.Column(db.String(32), default='undefined')
    avatar_hash = db.Column(db.String(32))
    created = db.Column(db.DateTime, default=func.now())
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    schools = db.relationship('School', secondary="users_schools", viewonly=True)

    scores = db.relationship('Score', backref='user', lazy='dynamic', order_by="Score.created")
    lessons = db.relationship('Lesson', backref='user', lazy='dynamic', order_by="Lesson.created")
    login_info = db.relationship('LoginInfo', backref='user', lazy='dynamic', order_by="LoginInfo.created", cascade='save-update')
    teacher = db.relationship('User', backref='user', lazy='dynamic', cascade='all')
    schools = db.relationship('School', backref='user', secondary='users_schools', lazy='dynamic', cascade='all')
    screens = db.relationship('Screen', backref='user', lazy='dynamic', order_by="Screen.created", cascade='save-update')

    @staticmethod
    def import_students():
        import requests
        with requests.Session() as s:
            download = s.get('https://s3.amazonaws.com/gamegen/import/students.csv')
            csvfile = download.content.decode('utf-8')
            User.import_students_from_data(csvfile, ',')

            
    @staticmethod
    def import_students_from_data(csv_data, delimiter=','):
        import csv
        from sqlalchemy.exc import IntegrityError
        csvreader = csv.reader(csv_data.splitlines(), delimiter=delimiter)
        for username, password, teacher in csvreader:
            print(username, password, teacher)
            teacher = User.query.filter_by(username=teacher).first()
            u = User(username=username,
                     password=password,
                     confirmed=True,
                     name=username,
                     role=Role.get('Student'),
                     teacher=teacher)
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()


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
        if self.gender is None:
            self.gender = 'undefined'
        if self.role is None:
            if self.email == current_app.config['BACKEND_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

        self.schools = []

    @property
    def teacher(self):
        if not self.teacher_id:
            return None
        return User.query.get(self.teacher_id)

    @teacher.setter
    def teacher(self, teacher):
        self.teacher_id = teacher.id

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save_login_info(self, request):
        login_info = LoginInfo(
                user_id = self.id,
                remote_addr = request['environ'].get('REMOTE_ADDR', ''),
                user_agent = request['environ'].get('HTTP_USER_AGENT', ''))
        db.session.add(login_info)

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
        if self.email:
            hash = self.avatar_hash or hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        else:
            hash = hashlib.md5(self.username.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def add_to_schools(self, schools):
        self.users_schools = []
        for s in schools:
            school = School.query.get(s)
            self.users_schools.append(UserSchool(user=self, school=school))

    def remove_from_school(self, school):
        f = self.schools.filter_by(school_id=school.id).first()
        if f:
            db.session.delete(f)

    def member_of_school(self, school):
        return self.schools.filter_by(
            school_id=school.id).first() is not None

    def to_json(self):
        json_user = {
            'id': self.id,
            'username': self.username,
            'tutorial_completed': self.tutorial_completed,
            'exam_points': self.exam_points,
            'gender': self.gender,
            'role': self.role.name,
            'created': self.created,
            'updated': self.updated,
        }
        return json_user

    def update(self, data):
        mapper = inspect(User)
        for k, v in data.items():
            if not k in mapper.attrs:
                raise ValidationError("Field '{}' is not part of User".format(k))
            setattr(self, k, v)

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

    def my_students(self):
        role = Role.get('Student')
        return User.query.filter(User.teacher_id == self.id)

    def have_scores(self):
        return Score.query.join(User, self.id == Score.user_id).count() > 0

    @property
    def max_score_by_game(self):
        return db.session.query(Score.game, func.max(Score.score).label('score')) \
            .select_from(Score) \
            .join(User, self.id == Score.user_id) \
            .group_by(Score.game)

    def __repr__(self):
        return '<User %r>' % self.username



