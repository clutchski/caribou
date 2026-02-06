"""
Example: directory-based migrations (the traditional approach).

Run from the repo root:
    python examples/directory_migrations.py
"""

import os
import sqlite3
import caribou

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "example.db")
MIGRATIONS = os.path.join(HERE, "migrations")


def show(label):
    conn = sqlite3.connect(DB)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'migration_version'"
    ).fetchall()
    version = caribou.get_version(DB)
    print(f"  {label}: version={version} tables={[t[0] for t in tables]}")
    conn.close()


def main():
    # clean slate
    if os.path.exists(DB):
        os.remove(DB)

    print("Directory-based migrations")
    print()

    caribou.upgrade(DB, MIGRATIONS)
    show("after upgrade")

    caribou.downgrade(DB, MIGRATIONS, "0")
    show("after downgrade")

    os.remove(DB)


if __name__ == "__main__":
    main()
