# Inventory Management System - Database Design

The Inventory Management System will use a MySQL database to store and manage information for a hypothetical game store

The database will support:

- Product information
- Current inventory quantities
- Low-stock thresholds
- Reorder amounts
- Inventory transaction history
- User accounts
- Permission levels
- Reorder history
- Event logging
- Two-factor authentication

## Proposed Tables

### 1. products

Stores information about each product in the inventory.

| Column | Description |
|---|---|
| product_id | Primary Key |
| name | Product name |
| description | Product description |
| price | Product price |

### 2. inventory

Stores the current inventory information for each product.

| Column | Description |
|---|---|
| inventory_id | Primary Key |
| product_id | Foreign Key referencing products |
| quantity | Current quantity in stock |
| low_stock_threshold | Quantity that triggers a low-stock alert |
| reorder_amount | Amount that should be reordered |

### 3. inventory_transactions

Records changes made to inventory quantities.

| Column | Description |
|---|---|
| transaction_id | Primary Key |
| product_id | Foreign Key referencing products |
| user_id | Foreign Key referencing users |
| quantity_change | Amount added or removed |
| transaction_type | Type of inventory change |
| date_time | Date and time of the transaction |

### 4. users

Stores application user accounts.

| Column | Description |
|---|---|
| user_id | Primary Key |
| username | User login name |
| password_hash | Hashed password |

### 5. roles

Stores user permission levels.

| Column | Description |
|---|---|
| role_id | Primary Key |
| role_name | Name of the permission role |

### 6. user_roles

Link table connecting users to their assigned roles.

| Column | Description |
|---|---|
| user_id | Foreign Key referencing users |
| role_id | Foreign Key referencing roles |

The combination of user_id and role_id will be used as the primary key.

### 7. reorders

Tracks product reorder activity.

| Column | Description |
|---|---|
| reorder_id | Primary Key |
| product_id | Foreign Key referencing products |
| quantity_ordered | Quantity being reordered |
| reorder_date | Date the reorder was created |
| status | Current reorder status |

### 8. event_logs

Records important activity in the system.

| Column | Description |
|---|---|
| log_id | Primary Key |
| user_id | Foreign Key referencing users |
| event_type | Type of event |
| description | Description of the event |
| date_time | Date and time the event occurred |

### 9. user_2fa

Stores two-factor authentication information for user accounts.

| Column | Description |
|---|---|
| user_id | Primary Key and Foreign Key referencing users |
| secret_key | Secret key used to generate authentication codes |
| is_enabled | Indicates whether 2FA is enabled for the user |
| backup_codes | Backup recovery codes for account access |
| updated_at | Date and time the 2FA information was last updated |

## Table Relationships

- `products` links to `inventory` using `product_id`.
- `products` links to `inventory_transactions` using `product_id`.
- `products` links to `reorders` using `product_id`.
- `users` links to `inventory_transactions` using `user_id`.
- `users` links to `event_logs` using `user_id`.
- `users` and `roles` are connected through the `user_roles` link table.
- `users` links to `user_2fa` using `user_id`.
  
## Link Table

The `user_roles` table is a link table between the `users` and `roles` tables.

This allows users to have permission roles without storing duplicate role information.
