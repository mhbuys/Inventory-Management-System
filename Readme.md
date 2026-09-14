# Inventory Management System

An Inventory Management System (IMS) for a hypothetical game store. The current implementation is a Flask server backed by SQLite.

## Quick Start

On Ubuntu Server 24.04 LTS:

```bash
./setup.sh
source .venv/bin/activate
flask --app app run --host (your server IP) --port 5000
```

The server is then available at `http://(your server IP):5000`.

See [install.md](install.md) for complete VM installation and deployment instructions.

## Initial API

- `GET /api/health` checks the Flask and SQLite connection.
- `GET /api/db-status` returns either `connected` or `not connected`.
- `GET /api/products` lists Products, with optional `?category=` filtering.
- `POST /api/products` creates a Product.
- `GET /api/inventory-events` lists Inventory Events.

The SQLite database is created at `instance/inventory.db` after running `flask --app app init-db`.