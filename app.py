import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

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
    )

    # Load environment settings when no explicit test config is supplied.
    if test_config is None:
        app.config.from_prefixed_env()
    else:
        app.config.update(test_config)

    # Ensure the instance directory exists before creating the database file.
    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    @app.get("/")
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

    @app.get("/login")
    def login_page():
        return render_template("login.html")
    
    @app.route("/add-item", methods=["GET", "POST"])
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
    def remove_item_page():
        items = get_db().execute(
            "SELECT product_id, name FROM products ORDER BY name"
        ).fetchall()

        if request.method == "POST":
            product_id = int(request.form["product_id"])
            remove_item(product_id)
            return redirect(url_for("inventory_page"))

        return render_template("remove_item.html", items=items)

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
