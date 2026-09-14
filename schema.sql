-- Inventory management database schema.
-- This script resets the database and recreates all tables, indexes, and constraints.

DROP TABLE IF EXISTS event_logs;
DROP TABLE IF EXISTS reorders;
DROP TABLE IF EXISTS inventory_transactions;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS products;

-- Core product catalog. Each item is unique by name and belongs to an allowed category.
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    price REAL NOT NULL DEFAULT 0 CHECK (price >= 0),
    category TEXT NOT NULL CHECK (category IN ('board_game', 'card_game', 'dice', 'miniature')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'discontinued')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Inventory totals and reorder settings for each product.
CREATE TABLE inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL UNIQUE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    low_stock_threshold INTEGER NOT NULL DEFAULT 0 CHECK (low_stock_threshold >= 0),
    reorder_amount INTEGER NOT NULL DEFAULT 0 CHECK (reorder_amount >= 0),
    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
);

-- User accounts used for authentication and activity tracking.
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

-- Role definitions used to group permissions for users.
CREATE TABLE roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE
);

-- Many-to-many relationship between users and roles.
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE
);

-- Record stock changes such as purchases, sales, adjustments, and reorder events.
CREATE TABLE inventory_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER,
    quantity_change INTEGER NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'sale', 'adjustment', 'alert', 'reorder')),
    date_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL
);

-- Purchase orders created for restocking products.
CREATE TABLE reorders (
    reorder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    quantity_ordered INTEGER NOT NULL CHECK (quantity_ordered > 0),
    reorder_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ordered', 'received', 'cancelled')),
    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
);

-- System and user event logging for auditing and debugging.
CREATE TABLE event_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    date_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL
);

-- Helpful indexes for common filters and joins used by the application.
CREATE INDEX idx_products_category ON products (category);
CREATE INDEX idx_products_status ON products (status);
CREATE INDEX idx_inventory_transactions_product_id ON inventory_transactions (product_id);
CREATE INDEX idx_inventory_transactions_user_id ON inventory_transactions (user_id);
CREATE INDEX idx_reorders_product_id ON reorders (product_id);
CREATE INDEX idx_event_logs_user_id ON event_logs (user_id);