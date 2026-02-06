"""
Example: module-based migrations.

This approach works inside PyInstaller bundles and other environments
where filesystem discovery is not available -- you just import the
migration modules directly and pass them as a list.

Run from the repo root:
    python examples/module_migrations.py
"""

import os
import sys
import sqlite3
import caribou

# Add examples/ to the path so "from migrations import ..." works
# regardless of where you run this script from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the migration modules directly. In a real app these would
# be regular package imports (from myapp.migrations import ...).
from migrations import v20260206024658_create_users, v20260206024701_create_scores

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "example.db")
MODULES = [v20260206024658_create_users, v20260206024701_create_scores]


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

    caribou.upgrade(DB, MODULES)
    show("after upgrade")

    caribou.downgrade(DB, MODULES, "0")
    show("after downgrade")

    os.remove(DB)


if __name__ == "__main__":
    main()
