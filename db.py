import pymysql
from flask import g

def connect_db():
    return pymysql.connect(
        host='localhost',
        user='root',
        port=3310,
        password='',
        database='flask',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_db():
    if 'db' not in g:
        g.db = connect_db()
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
