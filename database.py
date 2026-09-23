import sqlite3

from flask import current_app, g


# Open a SQLite connection for the current request or app context.
# Flask stores it on the special "g" object so each request gets its own connection.
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        # Enforce foreign key rules so related records are validated correctly.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def query_db(query, parameters=()):
    """Execute a parameterized read query and return all matching rows."""
    return get_db().execute(query, parameters).fetchall()


# Close the database connection when the request context ends.
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


# Initialize the database schema by executing the SQL script in schema.sql.
def init_db():
    database = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        database.executescript(schema_file.read().decode("utf-8"))
    database.commit()
