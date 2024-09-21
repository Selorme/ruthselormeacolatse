from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
import click
import smtplib
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase setup
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_ANON_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# Email and password
google_email = os.getenv('MY_EMAIL')
google_password = os.getenv('PASSWORD')


# Define your PostView to render HTML content properly
class PostView(ModelView):
    column_formatters = {
        'content': lambda v, c, m, p: Markup(m.content)
    }
    edit_template = 'admin/my_post_view.html'  # Ensure this template exists


app = Flask(__name__)

# Config for SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SECRET_KEY'] = '&dQsqo9rYa1%'

# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)

year = datetime.today().year


# Define your models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Post {self.title}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # For replies
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship for replies
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def __repr__(self):
        return f'<Comment {self.content[:20]}...>'


# Initialize Flask-Admin
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')

# Add views for models
admin.add_view(PostView(Post, db.session))  # Use PostView to handle HTML content


# Define your routes
@app.route("/")
def home():
    return render_template("index.html", copyright_year=year)


@app.route("/about")
def about():
    return render_template("about.html", copyright_year=year)


@app.route("/blog", defaults={'category': None})
@app.route("/blog/<category>")
def blogs(category):
    if category:
        posts = Post.query.filter_by(category=category).all()
        header = f"{category} Blogs"
    else:
        posts = Post.query.order_by(Post.id.desc()).limit(9).all()
        header = "Recent Blogs"

    # Fetch all unique categories from the Post table
    categories = db.session.query(Post.category).distinct().all()
    category_list = [cat[0] for cat in categories]

    return render_template("blog.html", posts=posts, categories=category_list, header=header)


@app.route("/<category>")
def show_category(category):
    category = category.replace('-', ' ')
    posts = Post.query.filter_by(category=category).all()
    return render_template("category.html", posts=posts, category=category, copyright_year=year)


@app.route("/Projects")
def projects():
    posts = Post.query.filter_by(category='Projects').all()
    return render_template("projects.html", posts=posts, copyright_year=year)


@app.route("/cvresume")
def cvresume():
    return render_template("cvresume.html", copyright_year=year)


@app.route("/UG-Escapades")
def ugescapades():
    posts = Post.query.filter_by(category='UG Escapades').all()
    return render_template("ugescapades.html", posts=posts, copyright_year=year)


@app.route("/Türkiye-Geçilmez")
def turkiyegecilmez():
    posts = Post.query.filter_by(category='Türkiye Geçilmez').all()
    return render_template("turkiyegecilmez.html", posts=posts, copyright_year=year)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        my_email = google_email
        password = google_password

        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(user=my_email, password=password)
            connection.sendmail(from_addr=my_email, to_addrs=my_email,
                                msg=f"Subject: New Message From Your Website!\n\nName: {name}\nEmail: {email}\nMessage: {message}")

        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template("index.html", message_sent=False, copyright_year=year)


@app.route("/Audacious-Men-Series")
def audacity():
    posts = Post.query.filter_by(category='Audacious Men Series').all()
    return render_template("audacity.html", posts=posts, copyright_year=year)


@app.route("/post/<int:index>")
def show_post(index):
    post = Post.query.get(index)
    if post is None:
        return "Post not found", 404
    all_posts = Post.query.filter_by(category=post.category).all()
    comments = Comment.query.filter_by(post_id=index).order_by(Comment.timestamp.desc()).all()

    categories = db.session.query(Post.category).distinct().all()
    category_list = [category[0] for category in categories]
    return render_template("post.html", post=post, all_posts=all_posts, current_category=post.category,
                           categories=category_list, comments=comments)


@app.cli.command('create-db')
def create_db():
    """Create the database tables."""
    with app.app_context():
        db.create_all()
    click.echo('Database created.')


@app.route('/search')
def search():
    query = request.args.get('q')
    if query:
        results = Post.query.filter(
            (Post.title.ilike(f'%{query}%')) | (Post.content.ilike(f'%{query}%'))
        ).all()
    else:
        results = []

    return render_template('search.html', query=query, results=results)


@app.route("/submit_comment/<int:post_id>", methods=['POST'])
def submit_comment(post_id):
    parent_id = request.form.get('parent_id', type=int)
    name = request.form.get('reply_name') if parent_id else request.form.get('name')
    comment_content = request.form.get('reply_content') if parent_id else request.form.get('comment')

    post_exists = Post.query.filter_by(id=post_id).first()
    if not post_exists:
        return "Post not found", 404

    if not name or not comment_content:
        return "Name and comment are required", 400

    # Create and save the new comment in SQLite
    timestamp = datetime.utcnow()
    new_comment = Comment(
        post_id=post_id,
        name=name,
        content=comment_content,
        timestamp=timestamp,
        parent_id=parent_id
    )
    db.session.add(new_comment)
    db.session.commit()

    # Prepare data for Supabase
    data = {
        'post_id': post_id,
        'name': name,
        'content': comment_content,
        'timestamp': timestamp.isoformat(),
        'parent_id': parent_id
    }

    print("Data being sent to Supabase:", data)  # Log the data

    # Check if in production and save to Supabase if true
    response = supabase.table('comment').insert(data).execute()

    if response.status_code != 201:  # Check for successful insertion
        print("Error inserting comment:", response.json())  # Log the error
        # Optionally: You could roll back the SQLite commit here if needed
    else:
        print("Comment added successfully:", response.data)

    return redirect(url_for('show_post', index=post_id))



if __name__ == "__main__":
    app.run(debug=True)
