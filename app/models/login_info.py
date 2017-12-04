from sqlalchemy import func

from .. import db


class LoginInfo(db.Model):
    __tablename__ = 'login_info'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    remote_addr = db.Column(db.String(32))
    user_agent = db.Column(db.String(64))
    created = db.Column(db.DateTime, default=func.now())
