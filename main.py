from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, LoginForm, RegistrationForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()

my_password = os.getenv('MY_PASSWORD')
my_email = os.getenv('MY_EMAIL')
my_name = "narasimha"
print(my_email)
print(my_password)
app = Flask(__name__)
# SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = my_email
app.config['MAIL_PASSWORD'] = my_password
app.config['MAIL_DEFAULT_SENDER'] = my_email
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False

mail = Mail(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app, size=100, rating='g', default='parameter', force_default=False,
                    force_lower=False, use_ssl=False, base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)

    return decorated_function


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    confirm_password = db.Column(db.String(250), nullable=False)

    posts = db.relationship('BlogPost', backref='User', lazy='dynamic')

    comments = db.relationship('Comment', backref='User', lazy='dynamic')


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author_name = db.Column(db.String(250), nullable=False)

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = db.relationship('Comment', backref='BlogPost', lazy='dynamic')


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    commenter_name = db.Column(db.String(50), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"), nullable=False)

with app.app_context():
        db.create_all()

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == "POST":
        if form.validate_on_submit():

            # if User.query.filter_by(email=request.form.get('email')):
            #     flash("You've already signed up with that email, log in instead!", "danger")
            #     return redirect(url_for('login'))

            name = request.form.get('name')
            email = request.form.get('email')
            sal_pas = request.form.get('password')
            confirm_sal_pas = request.form.get('confirm_password')
            salted_password = generate_password_hash(
                password=sal_pas, method="pbkdf2:sha256", salt_length=8)
            confirm_slated_password = generate_password_hash(
                password=confirm_sal_pas, method="pbkdf2:sha256", salt_length=8)
            password = salted_password
            confirm_password = confirm_slated_password
            new_user = User(name=name, email=email, password=password, confirm_password=confirm_password)
            db.session.add(new_user)
            db.session.commit()
            # This line will authenticate the user with Flask-Login
            login_user(new_user)

            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_email = request.form.get('email')
        login_password = request.form.get('password')

        user = User.query.filter_by(email=login_email).first()
        if not user:
            flash("Email does not exist, please try again.", "danger")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, login_password):
            flash("Password incorrect and try again.", "danger")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if request.method == "POST":
        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash("You need to login or register to comment.", "danger")
                return redirect(url_for('login'))

            new_comment = Comment(text=request.form.get('comment_text'),
                                  commenter_name=current_user.name,
                                  author_id=current_user.id,
                                  post_id=post_id)
            db.session.add(new_comment)
            db.session.commit()
    return render_template("post.html", form=form, post=requested_post, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        recipient1 = "narasimhamurty421@gmail.com"
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        prepared_msg = f"{name}<{email}>,\n\n Hi,\n\n Greetings from {name},\n contact no:{phone}\n message:{message}"
        msg = Message(subject="A Message from the Blog Capstone Project",
                      sender=my_email,
                      recipients=[recipient1],
                      body=prepared_msg)
        mail.send(msg)
        print(my_email)
        flash("Message sent successfully!", "success")
        return redirect(url_for('get_all_posts'))
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if request.method == "POST":
        if form.validate_on_submit():
            new_post = BlogPost(
                author_id=current_user.id,
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author_name=current_user.name,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author_name,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user.name
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
