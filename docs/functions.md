# Inventory Management System Functions

This document describes the current item-management functions and where readers can find their implementation.

## `query_db`

- **Location:** `database.py` (`query_db`)
- **Purpose:** Executes a parameterized read query and returns all matching rows.
- **Parameters:**
  - `query`: SQL query string using `?` placeholders for values.
  - `parameters`: Values bound to the query placeholders. Defaults to an empty tuple.
- **Returns:** A list of `sqlite3.Row` objects.
- **Database behavior:** Uses the current Flask application's database connection.

## `add_item`

- **Location:** `items.py`, line 4 (`add_item`)
- **Date added:** 2026-09-14
- **Purpose:** Adds a new product to the `products` table and creates its matching inventory record in the `inventory` table.
- **Parameters:**
  - `name`: Product name.
  - `category`: Product category, such as `board_game`, `card_game`, `dice`, or `miniature`.
  - `description`: Optional product description.
  - `price`: Product price. Defaults to `0`.
  - `quantity`: Starting inventory quantity. Defaults to `0`.
  - `low_stock_threshold`: Quantity at which the item is considered low in stock. Defaults to `0`.
  - `reorder_amount`: Quantity to order when restocking. Defaults to `0`.
- **Returns:** The new product ID.
- **Database behavior:** The product and inventory records are committed together. If either insert fails, the transaction is rolled back.

## `remove_item`

- **Location:** `items.py`, line 42 (`remove_item`)
- **Date added:** 2026-09-14
- **Purpose:** Removes a product from the `products` table using its product ID.
- **Parameters:**
  - `product_id`: ID of the product to remove.
- **Returns:** Nothing after a successful deletion.
- **Database behavior:** The database schema's foreign-key cascade also removes the product's related inventory record.
- **Errors:** Raises `ValueError` when no product exists with the supplied ID.

## `update_quantity`

- **Location:** `items.py` (`update_quantity`)
- **Purpose:** Replaces an item's current inventory quantity using its product ID.
- **Parameters:**
  - `product_id`: ID of the product to update.
  - `quantity`: New nonnegative inventory quantity.
- **Returns:** Nothing after a successful update.
- **Database behavior:** The updated inventory record is committed immediately.
- **Errors:** Raises `ValueError` for a missing product or negative quantity.

## How To Find The Functions

1. Open `items.py` in the project root.
2. Use your code editor's search feature to locate the function by name (e.g., `add_item` or `remove_item`).
