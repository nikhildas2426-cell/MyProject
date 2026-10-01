from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "stremex_secret_key"

UPLOAD_POSTERS = "static/posters"
UPLOAD_VIDEOS = "static/videos"

os.makedirs(UPLOAD_POSTERS, exist_ok=True)
os.makedirs(UPLOAD_VIDEOS, exist_ok=True)


# -----------------------------
# DATABASE
# -----------------------------
def get_db():
    conn = sqlite3.connect("stremex.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        genre TEXT,
        language TEXT,
        description TEXT,
        poster TEXT,
        video TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS likes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        movie_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        movie_id INTEGER,
        rating INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mylist(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        movie_id INTEGER
    )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# INDEX
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login")
def login():
    return render_template("login.html")


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/signup")
def signup():
    return render_template("signup.html")


# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["POST"])
def register():

    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO users(username,email,password)
        VALUES(?,?,?)
        """, (username, email, password))

        conn.commit()

    except:
        conn.close()
        return render_template(
            "signup.html",
            error="Username or Email already exists"
        )

    conn.close()

    return redirect("/login")


# -----------------------------
# LOGIN CHECK
# -----------------------------
@app.route("/check_login", methods=["POST"])
def check_login():

    username = request.form["username"]
    password = request.form["password"]

    if username == "admin" and password == "admin123":
        session["admin"] = True
        return redirect("/admin")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM users
    WHERE username=? AND password=?
    """, (username, password))

    user = cursor.fetchone()

    conn.close()

    if user:
        session["username"] = username
        return redirect("/home")

    return render_template(
        "login.html",
        error="Invalid Username or Password"
    )


# -----------------------------
# HOME
# -----------------------------
@app.route("/home")
def home():

    conn = get_db()
    cursor = conn.cursor()

    # Latest uploaded movie for banner
    cursor.execute("""
        SELECT *
        FROM movies
        ORDER BY id DESC
        LIMIT 1
    """)
    featured_movie = cursor.fetchone()

    # Latest 5 movies
    cursor.execute("""
        SELECT *
        FROM movies
        ORDER BY id DESC
        LIMIT 5
    """)
    movies = cursor.fetchall()

    likes = {}
    ratings = {}
    mylist_movies = []

    if "username" in session:

        cursor.execute("""
            SELECT movie_id
            FROM mylist
            WHERE username=?
        """, (session["username"],))

        mylist_movies = [
            row["movie_id"]
            for row in cursor.fetchall()
        ]

    for movie in movies:

        cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE movie_id=?",
            (movie["id"],)
        )
        likes[movie["id"]] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(rating) FROM ratings WHERE movie_id=?",
            (movie["id"],)
        )

        avg = cursor.fetchone()[0]

        ratings[movie["id"]] = round(avg,1) if avg else 0

    conn.close()

    return render_template(
        "home.html",
        featured_movie=featured_movie,
        movies=movies,
        likes=likes,
        ratings=ratings,
        mylist_movies=mylist_movies
    )
# -----------------------------
# LIKE
# -----------------------------
@app.route("/like/<int:id>")
def like(id):

    if "username" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM likes
        WHERE username=? AND movie_id=?
    """,
    (session["username"], id))

    existing = cursor.fetchone()

    if not existing:

        cursor.execute("""
            INSERT INTO likes(username,movie_id)
            VALUES(?,?)
        """,
        (session["username"], id))

        conn.commit()

    conn.close()

    return redirect("/home")


# -----------------------------
# RATE
# -----------------------------
@app.route("/rate/<int:id>/<int:rating>")
def rate(id, rating):

    if "username" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM ratings
        WHERE username=? AND movie_id=?
    """,
    (session["username"], id))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            UPDATE ratings
            SET rating=?
            WHERE username=? AND movie_id=?
        """,
        (rating, session["username"], id))

    else:

        cursor.execute("""
            INSERT INTO ratings(username,movie_id,rating)
            VALUES(?,?,?)
        """,
        (session["username"], id, rating))

    conn.commit()
    conn.close()

    return redirect("/home")


# -----------------------------
# MY LIST
# -----------------------------
@app.route("/mylist/<int:id>")
def add_mylist(id):

    if "username" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM mylist
        WHERE username=? AND movie_id=?
    """,
    (session["username"], id))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            DELETE FROM mylist
            WHERE username=? AND movie_id=?
        """,
        (session["username"], id))

    else:

        cursor.execute("""
            INSERT INTO mylist(username,movie_id)
            VALUES(?,?)
        """,
        (session["username"], id))

    conn.commit()
    conn.close()

    return redirect("/home")

# -----------------------------
# ADMIN
# -----------------------------

# -----------------------------
# UPLOAD MOVIE
# -----------------------------
@app.route("/upload_movie", methods=["POST"])
def upload_movie():

    if "admin" not in session:
        return redirect("/login")

    name = request.form["name"]
    genre = request.form["genre"]
    language = request.form["language"]
    description = request.form["description"]

    poster = request.files["poster"]
    video = request.files["video"]

    poster_name = secure_filename(poster.filename)
    video_name = secure_filename(video.filename)

    poster.save(
        os.path.join(
            UPLOAD_POSTERS,
            poster_name
        )
    )

    video.save(
        os.path.join(
            UPLOAD_VIDEOS,
            video_name
        )
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO movies
    (name,genre,language,description,poster,video)
    VALUES(?,?,?,?,?,?)
    """,
    (
        name,
        genre,
        language,
        description,
        "posters/" + poster_name,
        "videos/" + video_name
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


# -----------------------------
# DELETE MOVIE
# -----------------------------
@app.route("/delete_movie/<int:id>")
def delete_movie(id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM movies WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")
@app.route("/movies")
def movies_page():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM movies
        ORDER BY language,name
    """)

    movies = cursor.fetchall()

    languages = {}

    for movie in movies:

        lang = movie["language"]

        if lang not in languages:
            languages[lang] = []

        languages[lang].append(movie)

    likes = {}
    ratings = {}
    mylist_movies = []

    if "username" in session:

        cursor.execute("""
            SELECT movie_id
            FROM mylist
            WHERE username=?
        """, (session["username"],))

        mylist_movies = [
            row["movie_id"]
            for row in cursor.fetchall()
        ]

    for movie in movies:

        cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE movie_id=?",
            (movie["id"],)
        )

        likes[movie["id"]] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(rating) FROM ratings WHERE movie_id=?",
            (movie["id"],)
        )

        avg = cursor.fetchone()[0]

        ratings[movie["id"]] = round(avg,1) if avg else 0

    conn.close()

    return render_template(
        "movies.html",
        languages=languages,
        likes=likes,
        ratings=ratings,
        mylist_movies=mylist_movies
    )
@app.route("/admin/users")
def admin_users():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM users
    ORDER BY id DESC
    """)

    users = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_users.html",
        users=users
    )
