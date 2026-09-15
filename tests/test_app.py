from app import create_app
from database import get_db, init_db
from items import add_item, remove_item


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
