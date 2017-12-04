from sqlalchemy import func
from flask import current_app

from .. import db

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
