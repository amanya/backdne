import boto3
from flask import json
from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from sqlalchemy import text

from . import main
from .forms import EditProfileForm, EditProfileAdminForm, SchoolForm, \
        UserForm, EditSchoolForm, AssetForm, DeleteUserForm, DeleteSchoolForm, \
        ChangePasswordAdminForm, GameDataForm, DeleteAssetForm, DeleteUserStudentsForm, \
        BatchUsersForm
from .. import db, redis_store
from ..decorators import admin_required
from ..models import Role, User, School, Permission, Score, Asset, GameData, UserSchool


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['BACKEND_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


@main.route('/school/<id>', methods=['GET', 'POST'])
@login_required
def school(id):
    school = School.query.filter_by(id=id).first_or_404()
    return render_template('school.html', school=school)


@main.route('/schools', methods=['GET', 'POST'])
@login_required
def schools():
    form = SchoolForm()
    if current_user.can(Permission.CREATE_SCHOOLS) and form.validate_on_submit():
        school = School(name=form.name.data, description=form.description.data)
        db.session.add(school)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    if not current_user.is_administrator():
        query = School.query.join(UserSchool)\
            .filter(UserSchool.user_id == current_user.id)
    else:
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
    if current_user.is_teacher():
        query = User.query.filter(User.teacher_id == current_user.id)
    else:
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

@main.route('/batch-add-users', methods=['GET', 'POST'])
@login_required
@admin_required
def batch_add_users():
    form = BatchUsersForm()
    if current_user.can(Permission.CREATE_USERS) and form.validate_on_submit():
        User.import_students_from_data(form.csv_data.data, delimiter='\t')
        return redirect(url_for('.users'))
    return render_template('batch_add_users.html', form=form)

@main.route('/change-password-admin/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def change_password_admin(id):
    user = User.query.get_or_404(id)
    form = ChangePasswordAdminForm(user=user)
    if form.validate_on_submit():
        new_password = form.new_password.data
        token = user.generate_reset_token()
        user.reset_password(token, new_password)
        return redirect(url_for('.user', username=user.username))
    return render_template('change_password_admin.html', form=form)

@main.route('/delete-school/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_school(id):
    school = School.query.get_or_404(id)
    form = DeleteSchoolForm(school=school)
    if form.validate_on_submit():
        db.session.delete(school)
        return redirect(url_for('.schools'))
    return render_template('delete_school.html', school=school, form=form)

@main.route('/delete-user/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    delete_students = request.args.get('delete_students')
    if delete_students == "false":
        delete_students = False
    else:
        delete_students = True
    if delete_students and user.is_teacher() and len(user.my_students().all()) > 0:
        return redirect(url_for('.delete_user_students', id=id))
    form = DeleteUserForm(user=user)
    if form.validate_on_submit():
        if not delete_students:
            for student in user.my_students():
                student.teacher_id = None
                db.session.add(student)
            db.session.commit()
        db.session.delete(user)
        return redirect(url_for('.users'))
    return render_template('delete_user.html', user=user, form=form)

@main.route('/delete-user-students/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_user_students(id):
    user = User.query.get_or_404(id)
    if not user.is_teacher() or not len(user.my_students().all()) > 0:
        return redirect(url_for('.users'))
    form = DeleteUserStudentsForm(user=user)
    if form.validate_on_submit():
        if form.delete_students.data:
            for student in user.my_students():
                db.session.delete(student)
            db.session.commit()
        return redirect(url_for('.delete_user', id=id) + '?delete_students=false')
    return render_template('delete_user_students.html', user=user, form=form)

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
        if form.email.data == "":
            user.email = None
        else:
            user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.add_to_schools(form.schools.data)
        if user.is_student():
            user.teacher = User.query.get(form.teacher.data)
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.schools.data = [s.id for s in user.schools]
    if user.teacher and form.teacher:
        form.teacher.data = user.teacher.id
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

@main.route('/user-stats')
@login_required
@admin_required
def user_stats():
    from rq import Queue
    from ..jobs import game_stats

    s3_bucket = current_app.config['S3_BUCKET']
    aws_region = current_app.config['AWS_REGION']

    q = Queue(connection=redis_store)

    user_role = ''
    if current_user.is_student():
        user_role = 'student'
    if current_user.is_teacher():
        user_role = 'teacher'
    if current_user.is_administrator():
        user_role = 'administrator'

    result = q.enqueue(game_stats.game_stats, aws_region, s3_bucket, current_user.id, user_role, timeout=59*30)

    job_url = 'https://s3.amazonaws.com/{}/jobs/{}.csv'.format(s3_bucket, result.id)

    return render_template('game_stats.html', job_url=job_url)

@main.route('/game-data')
@login_required
@admin_required
def game_data():
    page = request.args.get('page', 1, type=int)
    query = GameData.query
    pagination = query.order_by(GameData.file_name.desc()).paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    game_data = pagination.items
    return render_template('game_data.html', game_data=game_data, pagination=pagination)


@main.route('/edit-game-data/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_game_data(id):
    game_data = GameData.query.get(id)
    form = GameDataForm(game_data=game_data)
    if form.validate_on_submit():
        game_data.content = form.file_content.data
        return redirect(url_for('.game_data'))
    return render_template('edit_game_data.html', form=form, game_data=game_data)


@main.route('/assets')
@login_required
@admin_required
def assets():
    page = request.args.get('page', 1, type=int)
    query = Asset.query
    pagination = query.order_by(Asset.file_name.asc()).paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    assets = pagination.items
    return render_template('assets.html', assets=assets, pagination=pagination)


@main.route('/upload-asset', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_asset():
    form = AssetForm()
    if form.validate_on_submit():
        asset = Asset()
        asset.file_name = form.file_name.data
        asset.file_type = form.file_type.data
        db.session.add(asset)
        return redirect(url_for('.assets'))
    return render_template('upload_asset.html', form=form)


@main.route('/delete-asset/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_asset(id):
    asset = Asset.query.filter_by(id=id).first_or_404()
    form = DeleteAssetForm()
    if form.validate_on_submit():
        s3 = boto3.client('s3', current_app.config['AWS_REGION'])
        s3.delete_object(Bucket=current_app.config['S3_BUCKET'], Key='assets/{}'.format(asset.file_name))
        db.session.delete(asset)
        return redirect(url_for('.assets'))
    return render_template('delete_asset.html', form=form, asset=asset)

@main.route('/sign-s3/')
@login_required
@admin_required
def sign_s3():
    S3_BUCKET = current_app.config['S3_BUCKET']
    AWS_REGION = current_app.config['AWS_REGION']

    file_name = request.args.get('file-name')
    file_type = request.args.get('file-type')

    s3 = boto3.client('s3', AWS_REGION)

    presigned_post = s3.generate_presigned_post(
        Bucket = S3_BUCKET,
        Key = 'assets/{}'.format(file_name),
        Fields = {"acl": "public-read", "Content-Type": file_type},
        Conditions = [
            {"acl": "public-read"},
            {"Content-Type": file_type}
        ],
        ExpiresIn = 3600
    )

    return json.dumps({
        'data': presigned_post,
        'file_name': file_name,
        'file_type': file_type,
        'url': 'https://s3.amazonaws.com/{}/assets/{}'.format(S3_BUCKET, file_name)
    })
