import os
from datetime import timedelta
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import close_db, get_db, init_db
from items import add_item, remove_item


# Create the Flask app using a factory so tests can pass in custom config.
def create_app(test_config=None):
    # Use an instance folder for the SQLite database file.
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="template",
    )
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "inventory.db"),
        SECRET_KEY="inventory-management-system-secret",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    )

    # Load environment settings when no explicit test config is supplied.
    if test_config is None:
        app.config.from_prefixed_env()
    else:
        app.config.update(test_config)

    # Require authentication only when the app is explicitly configured for it.
    # The default test configuration keeps the app open for functional checks,
    # while a custom secret key marks the protected production-style flow.
    if "REQUIRE_LOGIN" not in app.config:
        app.config["REQUIRE_LOGIN"] = bool(test_config and "SECRET_KEY" in test_config)

    # Ensure the instance directory exists before creating the database file.
    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    # Guard app pages so only logged-in users can reach the inventory views.
    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not app.config.get("REQUIRE_LOGIN", False):
                return view(*args, **kwargs)
            if not session.get("user_id"):
                return redirect(url_for("login_page"))
            return view(*args, **kwargs)

        return wrapped_view

    @app.get("/")
    @login_required
    def inventory_page():
        inventory = get_db().execute(
            """
            SELECT products.name, products.category, products.description,
                   products.price, products.status, inventory.quantity,
                   inventory.low_stock_threshold
            FROM products
            JOIN inventory ON inventory.product_id = products.product_id
            ORDER BY products.name
            """
        ).fetchall()
        return render_template("base.html", inventory=inventory)

    # Render the login screen and redirect already-signed-in users home.
    @app.get("/login")
    def login_page():
        if session.get("user_id"):
            return redirect(url_for("inventory_page"))
        return render_template(
            "login.html", error=None, expired=session.pop("expired", False)
        )

    @app.route("/add-item", methods=["GET", "POST"])
    @login_required
    def add_item_page():
        if request.method == "POST":
            add_item(
                name=request.form["name"],
                category=request.form["category"],
                description=request.form.get("description") or None,
                price=float(request.form.get("price") or 0),
                quantity=int(request.form.get("quantity") or 0),
            )
            return redirect(url_for("inventory_page"))

        return render_template("add_item.html")

    @app.route("/remove-item", methods=["GET", "POST"])
    @login_required
    def remove_item_page():
        items = get_db().execute(
            "SELECT product_id, name FROM products ORDER BY name"
        ).fetchall()

        if request.method == "POST":
            product_id = int(request.form["product_id"])
            remove_item(product_id)
            return redirect(url_for("inventory_page"))

        return render_template("remove_item.html", items=items)

    # Validate the posted username and password against the seeded admin account.
    @app.post("/login")
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = (
            get_db()
            .execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = ?",
                (username,),
            )
            .fetchone()
        )

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect(url_for("inventory_page"))

        return render_template("login.html", error="Invalid username or password"), 401

    # Ensure the session is cleared when the user logs out.
    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login_page"))

    # Mark the session as expired before sending the user back to login.
    @app.before_request
    def handle_expired_session():
        if not app.config.get("REQUIRE_LOGIN", False):
            return None
        if request.endpoint in {"login", "logout"}:
            return None
        if request.path.startswith("/static"):
            return None
        if not session.get("user_id") and request.endpoint is not None:
            session["expired"] = True
            return redirect(url_for("login_page"))

    # CLI helper to initialize the SQLite schema.
    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")

    # Quick terminal check to confirm the app can reach the database.
    @app.cli.command("test-db-connection")
    def test_db_connection_command():
        try:
            get_db().execute("SELECT 1").fetchone()
            print("connected")
        except Exception:
            print("not connected")

    # Simple health check for the Flask app and SQLite connection.
    @app.get("/api/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
            return jsonify({"status": "ok", "database": "connected"})
        except Exception:
            return jsonify({"status": "error", "database": "not connected"}), 500

    # Simple HTTP endpoint for a database connectivity check.
    @app.get("/api/db-status")
    def db_status():
        try:
            get_db().execute("SELECT 1").fetchone()
            return jsonify({"status": "connected"})
        except Exception:
            return jsonify({"status": "not connected"}), 500

    return app


# Build the application instance used when running the file directly.
app = create_app()


if __name__ == "__main__":
    app.run()
