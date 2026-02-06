"""
Example: module-based migrations.

This approach works inside PyInstaller bundles and other environments
where filesystem discovery is not available -- you just import the
migration modules directly and pass them as a list.

Run from the repo root:
    python -m examples.migrate_modules
"""

import os
import sqlite3
import caribou

from examples.migrations import (
    v20260206024658_create_users,
    v20260206024701_create_scores,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "example.db")

MODULES = [
    v20260206024658_create_users,
    v20260206024701_create_scores,
]

V1 = "20260206024658"
V2 = "20260206024701"


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

    print("Module-based migrations")
    print()

    caribou.upgrade(DB, MODULES, V1)
    show("after upgrade to v1")

    caribou.upgrade(DB, MODULES, V2)
    show("after upgrade to v2")

    caribou.downgrade(DB, MODULES, V1)
    show("after downgrade to v1")

    caribou.downgrade(DB, MODULES, "0")
    show("after downgrade to v0")

    os.remove(DB)


if __name__ == "__main__":
    main()
