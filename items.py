from database import get_db


def add_item(
    name,
    category,
    description=None,
    price=0,
    quantity=0,
    low_stock_threshold=0,
    reorder_amount=0,
    user_id=None,
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


def update_quantity(product_id, quantity, user_id=None):
    """Set an item's inventory quantity."""
    if quantity < 0:
        raise ValueError("Quantity cannot be negative")

    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    try:
        previous = database.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
        if previous is None:
            raise ValueError(f"No item found with product ID {product_id}")

        database.execute(
            "UPDATE inventory SET quantity = ? WHERE product_id = ?",
            (quantity, product_id),
        )
        queue_low_stock_reorder(
            product_id, user_id, previous_quantity=previous["quantity"]
        )
        database.commit()
    except Exception:
        database.rollback()
        raise


def adjust_quantity(product_id, quantity_change, user_id=None):
    """Add or remove units without allowing stock to become negative."""
    if not isinstance(quantity_change, int) or quantity_change == 0:
        raise ValueError("Quantity change must be a nonzero integer")

    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    try:
        previous = database.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
        if previous is None:
            raise ValueError(f"No item found with product ID {product_id}")

        result = database.execute(
            """
            UPDATE inventory
            SET quantity = quantity + ?
            WHERE product_id = ? AND quantity + ? >= 0
            """,
            (quantity_change, product_id, quantity_change),
        )
        if result.rowcount == 0:
            raise ValueError("Stock cannot be negative")

        queue_low_stock_reorder(
            product_id, user_id, previous_quantity=previous["quantity"]
        )
        database.commit()
    except Exception:
        database.rollback()
        raise


def queue_low_stock_reorder(product_id, user_id=None, previous_quantity=None):
    """Queue only when a quantity decrease crosses into the low-stock range."""
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
    if (
        item is None
        or previous_quantity is None
        or previous_quantity <= item["low_stock_threshold"]
        or item["quantity"] > item["low_stock_threshold"]
        or item["reorder_amount"] <= 0
    ):
        return False

    active_order = database.execute(
        """SELECT 1 FROM reorders
        WHERE product_id = ? AND status IN ('pending', 'ordered')""",
        (product_id,),
    ).fetchone()
    if active_order is not None:
        return False

    result = database.execute(
        """
        INSERT OR IGNORE INTO reorders (product_id, quantity_ordered, status)
        VALUES (?, ?, 'pending')
        """,
        (product_id, item["reorder_amount"]),
    )
    if result.rowcount == 0:
        return False

    database.execute(
        """
        INSERT INTO event_logs (user_id, event_type, description)
        VALUES (?, 'reorder_queued', ?)
        """,
        (
            user_id,
            f"Automatically queued reorder for {item['name']} "
            f"({item['reorder_amount']} units)",
        ),
    )
    return True
