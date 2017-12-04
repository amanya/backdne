from .. import db
from app.exceptions import ValidationError
from sqlalchemy import func
from sqlalchemy import Index

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


