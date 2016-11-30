from flask import json
from flask import jsonify, request, current_app, url_for
from .decorators import permission_required
from . import api
from ..models import User, Permission, School, Score


@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/<int:id>/schools/')
def get_user_schools(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(School.created.desc()).paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    schools = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_schools', page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_schools', page=page+1, _external=True)
    return jsonify({
        'schools': [school.to_json() for school in schools],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/users/<int:user_id>/games/<string:game>/max_score')
@permission_required(Permission.EXIST)
def get_user_game_max_score(user_id, game):
    if user_id is not None and game is not None:
        max_score = Score.max_score_by_user_and_game(user_id, game)
        if not max_score:
            return 'Not found', 404
        return jsonify({'max_score': max_score})


@api.route('/login', methods=['POST'])
def login():
    data = json.loads(request.data)
    user = User.query.filter_by(username=data["username"]).first()
    if user is not None and user.verify_password(data["password"]):
        return jsonify(user.to_json())
    return 'Unauthorized', 401


