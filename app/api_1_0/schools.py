from flask import jsonify, request, url_for, current_app

from .. import db
from .decorators import permission_required
from . import api
from ..models import School, Permission, User


@api.route('/schools/')
def get_schools():
    page = request.args.get('page', 1, type=int)
    pagination = School.query.paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    schools = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_schools', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_schools', page=page + 1, _external=True)
    return jsonify({
        'schools': [school.to_json() for school in schools],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/schools/<int:id>')
@permission_required(Permission.EXIST)
def get_school(id):
    school = School.query.get_or_404(id)
    return jsonify(school.to_json())


@api.route('/schools/', methods=['POST'])
@permission_required(Permission.CREATE_SCHOOLS)
def new_school():
    school = School.from_json(request.json)
    db.session.add(school)
    db.session.commit()
    return jsonify(school.to_json()), 201, {'Location': url_for('api.get_school', id=school.id, _external=True)}


@api.route('/schools/<int:id>', methods=['PUT'])
@permission_required(Permission.CREATE_SCHOOLS)
def edit_school(id):
    school = School.query.get_or_404(id)
    school.name = request.json.get('name', school.name)
    db.session.add(school)
    return jsonify(school.to_json())


@api.route('/schools/<int:id>/teachers/')
@permission_required(Permission.EXIST)
def get_teachers(id):
    school = School.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = school.teachers.paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    teachers = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_teachers', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_teachers', page=page + 1, _external=True)
    return jsonify({
        'teachers': [teacher.to_json() for teacher in teachers],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/schools/<int:id>/students/')
@permission_required(Permission.EXIST)
def get_students(id):
    school = School.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = school.students.paginate(
        page, per_page=current_app.config['BACKEND_POSTS_PER_PAGE'],
        error_out=False)
    students = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_students', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_students', page=page + 1, _external=True)
    return jsonify({
        'students': [student.to_json() for student in students],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/schools/<int:id>/students/', methods=['PUT'])
@permission_required(Permission.CREATE_SCHOOLS)
def add_student_to_school(id):
    school = School.query.get_or_404(id)
    student = User.query.get_or_404(request.json.get('id'))
    school.add_student(student)
    return jsonify({
        'school': school.to_json()
    })


@api.route('/schools/<int:id>/teachers/', methods=['PUT'])
@permission_required(Permission.CREATE_SCHOOLS)
def add_teacher_to_school(id):
    school = School.query.get_or_404(id)
    teacher = User.query.get_or_404(request.json.get('id'))
    school.add_teacher(teacher)
    return jsonify({
        'school': school.to_json()
    })

