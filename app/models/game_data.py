import boto3
from sqlalchemy import func
from flask import current_app

from .. import db

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



