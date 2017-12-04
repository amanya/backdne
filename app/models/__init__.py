from .. import login_manager

from .anonymous_user import AnonymousUser
from .asset import Asset
from .game_data import GameData
from .lesson import Lesson
from .login_info import LoginInfo
from .permission import Permission
from .role import Role
from .school import School
from .score import Score
from .screen import Screen
from .user import User
from .user_school import UserSchool


login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
