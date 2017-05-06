from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries

from . import main
from .forms import EditProfileForm, EditProfileAdminForm, SchoolForm, UserForm, EditSchoolForm
from .. import db
from ..decorators import admin_required
from ..models import Role, User, School, Permission, Score


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['BACKEND_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


@main.route('/school/<id>', methods=['GET', 'POST'])
def school(id):
    school = School.query.filter_by(id=id).first_or_404()
    return render_template('school.html', school=school)


@main.route('/schools', methods=['GET', 'POST'])
def schools():
    form = SchoolForm()
    if current_user.can(Permission.CREATE_SCHOOLS) and form.validate_on_submit():
        school = School(name=form.name.data, description=form.description.data)
        db.session.add(school)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    query = School.query
    pagination = query.order_by(School.created.desc()).paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    schools = pagination.items
    return render_template('schools.html', form=form, schools=schools, pagination=pagination)

@main.route('/scores', methods=['GET'])
@login_required
def scores():
    page = request.args.get('page', 1, type=int)
    query = Score.query
    pagination = query.order_by(Score.created.desc()).paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    scores = pagination.items
    return render_template('scores.html', scores=scores, pagination=pagination)

@main.route('/users', methods=['GET'])
@login_required
def users():
    form = UserForm()
    if current_user.can(Permission.CREATE_USERS) and form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.password = form.password.data
        user.role_id = form.role.data
        db.session.add(user)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    query = User.query
    pagination = query.order_by(User.created.desc()).paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    users = pagination.items
    return render_template('users.html', form=form, users=users, pagination=pagination)


@main.route('/add-user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserForm()
    if current_user.can(Permission.CREATE_USERS) and form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.password = form.password.data
        user.role = Role.query.get(form.role.data)
        user.confirmed = True
        db.session.add(user)
        flash('The user {} has been created'.format(user.username))
        return redirect(url_for('.users'))
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/edit-school/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_school(id):
    school = School.query.get_or_404(id)
    form = EditSchoolForm(school=school)
    if form.validate_on_submit():
        school.name = form.name.data
        school.enabled = form.enabled.data
        school.address = form.address.data
        school.email = form.email.data
        school.description = form.description.data

        db.session.add(school)
        flash('The school has been updated.')
        return redirect(url_for('.school', id=school.id))
    form.name.data = school.name
    form.enabled.data = school.enabled
    form.address.data = school.address
    form.email.data = school.email
    form.description.data = school.description
    return render_template('edit_school.html', form=form, user=user)
