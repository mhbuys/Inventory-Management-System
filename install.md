# Inventory Management System Installation

This document describes how to install and run the Inventory Management System (IMS) Flask server with Python and SQLite.

## Recommended Server

The recommended server operating system is **Ubuntu Server 24.04 LTS**.

Minimum development or VM requirements:

- 1 CPU core
- 1 GB RAM
- 10 GB available disk space
- SSH access for remote administration

SQLite does not require a separate database server. The database is stored as a local file managed by the Flask application.

## Required Software

The server requires:

- Python 3.12 or newer
- Python virtual environment support
- Git
- Flask
- SQLite 3

The Python `sqlite3` module provides the Python-to-SQL interface used by the application. A separate SQLite service is not required.

## Ubuntu Installation

Update the operating system packages:

```bash
sudo apt update
sudo apt upgrade -y
```

Install Python, the virtual environment package, Git, and SQLite:

```bash
sudo apt install -y python3 python3-venv python3-pip git sqlite3
```

Verify the installation:

```bash
python3 --version
sqlite3 --version
```

## Download the Project

Clone the project and enter its directory:

```bash
git clone <repository-url>
cd Inventory-Management-System
```

Replace `<repository-url>` with the team's GitHub repository URL.

## Create the Python Environment

Create a project-local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The virtual environment should be activated whenever the server is run manually.

## Initialize SQLite

Create the application data directory and initialize the database:

```bash
mkdir -p instance
flask --app app init-db
```

The SQLite database will be stored at:

```text
instance/inventory.db
```

The database will contain the IMS data needed for Products and Inventory Events. Product records will support the documented fields: product ID, product name, category, quantity in stock, reorder threshold, reorder quantity, and product status.

## Run the Development Server

Start Flask so it can be reached from the VM network:

```bash
flask --app app run --host 0.0.0.0 --port 5000
```

Open the server from another computer using:

```text
http://<server-ip>:5000
```

For local-only testing, use `127.0.0.1` instead of `0.0.0.0`.

## Open the Firewall Port

If Ubuntu's firewall is enabled, allow Flask's development port for testing:

```bash
sudo ufw allow 5000/tcp
sudo ufw status
```

The production deployment should use HTTPS through Nginx rather than exposing Flask's development server directly.

## Production Direction

The development server is suitable for local development and initial VM testing. For production, the planned deployment is:

1. Flask application
2. Gunicorn application server
3. Nginx reverse proxy
4. HTTPS certificate
5. A systemd service to start the IMS automatically

Those services will be added after the initial Flask and SQLite application is working.

## Windows Development

The server can also be developed on Windows with Python 3.12 or newer:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
flask --app app init-db
flask --app app run
```

Ubuntu Server remains the recommended VM operating system because the deployment commands and future Gunicorn, Nginx, and systemd setup are simpler there.

## Current Database Decision

The original requirements document references MySQL, but the current implementation direction is SQLite. SQLite is appropriate for the initial single-server IMS because it is simple to install, requires no separate service, and keeps the database in the project instance directory.

The database access layer should remain isolated behind Python functions so the IMS can migrate to MySQL later without changing the Flask routes or inventory rules.