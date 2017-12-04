from sqlalchemy import func

from .. import db, login_manager

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
