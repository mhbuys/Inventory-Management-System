#!/usr/bin/env python3
import argparse
import random
import sys
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Add test inventory to an existing IMS database."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=750,
        help="Number of items to add (500-1000; default: 750).",
    )
    args = parser.parse_args()

    if not 500 <= args.count <= 1000:
        parser.error("--count must be between 500 and 1000")

    project_dir = Path.cwd()
    if not all(
        (project_dir / name).is_file() for name in ("app.py", "items.py", "database.py")
    ):
        parser.error(
            "Run this script from the IMS project directory "
            "with its virtual environment active."
        )
    sys.path.insert(0, str(project_dir))

    from flask.cli import load_dotenv

    load_dotenv()
    from app import app
    from items import add_item, add_supplier

    database_path = Path(app.config["DATABASE"]).resolve()
    if not database_path.is_file():
        parser.error(
            f"Database not found: {database_path}. Initialize a new database first."
        )

    run_id = uuid.uuid4().hex
    supplier_name = f"Load Test Supplier {run_id}"
    categories = ("board_game", "card_game", "dice", "miniature")

    print(f"Adding {args.count} items to {database_path}", flush=True)

    with app.app_context():
        supplier_id = add_supplier(supplier_name, "load-test@example.com", "555-0100")
        print(f"Created supplier: {supplier_name} (ID {supplier_id})", flush=True)

        for index in range(1, args.count + 1):
            add_item(
                name=f"Load Test {run_id} Item {index:04d}",
                category=random.choice(categories),
                description="Generated test inventory",
                price=random.randint(100, 10000) / 100,
                quantity=random.randint(1, 50),
                low_stock_threshold=random.randint(1, 50),
                reorder_amount=random.randint(1, 50),
                supplier_id=supplier_id,
            )

            if index % 100 == 0 or index == args.count:
                print(f"Added {index}/{args.count} items", flush=True)

    print("Done. Existing inventory was not removed.")


if __name__ == "__main__":
    main()
