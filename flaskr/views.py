from flask import app, redirect, url_for, flash, request, send_from_directory, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import *
from models import *
from werkzeug.utils import secure_filename
import os

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ここから画面＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
@app.route('/', methods=['GET'])
@login_required
def home():
    notifications = Notification.query.filter_by(user_id=current_user.id, status='pending').all()
    search_query = request.args.get('search', '')
    if search_query:
        projects = Project.query.filter(
            Project.is_public == True,
            (Project.name.like(f'%{search_query}%') |
             Project.description.like(f'%{search_query}%'))
            #  Project.tags.any(like(f'%{search_query}%'))
        ).all()
    else:
        projects = Project.query.filter(Project.is_public == True).all()

    project_data = [
        {"id": project.id, "name": project.name, "description": project.description}
        for project in projects
    ]
    notification_data = [
        {"id": notification.id, "message": notification.message}
        for notification in notifications
    ]

    return jsonify({"projects": project_data, "notifications": notification_data})

@app.route('/login', methods=['POST'])
def login():#ログイン
    data = request.json
    user = User.query.filter_by(username=data.get("username")).first()

    if user and user.check_password(data.get("password")):
        login_user(user)
        return jsonify({"message": "ログインに成功しました。"}), 200
    else:
        return jsonify({"message": "ユーザー名またはパスワードが無効です。"}), 401


@app.route('/logout')
@login_required
def logout():#ログアウト
    logout_user()
    return jsonify({"message": "ログアウトしました。"}), 200


@app.route('/register', methods=['POST'])
def register():#登録
    data = request.json
    if data.get("password") != data.get("password2"):
        return jsonify({"message": "パスワードと確認用パスワードが一致しません。"}), 400
    
    user = User(username=data.get("username"))
    user.set_password(data.get("password"))
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "ユーザー登録が完了しました。"}), 201


