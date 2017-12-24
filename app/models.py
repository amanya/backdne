import hashlib
from datetime import datetime

import boto3
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import Index
from sqlalchemy import func
from sqlalchemy import inspect
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
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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

    user = db.relationship('User', backref=db.backref('users_schools', cascade='all, delete-orphan'))
    school = db.relationship('School', backref=db.backref('users_schools', cascade='all, delete-orphan'))

    def __init__(self, user=None, school=None):
        self.user = user
        self.school = school

    def __repr__(self):
        return '<UserSchool {%r} {%r}>' % (self.user.name, self.school.name)

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
                user_id=self.id,
                remote_addr=request['environ'].get('REMOTE_ADDR', ''),
                user_agent=request['environ'].get('HTTP_USER_AGENT', '')[:60])
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


class Score(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    game = db.Column(db.String(64), unique=False, index=True)
    state = db.Column(db.String(64), unique=False)
    score = db.Column(db.Integer)
    max_score = db.Column(db.Integer)
    is_exam = db.Column(db.Boolean, default=False)
    duration = db.Column(db.Integer)
    created = db.Column(db.DateTime, default=func.now())

    Index('idx_user_game', user_id, game)

    @property
    def user(self):
        return User.query.get(self.user_id)

    @staticmethod
    def from_json(json_score):
        user_id = json_score.get('user_id')
        game = json_score.get('game')
        state = json_score.get('state')
        score = json_score.get('score')
        max_score = json_score.get('max_score')
        duration = json_score.get('duration')
        is_exam = json_score.get('is_exam')
        if game is None or game == '':
            raise ValidationError('score does not have a game')
        if state is None or state == '':
            raise ValidationError('score does not have a state')
        return Score(user_id=user_id, game=game, score=score, max_score=max_score, duration=duration, state=state, is_exam=is_exam)

    def to_json(self):
        json_score = {
            'id': self.id,
            'user_id': self.user_id,
            'game': self.game,
            'state': self.state,
            'score': self.score,
            'max_score': self.max_score,
            'is_exam': self.is_exam,
            'duration': self.duration,
            'created': self.created,
        }
        return json_score

    @staticmethod
    def scores_by_user_and_game(user_id, game_id):
        return Score.query.join(User, User.id == Score.user_id) \
            .filter(User.id == user_id) \
            .filter(Score.game == game_id)

    @staticmethod
    def max_score_by_user_and_game(user_id, game_id):
        max_score = db.session.query(func.max(Score.score)).select_from(Score) \
            .filter(Score.user_id == user_id) \
            .filter(Score.game == game_id) \
            .first()[0]

        return max_score


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    lesson = db.Column(db.String(64), unique=False)
    total_pages_viewed = db.Column(db.Integer)
    clicks_forward = db.Column(db.Integer)
    clicks_backward = db.Column(db.Integer)
    clicks_menu = db.Column(db.Integer)
    clicks_lesson_repeat = db.Column(db.Integer)
    way_exit = db.Column(db.String(64))
    is_finished = db.Column(db.Boolean, default=False)
    duration = db.Column(db.Integer)
    created = db.Column(db.DateTime, default=func.now())

    @staticmethod
    def from_json(json_):
        lesson = json_.get('lesson')
        user_id = json_.get('user_id')
        total_pages_viewed = json_.get('total_pages_viewed')
        clicks_forward = json_.get('clicks_forward')
        clicks_backward = json_.get('clicks_backward')
        clicks_menu = json_.get('clicks_menu')
        clicks_lesson_repeat = json_.get('clicks_lesson_repeat')
        way_exit = json_.get('way_exit')
        is_finished = json_.get('is_finished')
        duration = json_.get('duration')
        if lesson is None or lesson == '':
            raise ValidationError('lesson does not have a valid lesson id')
        return Lesson(lesson=lesson, user_id=user_id, total_pages_viewed=total_pages_viewed,
                      clicks_forward=clicks_forward, clicks_backward=clicks_backward,
                      clicks_menu=clicks_menu, clicks_lesson_repeat=clicks_lesson_repeat,
                      way_exit=way_exit, is_finished=is_finished, duration=duration)

    def to_json(self):
        json_ = {
            'id': self.id,
            'user_id': self.user_id,
            'lesson': self.lesson,
            'total_pages_viewed': self.total_pages_viewed,
            'clicks_forward': self.clicks_forward,
            'clicks_backward': self.clicks_backward,
            'clicks_menu': self.clicks_menu,
            'clicks_lesson_repeat': self.clicks_lesson_repeat,
            'way_exit': self.way_exit,
            'is_finished': self.is_finished,
            'duration': self.duration,
            'created': self.created,
        }
        return json_

    @staticmethod
    def get_finished_lessons(user_id):
        data = {}
        lessons = Lesson.query.filter_by(user_id=user_id)

        for lesson in lessons:
            data.setdefault(lesson.lesson, False)
            if lesson.is_finished == True:
                data[lesson.lesson] = True

        return data

class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(128), index=True)
    file_type = db.Column(db.String(64))
    created = db.Column(db.DateTime, default=func.now())

    @property
    def url(self):
        S3_BUCKET = current_app.config['S3_BUCKET']
        AWS_REGION = current_app.config['AWS_REGION']
        return 'https://s3.amazonaws.com/{}/assets/{}'.format(S3_BUCKET, self.file_name)

class GameData(db.Model):
    __tablename__ = 'game_data'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(128), index=True)
    created = db.Column(db.DateTime, default=func.now())

    @property
    def url(self):
        S3_BUCKET = current_app.config['S3_BUCKET']
        AWS_REGION = current_app.config['AWS_REGION']
        return 'https://s3.amazonaws.com/{}/game_data/{}'.format(S3_BUCKET, self.file_name)

    @staticmethod
    def insert_game_data():
        game_data_files = [
            'animations_3d.json',
            'lessons.json',
            'localization.json',
            'quiz.json',
            'rooms.json'
        ]
        for g in game_data_files:
            game_data = GameData.get(g)
            if game_data is None:
                game_data = GameData(file_name=g)
            db.session.add(game_data)
        db.session.commit()

    @staticmethod
    def get(item):
        game_data = GameData.query.filter_by(file_name=item).first()
        if game_data and game_data.file_name == item:
            return game_data

    @property
    def content(self):
       s3 = boto3.resource('s3', current_app.config['AWS_REGION'])
       object = s3.Object(current_app.config['S3_BUCKET'], 'game_data/{}'.format(self.file_name))
       content = object.get()['Body'].read()
       return content

    @content.setter
    def content(self, content):
        s3 = boto3.resource('s3', current_app.config['AWS_REGION'])
        object = s3.Object(current_app.config['S3_BUCKET'], 'game_data/{}'.format(self.file_name))
        object.put(Body=content)


class LoginInfo(db.Model):
    __tablename__ = 'login_info'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    remote_addr = db.Column(db.String(32))
    user_agent = db.Column(db.String(64))
    created = db.Column(db.DateTime, default=func.now())


class Screen(db.Model):
    __tablename__ = 'screens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(64), unique=False)
    action = db.Column(db.String(64), unique=False)
    duration = db.Column(db.Integer)
    created = db.Column(db.DateTime, default=func.now())

    @property
    def user(self):
        return User.query.get(self.user_id)

    @staticmethod
    def from_json(data):
        user_id = data.get('user_id')
        name = data.get('name')
        action = data.get('action')
        duration = data.get('duration')
        return Screen(user_id=user_id, name=name, action=action, duration=duration)

    def to_json(self):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'action': self.action,
            'duration': self.duration,
            'created': self.created,
        }
        return data
