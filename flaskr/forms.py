from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

class ProjectForm(FlaskForm):
    project_name = StringField('Project Name', validators=[DataRequired()])
    project_description = TextAreaField('Project Description', validators=[DataRequired()])
    tags = StringField('Tags (comma separated)', validators=[DataRequired()])
    commit_message = StringField('Commit Message', validators=[DataRequired()])
    commit_image = FileField('Commit Image')
    submit = SubmitField('Create Project')

class CommitForm(FlaskForm):
    commit_message = StringField('Commit Message', validators=[DataRequired()])
    commit_image = FileField('Commit Image')
    submit = SubmitField('Submit')

class CommentForm(FlaskForm):
    content = TextAreaField('コメント', validators=[DataRequired()])
    submit = SubmitField('コメントを投稿')

class InviteUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Invite')