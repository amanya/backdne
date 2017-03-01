from flask import json
from flask import g, jsonify, request, current_app, url_for
from sqlalchemy import func, and_

from .decorators import permission_required
from . import api
from ..models import Permission, Score
from .. import db

BOOL_VALUES = {
    "True": True,
    "False": False,
    "true": True,
    "false": False,
    "TRUE": True,
    "FALSE": False,
    "1": True,
    "0": False,
    "t": True,
    "f": False,
}

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

@api.route('/scores_all')
@permission_required(Permission.EXIST)
def all_scores():
    user = g.current_user

    is_exam = request.args.get('is_exam')
    is_exam = BOOL_VALUES.get(is_exam, None)

    result = user.scores.filter_by(state='finished')

    if is_exam == True:
        result = result.filter_by(is_exam=True)
    elif is_exam == False:
        result = result.filter_by(is_exam=False)

    scores = []
    for score in result:
        scores.append(score.to_json())

    return jsonify({'scores': scores})



@api.route('/best_scores')
@permission_required(Permission.EXIST)
def best_scores():
    is_exam = request.args.get('is_exam')
    is_exam = BOOL_VALUES.get(is_exam, None)

    game = request.args.get('game', '', type=str)
    user_id = g.current_user.id

    t = db.session.query(Score.game, func.max(Score.score).label('max_score'))\
        .select_from(Score)\
        .filter_by(user_id=user_id)\
        .filter_by(state='finished')

    if is_exam == True:
        result = result.filter_by(is_exam=True)
    elif is_exam == False:
        result = result.filter_by(is_exam=False)

    if game:
        t = t.filter_by(game=game)
    t = t.group_by(Score.game)
    t = t.subquery('t')

    q = db.session.query(Score.id, Score.game, Score.score).select_from(Score)\
            .join(t, and_(Score.game == t.c.game, Score.score == t.c.max_score))

    scores = []
    for id, _, _ in q:
        scores.append(Score.query.get(id).to_json())

    return jsonify({'scores': scores})


@api.route('/last_scores')
@permission_required(Permission.EXIST)
def last_scores():
    is_exam = request.args.get('is_exam')
    is_exam = BOOL_VALUES.get(is_exam, None)

    game = request.args.get('game', '', type=str)
    user_id = g.current_user.id

    t = db.session.query(Score.game, func.max(Score.created).label('max_created'))\
        .select_from(Score)\
        .filter_by(user_id=user_id)\
        .filter_by(state='finished')

    if is_exam == True:
        t = t.filter_by(is_exam=True)
    elif is_exam == False:
        t = t.filter_by(is_exam=False)

    if game:
        t = t.filter_by(game=game)
    t = t.group_by(Score.game)
    t = t.subquery('t')

    q = db.session.query(Score.id, Score.game, Score.score).select_from(Score)\
            .join(t, and_(Score.game == t.c.game, Score.created == t.c.max_created))

    scores = []
    for id, _, _ in q:
        scores.append(Score.query.get(id).to_json())

    return jsonify({'scores': scores})

@api.route('/last_scores_game')
@permission_required(Permission.EXIST)
def last_scores_game():
    user = g.current_user
    game = request.args.get('game', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = user.scores.filter_by(game=game).filter_by(state='finished').paginate(
        page, per_page=per_page,
        error_out=False)
    scores = pagination.items
    return jsonify({'scores': [score.to_json() for score in scores],})

