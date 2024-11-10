from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import pytz

japan_timezone = pytz.timezone('Asia/Tokyo')
def get_japan_time():
    return datetime.now(japan_timezone)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_image = db.Column(db.String(120), nullable=True)

    def get_profile_image(self):
        return self.profile_image or 'default_profile.png'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tags = db.Column(db.PickleType, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('projects', lazy=True))
    is_public = db.Column(db.Boolean, default=False)
    date_posted = db.Column(db.DateTime, default=get_japan_time, nullable=False)
    members = db.relationship('User', secondary='project_members', backref=db.backref('projects_as_member', lazy=True))
    commits = db.relationship('Commit', back_populates='project', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Project {self.name}>'

class ProjectMembers(db.Model):
    __tablename__ = 'project_members'
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

class Commit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commit_message = db.Column(db.String(256), nullable=False)
    commit_image = db.Column(db.String(256))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    project = db.relationship('Project', back_populates='commits')
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('commits', lazy=True))

    def __repr__(self):
        return f'<Commit {self.commit_message}>'

class CommitComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=get_japan_time, nullable=False)
    commit_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=get_japan_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    commit_id = db.Column(db.Integer, db.ForeignKey('commit.id'), nullable=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    project = db.relationship('Project', backref=db.backref('notifications', lazy=True))
    commit = db.relationship('Commit', backref=db.backref('notifications', lazy=True))

    def __repr__(self):
        return f'<Notification {self.message}>'