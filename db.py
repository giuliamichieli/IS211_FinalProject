import sqlite3, datetime
from flask import current_app, g

DATABASE = 'blog.db'

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)for idx, value in enumerate(row))

def get_db():
    db = getattr(g, '_database', None)

    if db is None:
        db = g._database = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = make_dicts

    return db

def query(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()

    return (rv[0] if rv else None) if one else rv


def insert(query, vals=(), many=False):
    if many:
        cur = get_db().executemany(query, vals)
    else:
        cur = get_db().execute(query, vals)

    last_row_id = cur.lastrowid
    cur.close()
    get_db().commit()
    return last_row_id


def update(query, vals=()):
    cur = get_db().execute(query, vals)
    cur.close()
    get_db().commit()
    return True


def delete(query, vals=()):
    cur = get_db().execute(query, vals)
    cur.close()
    get_db().commit()
    return True


def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

    users = query("select * from users")
    categories = query("select * from categories")
    posts = query("select * from posts")

    if not users:
        insert("Insert into users (first_name, last_name, email, password)\
                     values (?, ?, ?, ?)",
                (
                    ("John", "L", "john@example.com", "password"),
                    ("Paul", "MC", "paul@example.com", "password"),
                    ("George", "H", "george@example.com", "password"),
                    ("Ringo", "S", "ringo@example.com", "password")
                ),
                True
            )
        print("Loaded dummy users into db")

    if not categories:
        insert("Insert into categories\
                (\
                    category_name,\
                    category_display_name,\
                    category_description\
                ) values (?, ?, ?)",
                (
                    ("iss-orbit", "ISS Orbit", "Posts about Orbit of the International Space Station."),
                    ("bitcoin-basics", "Bitcoin vs Fiat", "Posts about cryptocurrencies."),
                ),
                True
            )
        print("Loaded dummy categories into db")

    if not posts:
        short_content = """<p>ISS Orbitr around the Earth</p>"""
        content = """<h1>Testing more content</h1><p>ISS has been orbiting the Earth for more than a decade!"""
        timestamp = datetime.datetime.now()
        insert("Insert into posts\
                (\
                    author_id,\
                    category_id,\
                    title,\
                    slug,\
                    short_content,\
                    content,\
                    is_published,\
                    published_at,\
                    updated_at\
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (1, 1, "ISS Orbit", "iss-orbit", short_content, content, 1, timestamp, timestamp),
                    (1, 2, "ETH Fiat", "eth-fiat", short_content, content, 1, timestamp, timestamp),
                    (2, 1, "More Specs", "more-spects", short_content, content, 1, timestamp, timestamp),
                    (2, 2, "Less Specs", "less-specs", short_content, content, 1, timestamp, timestamp),
                    (3, 1, "Crypto Getting Bullish", "crypto-getting-bullish", short_content, content, 1, timestamp, timestamp),
                    (3, 2, "Buy Tesla Stocks", "buy-tesla-stocks", short_content, content, 1, timestamp, timestamp),
                    (4, 1, "Learn Python", "learn-python", short_content, content, 0, timestamp, timestamp)
                ),
                True
            )
        print("Loaded dummy posts results into db")
