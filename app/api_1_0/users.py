from flask import jsonify, request, current_app, url_for
from . import api
from ..models import User, School


@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/<int:id>/schools/')
def get_user_schools(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(School.timestamp.desc()).paginate(
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

