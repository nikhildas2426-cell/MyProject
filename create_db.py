import sqlite3

conn = sqlite3.connect("stremex.db")
cursor = conn.cursor()

# Users
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
)
""")

# Likes
cursor.execute("""
CREATE TABLE IF NOT EXISTS likes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    movie_name TEXT
)
""")

# Ratings
cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    movie_name TEXT,
    rating INTEGER
)
""")

# My List
cursor.execute("""
CREATE TABLE IF NOT EXISTS mylist(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    movie_name TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully")