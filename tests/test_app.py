import pyotp

from app import create_app
from database import get_db, init_db, query_db
from items import add_item, adjust_quantity, remove_item, update_quantity


# Log in as the seeded admin and clear the forced password-change flag it starts with.
def login_as_admin(client):
    client.post("/login", data={"username": "admin", "password": "admin"})
    client.post(
        "/account/change-password",
        data={"new_password": "new-password123", "confirm_password": "new-password123"},
    )


# Verify that the app can build the SQLite schema into a temporary database file.
def test_app_initializes_database(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        database = get_db()
        tables = database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

    # These are the core tables required for the inventory system.
    assert "products" in {row[0] for row in tables}
    assert "inventory" in {row[0] for row in tables}
    assert "user_2fa" in {row[0] for row in tables}


def test_query_db_returns_matching_rows(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        database = get_db()
        database.execute(
            "INSERT INTO products (name, category) VALUES (?, ?)",
            ("Catan", "board_game"),
        )
        database.commit()
        rows = query_db(
            "SELECT name FROM products WHERE category = ?",
            ("board_game",),
        )

    assert [row["name"] for row in rows] == ["Catan"]


def test_add_item_creates_product_and_inventory(tmp_path):
    # Adding an item should create both its catalog and inventory records.
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        product_id = add_item(
            "Catan",
            "board_game",
            price=34.99,
            quantity=5,
            low_stock_threshold=2,
            reorder_amount=10,
        )
        item = (
            get_db()
            .execute(
                """
            SELECT products.name, products.price, inventory.quantity
            FROM products
            JOIN inventory ON inventory.product_id = products.product_id
            WHERE products.product_id = ?
            """,
                (product_id,),
            )
            .fetchone()
        )

    assert tuple(item) == ("Catan", 34.99, 5)


def test_remove_item_deletes_product_and_inventory(tmp_path):
    # Removing an item should also remove its related inventory record.
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game")
        remove_item(product_id)
        database = get_db()
        product = database.execute(
            "SELECT 1 FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        inventory = database.execute(
            "SELECT 1 FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()

    assert product is None
    assert inventory is None


def test_update_quantity_changes_inventory_quantity(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=5)
        update_quantity(product_id, 12)
        quantity = (
            get_db()
            .execute(
                "SELECT quantity FROM inventory WHERE product_id = ?",
                (product_id,),
            )
            .fetchone()[0]
        )

    assert quantity == 12


def test_update_quantity_rejects_negative_quantity(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=5)

        try:
            update_quantity(product_id, -1)
        except ValueError as error:
            assert str(error) == "Quantity cannot be negative"
        else:
            raise AssertionError("Expected negative quantity to be rejected")


def test_adjust_quantity_adds_and_removes_one_unit(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=15)
        adjust_quantity(product_id, 1)
        adjust_quantity(product_id, -1)
        quantity = (
            get_db()
            .execute(
                "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
            )
            .fetchone()[0]
        )

    assert quantity == 15


def test_adjust_quantity_rejects_removing_below_zero(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=0)

        try:
            adjust_quantity(product_id, -1)
        except ValueError as error:
            assert str(error) == "Stock cannot be negative"
        else:
            raise AssertionError("Expected stock below zero to be rejected")


# Auth tests confirm that protected pages redirect and the default admin account works.
def test_login_requires_authentication(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_login_page_is_reachable_without_authentication(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    response = app.test_client().get("/login", follow_redirects=False)

    assert response.status_code == 200
    assert b"Please log in" in response.data


# This verifies the seeded admin login succeeds for the browser and protected routes.
def test_default_admin_user_can_login(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/account/2fa"


def test_homepage_displays_database_inventory(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        add_item("Catan", "board_game", price=34.99, quantity=5)

    client = app.test_client()
    login_as_admin(client)
    response = client.get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Catan" in page
    assert "5 units available" in page
    assert "1 items tracked" in page
    assert 'id="quantity-input"' in page
    assert ">Done</button>" in page
    assert 'data-current-quantity="5"' in page
    assert "Sample item" not in page


def test_inventory_disables_removal_when_stock_is_zero(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        add_item("Catan", "board_game", quantity=0)

    client = app.test_client()
    login_as_admin(client)
    page = client.get("/").get_data(as_text=True)

    assert 'aria-label="Remove units from Catan"' in page
    assert 'aria-label="Remove units from Catan" title="Remove units" disabled' in page


def test_inventory_page_adjusts_stock_by_one_unit(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=15)

    client = app.test_client()
    login_as_admin(client)

    response = client.post(
        "/adjust-stock",
        data={"product_id": product_id, "quantity_change": 1},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with app.app_context():
        assert (
            get_db()
            .execute(
                "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
            )
            .fetchone()[0]
            == 16
        )


def test_inventory_page_adjusts_stock_by_requested_amount(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=15)

    client = app.test_client()
    login_as_admin(client)

    add_response = client.post(
        "/adjust-stock",
        data={"product_id": product_id, "quantity_change": 15},
    )
    remove_response = client.post(
        "/adjust-stock",
        data={"product_id": product_id, "quantity_change": -5},
    )

    assert add_response.status_code == 302
    assert remove_response.status_code == 302
    with app.app_context():
        assert (
            get_db()
            .execute(
                "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
            )
            .fetchone()[0]
            == 25
        )


def test_inventory_low_stock_alert_opens_reorder_form_and_queues_automatic_order(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item(
            "Catan",
            "board_game",
            quantity=1,
            low_stock_threshold=2,
            reorder_amount=10,
        )

    client = app.test_client()
    login_as_admin(client)
    inventory_page = client.get("/")
    page = client.get(f"/reorders?product_id={product_id}")

    assert b'LOW STOCK: 1 units' in inventory_page.data
    assert f"/reorders?product_id={product_id}".encode() in inventory_page.data
    assert page.status_code == 200
    assert b"Catan" in page.data
    assert b"Use automatic reorder amount" in page.data

    response = client.post(
        "/reorders",
        data={
            "product_id": product_id,
            "automatic_amount": "1",
            "automatic_reorder_amount": "10",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/reorders"
    with app.app_context():
        order = get_db().execute(
            """
            SELECT product_id, quantity_ordered, status
            FROM reorders
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()

    assert tuple(order) == (product_id, 10, "pending")


def test_reorder_page_prevents_duplicate_active_orders(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item(
            "Catan",
            "board_game",
            quantity=0,
            low_stock_threshold=2,
            reorder_amount=10,
        )

    client = app.test_client()
    login_as_admin(client)
    assert client.post(
        "/reorders",
        data={"product_id": product_id, "quantity_ordered": "7"},
    ).status_code == 302
    duplicate = client.post(
        "/reorders",
        data={"product_id": product_id, "quantity_ordered": "7"},
    )

    assert duplicate.status_code == 409
    assert b"active reorder already exists" in duplicate.data


def test_reorder_page_accepts_custom_order_amount(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item(
            "Catan",
            "board_game",
            quantity=0,
            low_stock_threshold=2,
            reorder_amount=10,
        )

    client = app.test_client()
    login_as_admin(client)
    response = client.post(
        "/reorders",
        data={"product_id": product_id, "quantity_ordered": "7"},
    )

    assert response.status_code == 302
    with app.app_context():
        quantity_ordered = get_db().execute(
            "SELECT quantity_ordered FROM reorders WHERE product_id = ?",
            (product_id,),
        ).fetchone()[0]

    assert quantity_ordered == 7


def test_queued_order_can_be_cancelled(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item(
            "Catan",
            "board_game",
            quantity=0,
            low_stock_threshold=2,
            reorder_amount=10,
        )

    client = app.test_client()
    login_as_admin(client)
    client.post(
        "/reorders",
        data={"product_id": product_id, "quantity_ordered": "7"},
    )
    with app.app_context():
        reorder_id = get_db().execute(
            "SELECT reorder_id FROM reorders WHERE product_id = ?",
            (product_id,),
        ).fetchone()[0]

    response = client.post(f"/reorders/{reorder_id}/cancel")

    assert response.status_code == 302
    assert response.headers["Location"] == "/reorders"
    with app.app_context():
        status = get_db().execute(
            "SELECT status FROM reorders WHERE reorder_id = ?",
            (reorder_id,),
        ).fetchone()[0]

    assert status == "cancelled"


def test_cancel_missing_or_completed_order_returns_not_found(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    login_as_admin(client)

    response = client.post("/reorders/999/cancel")

    assert response.status_code == 404
    assert b"Queued order not found" in response.data


def test_add_item_page_does_not_show_automatic_reorder_amount(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    login_as_admin(client)
    page = client.get("/add-item")

    assert page.status_code == 200
    assert b'name="reorder_amount"' not in page.data


# Verify that the add-item page is protected but reachable after login.
def test_add_item_page_requires_authentication(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    response = client.get("/add-item", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

    login_as_admin(client)
    response = client.get("/add-item")

    assert response.status_code == 200
    assert b"Add Item" in response.data


# Verify that the browser can remove a selected database item through the route.
def test_remove_item_page_deletes_selected_inventory_item(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        product_id = add_item("Catan", "board_game", quantity=5)

    client = app.test_client()
    login_as_admin(client)

    page = client.get("/remove-item")
    assert page.status_code == 200
    assert b"Catan" in page.data

    response = client.post("/remove-item", data={"product_id": product_id})

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with app.app_context():
        assert (
            get_db()
            .execute("SELECT 1 FROM products WHERE product_id = ?", (product_id,))
            .fetchone()
            is None
        )


# Invalid form values should return a client error instead of reaching the database.
def test_remove_item_rejects_invalid_product_id(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    login_as_admin(client)

    response = client.post("/remove-item", data={"product_id": "not-a-number"})

    assert response.status_code == 400
    assert b"Invalid inventory item" in response.data


# Logging out should remove access to protected pages from the current client.
def test_logout_clears_authentication_session(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    login_as_admin(client)
    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert client.get("/", follow_redirects=False).headers["Location"] == "/login"


# Verify 2FA enrollment, require a TOTP at login, and block pending sessions. - NL
def test_two_factor_enrollment_and_totp_login(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    login_as_admin(client)

    setup_response = client.get("/account/2fa")
    assert setup_response.status_code == 200
    with app.app_context():
        settings = (
            get_db()
            .execute(
                """SELECT user_2fa.secret_key, user_2fa.is_enabled
            FROM user_2fa JOIN users ON users.user_id = user_2fa.user_id
            WHERE users.username = ?""",
                ("admin",),
            )
            .fetchone()
        )
    secret_key = settings["secret_key"]
    assert settings["secret_key"]
    assert settings["is_enabled"] == 0

    enable_response = client.post(
        "/account/2fa/enable",
        data={"code": pyotp.TOTP(settings["secret_key"]).now()},
    )
    assert enable_response.status_code == 200
    with app.app_context():
        settings = (
            get_db()
            .execute(
                """SELECT is_enabled, confirmed_at, updated_at
            FROM user_2fa JOIN users ON users.user_id = user_2fa.user_id
            WHERE users.username = ?""",
                ("admin",),
            )
            .fetchone()
        )
        backup_code_count = (
            get_db()
            .execute(
                """SELECT COUNT(*) FROM user_backup_codes
            JOIN users ON users.user_id = user_backup_codes.user_id
            WHERE users.username = ?""",
                ("admin",),
            )
            .fetchone()[0]
        )
    assert settings["is_enabled"] == 1
    assert settings["confirmed_at"]
    assert settings["updated_at"]
    assert backup_code_count > 0

    client.get("/logout")
    login_response = client.post(
        "/login", data={"username": "admin", "password": "new-password123"}
    )
    assert login_response.headers["Location"] == "/login/2fa"
    for protected_path in ("/", "/add-item", "/remove-item", "/account/2fa"):
        protected_response = client.get(protected_path, follow_redirects=False)
        assert protected_response.status_code == 302
        assert protected_response.headers["Location"] == "/login/2fa"

    mutation_response = client.post(
        "/adjust-stock",
        data={"product_id": 1, "quantity_change": 1},
        follow_redirects=False,
    )
    assert mutation_response.status_code == 302
    assert mutation_response.headers["Location"] == "/login/2fa"

    verify_response = client.post(
        "/login/2fa", data={"code": pyotp.TOTP(secret_key).now()}
    )
    assert verify_response.headers["Location"] == "/"
    assert client.get("/").status_code == 200


# Verify users without enabled 2FA are sent to setup after password login. - NL
def test_login_redirects_to_two_factor_setup_when_not_enabled(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()

    client = app.test_client()
    first_login = client.post("/login", data={"username": "admin", "password": "admin"})
    assert first_login.headers["Location"] == "/account/2fa"

    password_page = client.get("/account/2fa", follow_redirects=False)
    assert password_page.status_code == 302
    assert password_page.headers["Location"] == "/account/change-password"

    password_response = client.post(
        "/account/change-password",
        data={"new_password": "new-password123", "confirm_password": "new-password123"},
    )
    assert password_response.headers["Location"] == "/account/2fa"
    assert client.get("/account/2fa").status_code == 200

    client.get("/logout")
    subsequent_login = client.post(
        "/login", data={"username": "admin", "password": "new-password123"}
    )
    assert subsequent_login.headers["Location"] == "/account/2fa"
    assert client.get("/account/2fa").status_code == 200