@app.route("/admin/movies")
def admin_movies():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM movies
    ORDER BY id DESC
    """)

    movies = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_movies.html",
        movies=movies
    )
@app.route("/admin/analytics")
def admin_analytics():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM likes")
    total_likes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ratings")
    total_ratings = cursor.fetchone()[0]

    cursor.execute("""
    SELECT movies.name,
           COUNT(likes.id) as likes
    FROM movies
    LEFT JOIN likes
    ON movies.id = likes.movie_id
    GROUP BY movies.id
    ORDER BY likes DESC
    """)
    liked_movies = cursor.fetchall()

    cursor.execute("""
    SELECT movies.name,
           ROUND(AVG(ratings.rating),1) as rating
    FROM movies
    LEFT JOIN ratings
    ON movies.id = ratings.movie_id
    GROUP BY movies.id
    """)
    rated_movies = cursor.fetchall()

    cursor.execute("""
    SELECT language,
           COUNT(*) as count
    FROM movies
    GROUP BY language
    """)
    languages = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_analytics.html",
        total_users=total_users,
        total_movies=total_movies,
        total_likes=total_likes,
        total_ratings=total_ratings,
        liked_movies=liked_movies,
        rated_movies=rated_movies,
        languages=languages
    )
@app.route("/admin")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Total Movies
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()[0]

    # Total Likes
    cursor.execute("SELECT COUNT(*) FROM likes")
    total_likes = cursor.fetchone()[0]

    # Total Ratings
    cursor.execute("SELECT COUNT(*) FROM ratings")
    total_ratings = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_movies=total_movies,
        total_likes=total_likes,
        total_ratings=total_ratings
    )
@app.route("/mylist")
def view_mylist():

    if "username" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT movies.*
    FROM mylist
    JOIN movies
    ON movies.id = mylist.movie_id
    WHERE mylist.username = ?
    """, (session["username"],))

    saved_movies = cursor.fetchall()

    likes = {}
    ratings = {}

    for movie in saved_movies:

        cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE movie_id=?",
            (movie["id"],)
        )
        likes[movie["id"]] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(rating) FROM ratings WHERE movie_id=?",
            (movie["id"],)
        )

        avg = cursor.fetchone()[0]

        ratings[movie["id"]] = round(avg, 1) if avg else 0

    conn.close()

    return render_template(
        "mylist.html",
        saved_movies=saved_movies,
        likes=likes,
        ratings=ratings
    )
@app.route("/suggestions")
def suggestions():

    if "username" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    username = session["username"]

    # Get user's liked genres
    cursor.execute("""
        SELECT m.genre
        FROM likes l
        JOIN movies m
        ON l.movie_id = m.id
        WHERE l.username = ?
    """, (username,))

    genres = [row["genre"] for row in cursor.fetchall()]

    if not genres:
        cursor.execute("""
            SELECT *
            FROM movies
            ORDER BY id DESC
            LIMIT 12
        """)
        suggested_movies = cursor.fetchall()

    else:

        genre_count = {}

        for genre in genres:
            genre_count[genre] = genre_count.get(genre, 0) + 1

        favorite_genre = max(
            genre_count,
            key=genre_count.get
        )

        cursor.execute("""
            SELECT *
            FROM movies
            WHERE genre=?
            ORDER BY id DESC
        """, (favorite_genre,))

        suggested_movies = cursor.fetchall()

    likes = {}
    ratings = {}

    for movie in suggested_movies:

        cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE movie_id=?",
            (movie["id"],)
        )
        likes[movie["id"]] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(rating) FROM ratings WHERE movie_id=?",
            (movie["id"],)
        )

        avg = cursor.fetchone()[0]

        ratings[movie["id"]] = round(avg,1) if avg else 0

    conn.close()

    return render_template(
        "suggestions.html",
        movies=suggested_movies,
        likes=likes,
        ratings=ratings,
        favorite_genre=favorite_genre if genres else "Popular"
    )
if __name__ == "__main__":
    app.run(debug=True)
