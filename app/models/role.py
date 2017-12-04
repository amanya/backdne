from .. import db

from .permission import Permission

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