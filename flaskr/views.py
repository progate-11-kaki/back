from flask import render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, login_manager
from models import User, Project, Commit, CommitComment, Notification
from forms import LoginForm, RegistrationForm, ProjectForm, CommentForm, InviteUserForm, CommitForm
from werkzeug.utils import secure_filename
from sqlalchemy import event
import os

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿ここから画面＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
@app.route('/', methods=['GET', 'POST'])
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

    return render_template('home.html', projects=projects, notifications=notifications)


@app.route('/login', methods=['GET', 'POST'])
def login():#ログイン
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('ログインに成功しました。')
            return redirect(url_for('home'))
        else:
            flash('ユーザー名またはパスワードが無効です。')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():#ログアウト
    logout_user()
    flash('ログアウトしました。')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():#登録
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('ユーザー登録が完了しました。')
        return redirect(url_for('login'))
    if form.password.data != form.password2.data:
        flash('パスワードと確認用パスワードが一致しません。', 'error')
    return render_template('register.html', form=form)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():#ユーザープロフィール
    projects = Project.query.filter_by(user_id=current_user.id).all()
    for project in projects:
        latest_commit = Commit.query.filter_by(project_id=project.id).order_by(Commit.id.desc()).first()
        project.latest_commit = latest_commit

    if request.method == 'POST':
        profile_image = request.files.get('profile_image')
        
        if profile_image:
            filename = secure_filename(profile_image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_image.save(filepath)
            current_user.profile_image = filename
            db.session.commit()
            flash('プロフィール画像が更新されました。')

    return render_template('profile.html', name=current_user.username, projects=projects, profile_image=current_user.get_profile_image())


@app.route('/makeproject', methods=['GET', 'POST'])
@login_required
def make_project():#プロジェクト作成
    form = ProjectForm()
    if form.validate_on_submit():
        project_name = form.project_name.data
        project_description = form.project_description.data
        tags = form.tags.data.split(',')  # タグをカンマ区切りでリストに分ける
        commit_message = form.commit_message.data
        commit_image = form.commit_image.data

        if commit_image:
            filename = secure_filename(commit_image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            commit_image.save(filepath)
        else:
            flash('画像ファイルをアップロードしてください。', 'error')
            return render_template('make_project.html', form=form)

        new_project = Project(
        name=project_name,
        description=project_description,
        tags=tags,
        user_id=current_user.id
        )
        db.session.add(new_project)
        db.session.commit()

        new_project.members.append(current_user)
        db.session.commit()

        new_commit = Commit(
            commit_message=commit_message,
            commit_image=filepath,
            project_id=new_project.id,
            user_id=current_user.id
        )
        db.session.add(new_commit)
        db.session.commit()


        flash('プロジェクトが作成されました！')
        return redirect(url_for('project_detail', project_id=new_project.id))

    return render_template('make_project.html', form=form)


@app.route('/project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def project_detail(project_id):#プロジェクト詳細
    project = Project.query.get_or_404(project_id)
    latest_commit = Commit.query.filter_by(project_id=project.id).order_by(Commit.id.desc()).first()

    if request.method == 'POST' and 'toggle_visibility' in request.form:
        project.is_public = not project.is_public
        db.session.commit()
        flash('プロジェクトの公開設定が更新されました。')
        return redirect(url_for('project_detail', project_id=project_id))

    if request.method == 'POST' and 'delete' in request.form:
        db.session.delete(project)
        db.session.commit()
        flash('プロジェクトが削除されました。')
        return redirect(url_for('profile'))

    return render_template('project_detail.html', project=project, latest_commit=latest_commit)


@app.route('/project/<int:project_id>/invite', methods=['GET', 'POST'])
@login_required
def invite_user(project_id):#招待
    project = Project.query.get_or_404(project_id)
    
    search_query = request.args.get('search', '')
    users = []
    
    if search_query:
        users = User.query.filter(User.username.contains(search_query)).all()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id:
            user_to_invite = User.query.get(user_id)
            if user_to_invite:
                # 通知を作成し招待を送信
                notification = Notification(
                    message=f'You have been invited to join the project: {project.name}',
                    user_id=user_to_invite.id,
                    project_id=project.id
                )
                db.session.add(notification)
                db.session.commit()
                flash(f'{user_to_invite.username} has been invited to the project.', 'success')
            else:
                flash('User not found.', 'error')

    return render_template('invite_user.html', project=project, users=users, search_query=search_query)


@app.route('/project/<int:project_id>/commit', methods=['GET', 'POST'])
@login_required
def commit(project_id):#コミット追加
    project = Project.query.get_or_404(project_id)

    form = CommitForm()
    if form.validate_on_submit():
        commit_message = form.commit_message.data
        commit_image = form.commit_image.data
        
        if commit_image:
            filename = secure_filename(commit_image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not filepath:
                print("Error: filepath is None or empty.")
            commit_image.save(filepath)
        else:
            flash('画像ファイルをアップロードしてください。', 'error')
            return render_template('commit.html', form=form, project=project)

        new_commit = Commit(
            commit_message=commit_message,
            commit_image=filepath,
            project_id=project.id,
            user_id=current_user.id
        )
        db.session.add(new_commit)
        db.session.commit()

        flash('Commit has been added!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    return render_template('commit.html', form=form, project=project)


@app.route('/project/<int:project_id>/commits')
@login_required
def commits(project_id):#コミット一覧
    project = Project.query.get_or_404(project_id)
    commits = Commit.query.filter_by(project_id=project.id).order_by(Commit.date_posted.desc()).all()

    return render_template('commits.html', project=project, commits=commits)


@app.route('/project/<int:project_id>/commit/<int:commit_id>', methods=['GET', 'POST'])
@login_required
def commit_detail(project_id, commit_id):  # コミット詳細
    project = Project.query.get_or_404(project_id)
    commit = Commit.query.get_or_404(commit_id)
    form = CommentForm()

    if form.validate_on_submit():
        comment = CommitComment(content=form.content.data, commit_id=commit.id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
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
        flash('コメントが投稿されました！')
        return redirect(url_for('commit_detail', project_id=project_id, commit_id=commit_id))

    comments = CommitComment.query.filter_by(commit_id=commit_id).all()

    return render_template('commit_detail.html', project=project, commit=commit, form=form, comments=comments)

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


@app.route('/notification/<int:notification_id>/respond/<string:response>', methods=['GET'])
@login_required
def respond_to_invitation(notification_id, response):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id == current_user.id:
        if response == 'accept':
            notification.status = 'accepted'
            # メンバーに追加する
            project = notification.project
            project.members.append(current_user)  # ここでメンバーに追加
            db.session.commit()
            flash('You have accepted the invitation.', 'success')
        elif response == 'decline':
            notification.status = 'declined'
            db.session.commit()
            flash('You have declined the invitation.', 'error')
    else:
        flash('You are not authorized to respond to this notification.', 'error')

    return redirect(url_for('home'))

