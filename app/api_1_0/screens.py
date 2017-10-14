from flask import json
from flask import g, jsonify, request, url_for
from sqlalchemy import func, and_

from .decorators import permission_required
from . import api
from ..models import Permission, Screen
from .. import db


@api.route('/screens/', methods=['POST'])
@permission_required(Permission.EXIST)
def create_screen():
    screen = Screen.from_json(request.json)
    screen.user_id = g.current_user.id
    db.session.add(screen)
    db.session.commit()
    return jsonify(screen.to_json()), 201, {'Location': url_for('api.get_screen', id=screen.id, _external=True)}


@api.route('/screens/<int:id>')
@permission_required(Permission.EXIST)
def get_screen(id):
    screen = Screen.query.get_or_404(id)
    return jsonify(screen.to_json())

