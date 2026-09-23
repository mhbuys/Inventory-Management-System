from app import create_app
from database import get_db, init_db, query_db
from items import add_item, remove_item, update_quantity


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
    assert response.headers["Location"] == "/"


def test_homepage_displays_database_inventory(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": str(database_path)}
    )

    with app.app_context():
        init_db()
        add_item("Catan", "board_game", price=34.99, quantity=5)

    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin"})
    response = client.get("/")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Catan" in page
    assert "5 units available" in page
    assert "1 items tracked" in page
    assert "Sample item" not in page