@app.route('/profile', methods=['POST'])
@login_required
def profile():
    if request.method == 'POST':
        profile_image = request.files.get('profile_image')
        
        if profile_image:
            filename = secure_filename(profile_image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_image.save(filepath)
            current_user.profile_image = filename
            db.session.commit()
            return jsonify(message='プロフィール画像が更新されました。'), 200

    projects = Project.query.filter_by(user_id=current_user.id).all()
    response_data = {
        "username": current_user.username,
        "projects": [{
            "id": project.id,
            "name": project.name,
            "latest_commit_image": project.commits[-1].commit_image
        } for project in projects],
        "profile_image": current_user.get_profile_image()
    }
    return jsonify(response_data), 200


@app.route('/makeproject', methods=['POST'])
@login_required
def make_project():
    data = request.json
    project_name = data.get('project_name')
    project_description = data.get('project_description')
    tags = data.get('tags', '').split(',')
    commit_message = data.get('commit_message')
    commit_image = request.files.get('commit_image')

    if commit_image:
        filename = secure_filename(commit_image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        commit_image.save(filepath)
    else:
        return '', 400

    new_project = Project(
        name=project_name,
        description=project_description,
        tags=tags,
        user_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()

    new_commit = Commit(
        commit_message=commit_message,
        commit_image=filepath,
        project_id=new_project.id,
        user_id=current_user.id
    )
    db.session.add(new_commit)
    db.session.commit()

    return jsonify(project_id=new_project.id), 201



@app.route('/project/<int:project_id>', methods=['GET', 'PATCH', 'DELETE'])
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'PATCH':
        project.is_public = not project.is_public
        db.session.commit()
        return '', 200

    elif request.method == 'DELETE':
        db.session.delete(project)
        db.session.commit()
        return '', 200

    latest_commit = Commit.query.filter_by(project_id=project.id).order_by(Commit.id.desc()).first()
    return jsonify(
        project_id=project.id,
        name=project.name,
        description=project.description,
        is_public=project.is_public,
        latest_commit_image=latest_commit.commit_image
    ), 200


@app.route('/project/<int:project_id>/invite', methods=['GET', 'POST'])
@login_required
def invite_user(project_id):
    project = Project.query.get_or_404(project_id)
    
    search_query = request.args.get('search', '')
    users = []
    
    if search_query:
        users = User.query.filter(User.username.contains(search_query)).all()

    if request.method == 'POST':
        user_id = request.json.get('user_id')
        user_to_invite = User.query.get(user_id)
        
        if user_to_invite:
            notification = Notification(
                message=f'{project.name}への招待',
                user_id=user_to_invite.id,
                project_id=project.id
            )
            db.session.add(notification)
            db.session.commit()
            return jsonify(message=f'{user_to_invite.username}が招待されました。'), 200
        
        return '', 404

    return jsonify(users=[{"id": user.id, "username": user.username} for user in users]), 200


@app.route('/project/<int:project_id>/commit', methods=['POST'])
@login_required
def commit(project_id):
    project = Project.query.get_or_404(project_id)

    commit_message = request.json.get('commit_message')
    commit_image = request.files.get('commit_image')
    
    if commit_image:
        filename = secure_filename(commit_image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        commit_image.save(filepath)
    else:
        return '', 400

    new_commit = Commit(
        commit_message=commit_message,
        commit_image=filepath,
        project_id=project.id,
        user_id=current_user.id
    )
    db.session.add(new_commit)
    db.session.commit()

    return '', 201


@app.route('/project/<int:project_id>/commits')
@login_required
def commits(project_id):
    project = Project.query.get_or_404(project_id)
    commits = Commit.query.filter_by(project_id=project.id).order_by(Commit.id.desc()).all()

    return jsonify(commits=[{
        "id": commit.id,
        "commit_message": commit.commit_message,
        "commit_image": commit.commit_image,
        "date_posted": commit.date_posted
    } for commit in commits]), 200


@app.route('/project/<int:project_id>/commit/<int:commit_id>', methods=['GET', 'POST'])
@login_required
def commit_detail(project_id, commit_id):  # コミット詳細
    project = Project.query.get_or_404(project_id)
    commit = Commit.query.get_or_404(commit_id)
    
    if request.method == 'POST':
        data = request.get_json()
        content = data.get('content')
        
        if content:
            comment = CommitComment(content=content, commit_id=commit.id, user_id=current_user.id)
            db.session.add(comment)
            db.session.commit()

            # プロジェクトのメンバーに通知
            users = project.members
            for user in users:
                if user.id != current_user.id:
                    notification_message = f'New comment on the commit "{commit.commit_message}" in project "{project.name}".'
                    notification = Notification(
                        message=notification_message,
                        user_id=user.id,
                        project_id=project.id,
                        commit_id=commit.id
                    )
                    db.session.add(notification)
            db.session.commit()

            return '', 200
        else:
            return '', 400

    comments = CommitComment.query.filter_by(commit_id=commit_id).all()
    comment_data = [{
        'id': comment.id,
        'content': comment.content,
        'created_at': comment.created_at,
        'user': {
            'id': comment.user.id,
            'username': comment.user.username
        }
    } for comment in comments]

    return jsonify(
        project_id=project.id,
        project_name=project.name,
        commit_id=commit.id,
        commit_message=commit.commit_message,
        commit_image=commit.commit_image,
        date_posted=commit.created_at,
        comments=comment_data
    ), 200
#__________________________________通知_________________________________________
# @event.listens_for(db.session, 'after_commit')
# def create_commit_notification(session):
#     for target in session.new:
#         if isinstance(target, Commit):
#             project = target.project
#             users = project.members

#             for user in users:
#                 if user.id != target.user_id:
#                     notification_message = f'{target.user.username} added a commit to the project {project.name}.'
#                     notification = Notification(
#                         message=notification_message,
#                         user_id=user.id,
#                         project_id=project.id
#                     )
#                     session.add(notification)
#     session.commit()


@app.route('/notification/<int:notification_id>/respond/<string:response>', methods=['PATCH'])
@login_required
def respond_to_invitation(notification_id, response):
    data = request.get_json()
    response = data.get('response')
    notification = Notification.query.filter_by(user_id=current_user.id).all()
    
    if not notification:
        return '', 404
    
    if response == 'accept':
        notification.status = 'accepted'
        project = notification.project
        project.members.append(current_user)
        db.session.commit()
        return '', 200
    
    elif response == 'decline':
        notification.status = 'declined'
        db.session.commit()
        return '', 200

