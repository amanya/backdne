from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, \
    SubmitField, PasswordField, SelectMultipleField, HiddenField
from wtforms.validators import DataRequired, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User, School


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    submit = SubmitField('Submit')


class ChangePasswordAdminForm(FlaskForm):
    new_password = PasswordField('New password')
    submit = SubmitField('Submit')


class DeleteUserForm(FlaskForm):
    check_username = StringField('Repeat username to delete')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(DeleteUserForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate_check_username(self, field):
        if field.data != self.user.username:
            raise ValidationError('Wrong username')

class DeleteUserStudentsForm(FlaskForm):
    delete_students = BooleanField('Delete students')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(DeleteUserStudentsForm, self).__init__(*args, **kwargs)
        self.user = user

class DeleteSchoolForm(FlaskForm):
    check_name = StringField('Repeat school name to delete')
    submit = SubmitField('Submit')

    def __init__(self, school, *args, **kwargs):
        super(DeleteSchoolForm, self).__init__(*args, **kwargs)
        self.school = school

    def validate_check_name(self, field):
        if field.data != self.school.name:
            raise ValidationError('Wrong school name')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email')
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              'Usernames must have only letters, '
                                              'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    enabled = BooleanField('Enabled')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    teacher = SelectField('Teacher', coerce=int)
    schools = SelectMultipleField('School', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        r = Role.get('Teacher')
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        if user.is_student():
            self.teacher.choices = [(teacher.id, teacher.name)
                                    for teacher in User.query.filter(User.role_id == r.id).order_by(User.name).all()]
        else:
            del(self.teacher)
        self.schools.choices = [(school.id, school.name)
                               for school in School.query.order_by(School.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data:
            if field.data != self.user.email and \
                    User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class UserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              'Usernames must have only letters, '
                                              'numbers, dots or underscores')])
    password = PasswordField("Password", validators=[DataRequired()])
    role = SelectField('Role', coerce=int)

    submit = SubmitField('Submit')
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]

class BatchUsersForm(FlaskForm):
    csv_data = TextAreaField('CSV users data', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_csv_data(self, field):
        import csv
        try:
            csvreader = csv.reader(field.data.splitlines(), delimiter='\t')
            for username, password, teacher in csvreader:
                pass
        except:
            raise ValidationError('Invalid CSV format')


class SchoolForm(FlaskForm):
    name = StringField('Name of the school', validators=[Length(0, 64)])
    description = PageDownField("Description", validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditSchoolForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                              'Names must have only letters, '
                                              'numbers, dots or underscores')])
    enabled = BooleanField('Confirmed')
    address = StringField('Address', validators=[Length(0, 254)])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    description = TextAreaField('Description', validators=[Length(0, 254)])
    submit = SubmitField('Submit')

    def __init__(self, school, *args, **kwargs):
        super(EditSchoolForm, self).__init__(*args, **kwargs)
        self.school = school

    def validate_email(self, field):
        if field.data != self.school.email and \
                School.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_name(self, field):
        if field.data != self.school.name and \
                School.query.filter_by(name=field.data).first():
            raise ValidationError('School name already in use.')


class CommentForm(FlaskForm):
    body = StringField('Enter your comment', validators=[DataRequired()])
    submit = SubmitField('Submit')


class AssetForm(FlaskForm):
    file_name = HiddenField('Name of the asset', validators=[Length(0, 128)])
    file_type = HiddenField('Type of the asset', validators=[Length(0, 64)])
    submit = SubmitField('Submit')


class DeleteAssetForm(FlaskForm):
    submit = SubmitField('Delete asset')


class GameDataForm(FlaskForm):
    file_content = TextAreaField('Game Data content', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, game_data, *args, **kwargs):
        super(GameDataForm, self).__init__(*args, **kwargs)
        if not self.file_content.data:
            self.file_content.data = game_data.content.decode()

