from flask import json
from flask import g, jsonify, request, current_app, url_for
from .decorators import permission_required
from . import api
from ..models import Permission, Lesson
from .. import db


@api.route('/lessons/', methods=['POST'])
@permission_required(Permission.EXIST)
def create_lesson():
    lesson = Lesson.from_json(request.json)
    lesson.user_id = g.current_user.id
    db.session.add(lesson)
    db.session.commit()
    return jsonify(lesson.to_json()), 201, {'Location': url_for('api.get_lesson', id=lesson.id, _external=True)}

@api.route('/lessons/<int:id>')
@permission_required(Permission.EXIST)
def get_lesson(id):
    lesson = Lesson.query.get_or_404(id)
    return jsonify(lesson.to_json())

@api.route('/lessons/finished')
@permission_required(Permission.EXIST)
def get_finished_lessons():
    user_id = g.current_user.id
    return jsonify(Lesson.get_finished_lessons(user_id)), 200
