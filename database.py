import logging
import os
import sqlite3

from flask import current_app, g, has_request_context, session
from werkzeug.security import generate_password_hash


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


def log_event(event_type, description, user_id=None):
    """Write an audit row to event_logs.

    Does not commit: call it before the caller's commit() so the log entry and
    the change it describes succeed or roll back together. user_id defaults to
    the logged-in user when called inside a request.
    """
    # Outside a request (scripts, tests) there is no session, so user_id stays NULL.
    if user_id is None and has_request_context():
        user_id = session.get("user_id")
    # Reuses the request's connection so the row joins the caller's open transaction.
    get_db().execute(
        "INSERT INTO event_logs (user_id, event_type, description) VALUES (?, ?, ?)",
        (user_id, event_type, description),
    )
    _get_file_logger().info("user=%s | %s | %s", user_id, event_type, description)


# Build the file logger once; LOG_DIR config overrides the default docs/Logs folder.
def _get_file_logger():
    logger = logging.getLogger("inventory.events")
    if not logger.handlers:
        log_dir = current_app.config.get(
            "LOG_DIR", os.path.join(current_app.root_path, "docs", "Logs")
        )
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(
            os.path.join(log_dir, "event_log.txt"), encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


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

    # Seed the default admin account and force a password change on first login. - NL
    database.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, must_change_password) VALUES (?, ?, 1)",
        ("admin", generate_password_hash("admin")),
    )
    database.commit()
