from sqlalchemy import func
from .. import db

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
