from flask import json
from flask import g, jsonify, request, current_app, url_for
from .decorators import permission_required
from . import api
from ..models import Permission, Score
from .. import db


@api.route('/scores/', methods=['POST'])
@permission_required(Permission.EXIST)
def create_score():
    score = Score.from_json(request.json)
    score.user_id = g.current_user.id
    db.session.add(score)
    db.session.commit()
    return jsonify(score.to_json()), 201, {'Location': url_for('api.get_score', id=score.id, _external=True)}

@api.route('/scores/<int:id>')
@permission_required(Permission.EXIST)
def get_score(id):
    score = Score.query.get_or_404(id)
    return jsonify(score.to_json())


