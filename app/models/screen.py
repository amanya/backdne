from sqlalchemy import func

from .. import db

from .user import User


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
