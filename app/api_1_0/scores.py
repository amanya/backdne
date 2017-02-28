from flask import json
from flask import g, jsonify, request, current_app, url_for
from sqlalchemy import func

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

@api.route('/best_scores')
@permission_required(Permission.EXIST)
def best_scores():
    is_exam = request.args.get('is_exam', False, type=bool)
    game = request.args.get('game', '', type=str)

    best_scores = db.session.query(Score.id, Score.game, func.max(Score.score)).select_from(Score) \
        .group_by(Score.game)

    if is_exam:
        best_scores = best_scores.filter_by(is_exam=True)

    if game:
        best_scores = best_scores.filter_by(game=game)

    scores = []
    for id, _, _ in best_scores:
        scores.append(Score.query.get(id).to_json())

    return jsonify({'best_scores': scores})


@api.route('/last_scores')
@permission_required(Permission.EXIST)
def last_scores():
    is_exam = request.args.get('is_exam', False, type=bool)
    game = request.args.get('game', '', type=str)

    last_scores = db.session.query(Score.id, Score.game, func.max(Score.created)).select_from(Score) \
        .group_by(Score.game)

    if is_exam:
        last_scores = last_scores.filter_by(is_exam=True)

    if game:
        last_scores = last_scores.filter_by(game=game)

    scores = []
    for id, _, _ in last_scores:
        scores.append(Score.query.get(id).to_json())

    return jsonify({'last_scores': scores})
