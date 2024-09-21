from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
import click
import smtplib


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
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
        # Fetch posts that belong to the selected category
        posts = Post.query.filter_by(category=category).all()
        header = f"{category} Blogs"
    else:
        # No category, show recent posts or all categories
        posts = Post.query.order_by(Post.id.desc()).limit(9).all()  # Example: show the 5 most recent posts
        header = "Recent Blogs"

    # Fetch all unique categories from the Post table
    categories = db.session.query(Post.category).distinct().all()
    category_list = [cat[0] for cat in categories]

    # Render blog.html with posts, categories, and current category or header
    return render_template("blog.html", posts=posts, categories=category_list, header=header)


@app.route("/<category>")
def show_category(category):
    # Replace hyphens with spaces to match category names in the database
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
        messages = request.form['message']

        my_email = "ruthacolatse.official@gmail.com"
        password = "ekdkxegsfexyfpkd"

        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(user=my_email, password=password)
            connection.sendmail(from_addr=email, to_addrs=my_email,
                                msg=f"Subject: New Message From Your Website!\n\nName: {name}\nEmail address: {email}\nMessage: {messages}")
        return render_template("contact.html", message_sent=True, copyright_year=year)
    return render_template("contact.html", message_sent=False, copyright_year=year)


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

    # Get unique categories for navigation
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
        # Perform a search by filtering posts with titles or content matching the query
        results = Post.query.filter(
            (Post.title.ilike(f'%{query}%')) | (Post.content.ilike(f'%{query}%'))
        ).all()
    else:
        results = []

    return render_template('search.html', query=query, results=results)


@app.route('/submit_comment/<int:post_id>', methods=['POST'])
def submit_comment(post_id):
    # Retrieve the data from the form
    name = request.form['name']
    email = request.form['email']
    comment_content = request.form['comment']

    # Check if this is a reply to an existing comment
    parent_id = request.form.get('parent_id')  # Use parent_id for replies

    # Create a new comment instance
    new_comment = Comment(
        post_id=post_id,
        name=name,
        email=email,
        content=comment_content,
        timestamp=datetime.utcnow()  # Use the current UTC timestamp
    )

    if parent_id:
        # If there's a parent_id, this is a reply
        new_comment.parent_id = parent_id

    # Add and commit the new comment to the database
    db.session.add(new_comment)
    db.session.commit()

    # Redirect back to the post page after submission
    return redirect(url_for('show_post', index=post_id))


if __name__ == "__main__":
    app.run(debug=True)
