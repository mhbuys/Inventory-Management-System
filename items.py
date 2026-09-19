from database import get_db


def add_item(
    name,
    category,
    description=None,
    price=0,
    quantity=0,
    low_stock_threshold=0,
    reorder_amount=0,
):
    """Add a product and its inventory record, returning the product ID."""
    database = get_db()
    try:
        # Store catalog details first so the inventory row can reference the new ID.
        product = database.execute(
            """
            INSERT INTO products (name, description, price, category)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, price, category),
        )
        product_id = product.lastrowid
        database.execute(
            """
            INSERT INTO inventory (
                product_id, quantity, low_stock_threshold, reorder_amount
            )
            VALUES (?, ?, ?, ?)
            """,
            (product_id, quantity, low_stock_threshold, reorder_amount),
        )
        # Keep the product and inventory records in the same transaction.
        database.commit()
    except Exception:
        database.rollback()
        raise

    return product_id


def remove_item(product_id):
    """Remove a product and its related inventory records."""
    database = get_db()
    # The schema's foreign-key cascade removes related inventory records.
    result = database.execute(
        "DELETE FROM products WHERE product_id = ?",
        (product_id,),
    )
    if result.rowcount == 0:
        raise ValueError(f"No item found with product ID {product_id}")

    database.commit()


def update_quantity(product_id, quantity):
    """Set an item's inventory quantity."""
    if quantity < 0:
        raise ValueError("Quantity cannot be negative")

    database = get_db()
    result = database.execute(
        "UPDATE inventory SET quantity = ? WHERE product_id = ?",
        (quantity, product_id),
    )
    if result.rowcount == 0:
        raise ValueError(f"No item found with product ID {product_id}")

    database.commit()
