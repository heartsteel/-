# app.py

from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask import send_from_directory, render_template, Response
from flask import render_template
from docx import Document
from io import BytesIO
from werkzeug.utils import secure_filename
import os
ALLOWED_EXTENSIONS = { 'txt','png','jpeg','jpg','gif'}
db = SQLAlchemy()
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def create_app():
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:114514@localhost/vandark'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['AVATAR_FOLDER'] = 'static/avatars'
    db.init_app(app)

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password = db.Column(db.String(128), nullable=False)
        is_admin = db.Column(db.Boolean, default=False)
        avatar = db.Column(db.String(128), default='default.jpg')

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    @login_required
    def index():
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        return render_template('index.html', files=files)

    @app.route('/upload', methods=['POST'])
    @login_required
    def upload_file():
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        if file:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            return redirect(url_for('index'))
    @app.route('/change_avatar', methods=['POST'])
    @login_required
    def change_avatar():
        new_avatar = request.files.get('new_avatar')

        if new_avatar and allowed_file(new_avatar.filename):
            filename = secure_filename(new_avatar.filename)
            new_avatar.save(os.path.join(app.config['AVATAR_FOLDER'], filename))

            # 更新数据库中的头像信息
            current_user.avatar = filename
            db.session.commit()

            flash('头像更新成功！', 'success')
        else:
            flash('不支持的头像文件格式，或者头像文件为空', 'danger')

        return redirect(url_for('user_profile', username=current_user.username))

    @app.route('/reset_avatar', methods=['POST'])
    @login_required
    def reset_avatar():
        # 重置头像为默认头像
        current_user.avatar = 'default.jpg'
        db.session.commit()

        flash('头像已重置为默认头像！', 'success')
        return redirect(url_for('user_profile', username=current_user.username))
    @app.route('/preview/<filename>')
    @login_required
    def preview_file(filename):
        if allowed_file(filename):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            return render_template('preview_not_supported.html')
    @app.route('/preview_image/<filename>')
    @login_required
    def preview_image(filename):
        response = Response()
        response.headers['Content-Disposition'] = 'inline; filename=' + filename

    # 检查文件类型，如果是docx，将其转换为HTML并在浏览器中显示
        if filename.lower().endswith('docx'):
            docx_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            html_content = convert_docx_to_html(docx_path)
            return render_template('preview_html.html', html_content=html_content)

    # 对于图像类型，直接返回文件
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        return send_file(img_path, mimetype='image/*', as_attachment=False)
    def convert_docx_to_html(docx_path):
        doc = Document(docx_path)
        html_output = BytesIO()
        doc.save(html_output)
        html_content = html_output.getvalue().decode('utf-8')
        return html_content
    @app.route('/download/<filename>')
    @login_required
    def download_file(filename):
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

    @app.route('/delete/<filename>')
    @login_required
    def delete_file(filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        return redirect(url_for('index'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()

            if user and user.password == password:
                login_user(user)
                flash('Login successful!', 'success')
                if user.is_admin:
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Login failed. Check your username and password.', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        username = None  # 提前为 username 赋一个默认值

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            is_admin = request.form.get('account_type') == 'admin'

        # 处理上传的头像文件
            if 'avatar' in request.files:
                avatar = request.files['avatar']
                if avatar and allowed_file(avatar.filename):
                    filename = secure_filename(avatar.filename)
                    avatar.save(os.path.join(app.config['AVATAR_FOLDER'], filename))
                else:
                    flash('不支持的头像文件格式，或者头像文件为空', 'danger')
                    return redirect(url_for('register'))

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('用户名已存在，请选择一个不同的用户名。', 'danger')
            else:
                new_user = User(username=username, password=password, is_admin=is_admin, avatar=filename)
                db.session.add(new_user)
                db.session.commit()

                flash('注册成功！现在可以登录了。', 'success')
                return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/admin')
    @login_required
    def admin():
        if current_user.is_admin:
            users = User.query.all()
            return render_template('admin.html', users=users)
        else:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))

    @app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_user(user_id):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))

        user = User.query.get(user_id)

        if request.method == 'POST':
            user.username = request.form['new_username']
            user.password = request.form['new_password']
            db.session.commit()
            flash('User information updated successfully!', 'success')
            return redirect(url_for('admin'))

        return render_template('admin_edit_user.html', user=user)

    @app.route('/admin/delete_user/<int:user_id>')
    @login_required
    def admin_delete_user(user_id):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))

        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()

        flash('User deleted successfully!', 'success')
        return redirect(url_for('admin'))

    @app.route('/admin/add_user', methods=['POST'])
    @login_required
    def admin_add_user():
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))

        new_username = request.form['new_username']
        new_password = request.form['new_password']

        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            flash('Username already exists. Choose a different one.', 'danger')
        else:
            new_user = User(username=new_username, password=new_password, is_admin=False)
            db.session.add(new_user)
            db.session.commit()

            flash('User added successfully!', 'success')
        return redirect(url_for('admin'))
    @app.route('/user_profile')
    @login_required
    def user_profile():
    # 查询用户上传的文件列表与上传文件总数
        user_files = os.listdir(app.config['UPLOAD_FOLDER'])
        total_files = len(user_files)
    
        return render_template('user_profile.html', user=current_user, total_files=total_files, user_files=user_files)

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    return app

if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0', port=5000)
