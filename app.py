import base64
import io
import os
import secrets
from datetime import timedelta
from functools import wraps

import pyotp
import qrcode
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import close_db, get_db, init_db, query_db
from items import add_item, adjust_quantity, remove_item

BACKUP_CODE_COUNT = 8  # Number of one-time backup codes issued per user - NL


# Render a TOTP provisioning URI as a base64 PNG the browser can show inline. - NL
def build_qr_code_data_uri(provisioning_uri):
    image = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


# Create fresh single-use backup codes and return the plaintext values to show once. - NL
def generate_backup_codes():
    return [secrets.token_hex(5) for _ in range(BACKUP_CODE_COUNT)]


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

    # Ensure the instance directory exists before creating the database file.
    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    # Guard app pages so only logged-in users can reach the inventory views.
    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login_page"))
            return view(*args, **kwargs)

        return wrapped_view

    # Complete a login by populating the permanent session. - NL
    def finish_login(user_id, username, must_change_password):
        session.clear()
        session.permanent = True
        session["user_id"] = user_id
        session["username"] = username
        session["must_change_password"] = bool(must_change_password)

    # Consume a matching, unused backup code if the submitted value redeems one. - NL
    def redeem_backup_code(user_id, code):
        if not code:
            return False

        database = get_db()
        candidates = database.execute(
            """SELECT backup_code_id, code_hash FROM user_backup_codes
            WHERE user_id = ? AND used_at IS NULL""",
            (user_id,),
        ).fetchall()

        for candidate in candidates:
            if check_password_hash(candidate["code_hash"], code):
                database.execute(
                    "UPDATE user_backup_codes SET used_at = CURRENT_TIMESTAMP WHERE backup_code_id = ?",
                    (candidate["backup_code_id"],),
                )
                database.commit()
                return True

        return False

    @app.get("/")
    @login_required
    def inventory_page():
        inventory = query_db("""
            SELECT products.product_id, products.name, products.category,
                   products.price, inventory.quantity,
                   inventory.low_stock_threshold
            FROM products
            JOIN inventory ON inventory.product_id = products.product_id
            WHERE products.status = 'active'
            ORDER BY products.name COLLATE NOCASE
            """)
        return render_template("inventory.html", inventory=inventory)

    # Show queued orders and, when selected, the order form for one low-stock item.
    @app.get("/reorders")
    @login_required
    def reorder_page():
        database = get_db()
        selected_item = None
        selected_product_id = request.args.get("product_id", type=int)
        if selected_product_id is not None:
            selected_item = database.execute(
            """
            SELECT products.product_id, products.name, inventory.quantity,
                   inventory.low_stock_threshold, inventory.reorder_amount
            FROM products
            JOIN inventory ON inventory.product_id = products.product_id
            WHERE products.status = 'active'
              AND products.product_id = ?
              AND inventory.quantity <= inventory.low_stock_threshold
            """,
            (selected_product_id,),
            ).fetchone()
        queued_orders = database.execute(
            """
            SELECT reorders.reorder_id, reorders.product_id,
                   products.name, reorders.quantity_ordered,
                   reorders.reorder_date, reorders.status
            FROM reorders
            JOIN products ON products.product_id = reorders.product_id
            WHERE reorders.status IN ('pending', 'ordered')
            ORDER BY reorders.reorder_date DESC, reorders.reorder_id DESC
            """
        ).fetchall()
        return render_template(
            "reorders.html",
            selected_item=selected_item,
            queued_orders=queued_orders,
        )

    # Queue one reorder using either the configured or a user-entered amount.
    @app.post("/reorders")
    @login_required
    def queue_reorder():
        try:
            product_id = int(request.form.get("product_id", ""))
        except (TypeError, ValueError):
            return "Invalid inventory item", 400

        database = get_db()
        item = database.execute(
            """
            SELECT products.name, inventory.quantity, inventory.low_stock_threshold,
                   inventory.reorder_amount
            FROM products
            JOIN inventory ON inventory.product_id = products.product_id
            WHERE products.product_id = ? AND products.status = 'active'
            """,
            (product_id,),
        ).fetchone()

        if item is None:
            return "Invalid inventory item", 400
        if item["quantity"] > item["low_stock_threshold"]:
            return "Item is not currently low in stock", 400

        # The checkbox selects a saved automatic amount; otherwise use the custom quantity.
        use_automatic_amount = request.form.get("automatic_amount") == "1"
        if use_automatic_amount:
            try:
                quantity_ordered = int(
                    request.form.get("automatic_reorder_amount", "")
                )
            except (TypeError, ValueError):
                return "Enter a valid automatic reorder amount", 400
            # Save the selected automatic amount for the next reorder of this item.
            database.execute(
                "UPDATE inventory SET reorder_amount = ? WHERE product_id = ?",
                (quantity_ordered, product_id),
            )
        else:
            try:
                quantity_ordered = int(request.form.get("quantity_ordered", ""))
            except (TypeError, ValueError):
                return "Enter a valid order quantity", 400
        # Both manual and automatic quantities must satisfy the positive-order constraint.
        if quantity_ordered <= 0:
            return "Order quantity must be greater than zero", 400

        active_order = database.execute(
            """
            SELECT 1 FROM reorders
            WHERE product_id = ? AND status IN ('pending', 'ordered')
            """,
            (product_id,),
        ).fetchone()
        if active_order is not None:
            return "An active reorder already exists for this item", 409

        database.execute(
            """
            INSERT INTO reorders (product_id, quantity_ordered, status)
            VALUES (?, ?, 'pending')
            """,
            (product_id, quantity_ordered),
        )
        database.execute(
            """
            INSERT INTO event_logs (user_id, event_type, description)
            VALUES (?, 'reorder_queued', ?)
            """,
            (
                session["user_id"],
                f"Queued reorder for {item['name']} ({quantity_ordered} units)",
            ),
        )
        database.commit()
        return redirect(url_for("reorder_page"))

    # Cancel a pending or ordered reorder from the queue.
    @app.post("/reorders/<int:reorder_id>/cancel")
    @login_required
    def cancel_reorder(reorder_id):
        database = get_db()
        order = database.execute(
            """
            SELECT reorders.reorder_id, products.name
            FROM reorders
            JOIN products ON products.product_id = reorders.product_id
            WHERE reorders.reorder_id = ?
              AND reorders.status IN ('pending', 'ordered')
            """,
            (reorder_id,),
        ).fetchone()
        if order is None:
            return "Queued order not found", 404

        database.execute(
            "UPDATE reorders SET status = 'cancelled' WHERE reorder_id = ?",
            (reorder_id,),
        )
        database.execute(
            """
            INSERT INTO event_logs (user_id, event_type, description)
            VALUES (?, 'reorder_cancelled', ?)
            """,
            (session["user_id"], f"Cancelled reorder for {order['name']}"),
        )
        database.commit()
        return redirect(url_for("reorder_page"))

    # Adjust stock from the inventory page.
    @app.post("/adjust-stock")
    @login_required
    def adjust_stock():
        try:
            # The dialog sends a signed amount: positive for adding and negative for removing.
            product_id = int(request.form.get("product_id", ""))
            quantity_change = int(request.form.get("quantity_change", ""))
            if quantity_change == 0:
                raise ValueError("Invalid quantity change")
            adjust_quantity(product_id, quantity_change)
        except (TypeError, ValueError) as error:
            return str(error), 400

        return redirect(url_for("inventory_page"))

    # Render the login screen and redirect already-signed-in users home.
    @app.get("/login")
    def login_page():
        if session.get("user_id"):
            return redirect(url_for("inventory_page"))
        return render_template(
            "login.html", error=None, expired=session.pop("expired", False)
        )

    # Validate the posted username and password against the seeded admin account.
    @app.post("/login")
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = (
            get_db()
            .execute(
                """SELECT users.user_id, users.username, users.password_hash,
                          COALESCE(user_2fa.is_enabled, 0) AS is_enabled,
                          users.must_change_password
                FROM users
                LEFT JOIN user_2fa ON user_2fa.user_id = users.user_id
                WHERE users.username = ?""",
                (username,),
            )
            .fetchone()
        )

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            if user["is_enabled"]:
                # Hold the login until a valid authenticator code is provided. - NL
                session["pending_2fa_user_id"] = user["user_id"]
                return redirect(url_for("verify_2fa_page"))

            finish_login(
                user["user_id"], user["username"], user["must_change_password"]
            )

            return redirect(url_for("account_2fa_page"))

        return render_template("login.html", error="Invalid username or password"), 401

    # Show the authenticator code prompt for a password-verified, pending login. - NL
    @app.get("/login/2fa")
    def verify_2fa_page():
        if not session.get("pending_2fa_user_id"):
            return redirect(url_for("login_page"))
        return render_template("verify_2fa.html", error=None)

    # Check the submitted authenticator or backup code and finish the login. - NL
    @app.post("/login/2fa")
    def verify_2fa():
        pending_user_id = session.get("pending_2fa_user_id")
        if not pending_user_id:
            return redirect(url_for("login_page"))

        code = request.form.get("code", "").strip()
        user = (
            get_db()
            .execute(
                """SELECT users.user_id, users.username, user_2fa.secret_key,
                          users.must_change_password
                FROM users
                LEFT JOIN user_2fa ON user_2fa.user_id = users.user_id
                WHERE users.user_id = ?""",
                (pending_user_id,),
            )
            .fetchone()
        )

        if (
            user
            and user["secret_key"]
            and pyotp.TOTP(user["secret_key"]).verify(code, valid_window=1)
        ):
            finish_login(
                user["user_id"], user["username"], user["must_change_password"]
            )
            return redirect(url_for("inventory_page"))

        if user and redeem_backup_code(user["user_id"], code):
            finish_login(
                user["user_id"], user["username"], user["must_change_password"]
            )
            return redirect(url_for("inventory_page"))

        return render_template(
            "verify_2fa.html", error="Invalid authentication code"
        ), 401

    # Ensure the session is cleared when the user logs out.
    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login_page"))

    # Keep partially authenticated sessions on the 2FA challenge until verified. - NL
    @app.before_request
    def require_two_factor_verification():
        if not session.get("pending_2fa_user_id"):
            return None

        allowed_endpoints = {"verify_2fa_page", "verify_2fa", "logout"}
        if request.path.startswith("/static") or request.endpoint in allowed_endpoints:
            return None

        return redirect(url_for("verify_2fa_page"))

    # Mark the session as expired before sending the user back to login.
    @app.before_request
    def handle_expired_session():
        # Pending-2FA endpoints are exempt since the user isn't fully logged in yet. - NL
        if request.endpoint in {
            "login",
            "login_page",
            "logout",
            "verify_2fa_page",
            "verify_2fa",
        }:
            return None
        if request.path.startswith("/static"):
            return None
        if not session.get("user_id") and request.endpoint is not None:
            session["expired"] = True
            return redirect(url_for("login_page"))

    # Block every other page until a required password change is completed. - NL
    @app.before_request
    def require_password_change():
        allowed_endpoints = {"change_password_page", "change_password", "logout"}
        if request.path.startswith("/static") or request.endpoint in allowed_endpoints:
            return None
        if session.get("user_id") and session.get("must_change_password"):
            return redirect(url_for("change_password_page"))

    # Protect the add-item page and accept new inventory submissions.
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
                low_stock_threshold=int(
                    request.form.get("low_stock_threshold") or 0
                ),
            )
            return redirect(url_for("inventory_page"))
        return render_template("add_item.html")

    # Show active items that can be selected for removal.
    @app.get("/remove-item")
    @login_required
    def remove_item_page():
        items = query_db("""
            SELECT product_id, name
            FROM products
            WHERE status = 'active'
            ORDER BY name COLLATE NOCASE
            """)
        return render_template("remove_item.html", items=items)

    # Delete the selected item and return to the current inventory list.
    @app.post("/remove-item")
    @login_required
    def remove_item_action():
        try:
            product_id = int(request.form.get("product_id", ""))
            remove_item(product_id)
        except (TypeError, ValueError):
            return "Invalid inventory item", 400

        return redirect(url_for("inventory_page"))

    # Prompt for a new password when the account is flagged for a forced change. - NL
    @app.get("/account/change-password")
    @login_required
    def change_password_page():
        return render_template("change_password.html", error=None)

    # Apply the new password and clear the forced-change flag. - NL
    @app.post("/account/change-password")
    @login_required
    def change_password():
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(new_password) < 8 or new_password != confirm_password:
            return render_template(
                "change_password.html",
                error="Passwords must match and be at least 8 characters",
            ), 400

        database = get_db()
        database.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE user_id = ?",
            (generate_password_hash(new_password), session["user_id"]),
        )
        database.commit()
        session["must_change_password"] = False
        two_factor = database.execute(
            "SELECT is_enabled FROM user_2fa WHERE user_id = ?",
            (session["user_id"],),
        ).fetchone()
        if not two_factor or not two_factor["is_enabled"]:
            # Send users without enabled 2FA to enrollment after a password change. - NL
            return redirect(url_for("account_2fa_page"))
        return redirect(url_for("inventory_page"))

    # Show current 2FA status and, when not yet enabled, a QR code to scan. - NL
    @app.get("/account/2fa")
    @login_required
    def account_2fa_page():
        database = get_db()
        user = database.execute(
            """SELECT users.username, user_2fa.secret_key,
                      COALESCE(user_2fa.is_enabled, 0) AS is_enabled
            FROM users
            LEFT JOIN user_2fa ON user_2fa.user_id = users.user_id
            WHERE users.user_id = ?""",
            (session["user_id"],),
        ).fetchone()

        if user["is_enabled"]:
            return render_template(
                "account_2fa.html", enabled=True, qr_code=None, secret=None, error=None
            )

        # Reuse a secret already generated for an in-progress enrollment. - NL
        secret = user["secret_key"] or pyotp.random_base32()
        if not user["secret_key"]:
            database.execute(
                """INSERT INTO user_2fa (user_id, secret_key) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    secret_key = excluded.secret_key,
                    updated_at = CURRENT_TIMESTAMP""",
                (session["user_id"], secret),
            )
            database.commit()

        provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
            name=user["username"], issuer_name="Inventory Management System"
        )
        return render_template(
            "account_2fa.html",
            enabled=False,
            qr_code=build_qr_code_data_uri(provisioning_uri),
            secret=secret,
            error=None,
        )

    # Confirm enrollment by checking a live code, then issue one-time backup codes. - NL
    @app.post("/account/2fa/enable")
    @login_required
    def account_2fa_enable():
        database = get_db()
        user = database.execute(
            """SELECT users.username, user_2fa.secret_key
            FROM users
            LEFT JOIN user_2fa ON user_2fa.user_id = users.user_id
            WHERE users.user_id = ?""",
            (session["user_id"],),
        ).fetchone()

        code = request.form.get("code", "").strip()
        if not user or not user["secret_key"]:
            return redirect(url_for("account_2fa_page"))

        if not pyotp.TOTP(user["secret_key"]).verify(code, valid_window=1):
            provisioning_uri = pyotp.TOTP(user["secret_key"]).provisioning_uri(
                name=user["username"], issuer_name="Inventory Management System"
            )
            return render_template(
                "account_2fa.html",
                enabled=False,
                qr_code=build_qr_code_data_uri(provisioning_uri),
                secret=user["secret_key"],
                error="Invalid authentication code",
            ), 400

        backup_codes = generate_backup_codes()
        database.execute(
            """UPDATE user_2fa
            SET is_enabled = 1, confirmed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (session["user_id"],),
        )
        database.execute(
            "DELETE FROM user_backup_codes WHERE user_id = ?", (session["user_id"],)
        )
        database.executemany(
            "INSERT INTO user_backup_codes (user_id, code_hash) VALUES (?, ?)",
            [
                (session["user_id"], generate_password_hash(backup_code))
                for backup_code in backup_codes
            ],
        )
        database.commit()

        return render_template(
            "account_2fa_backup_codes.html", backup_codes=backup_codes
        )

    # Turn 2FA off after re-checking the account password and wipe stored secrets. - NL
    @app.post("/account/2fa/disable")
    @login_required
    def account_2fa_disable():
        database = get_db()
        user = database.execute(
            "SELECT password_hash FROM users WHERE user_id = ?", (session["user_id"],)
        ).fetchone()

        password = request.form.get("password", "")
        if not check_password_hash(user["password_hash"], password):
            return render_template(
                "account_2fa.html",
                enabled=True,
                qr_code=None,
                secret=None,
                error="Incorrect password",
            ), 401

        database.execute(
            """UPDATE user_2fa
            SET secret_key = NULL, is_enabled = 0, confirmed_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (session["user_id"],),
        )
        database.execute(
            "DELETE FROM user_backup_codes WHERE user_id = ?", (session["user_id"],)
        )
        database.commit()
        return redirect(url_for("account_2fa_page"))

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
