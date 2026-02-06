"""
This module contains a Caribou migration.

Migration Name: create_users
Migration Version: v20260206024658
"""

def upgrade(connection):
    connection.execute("""
        CREATE TABLE users
        ( id        INTEGER PRIMARY KEY
        , username  TEXT NOT NULL
        , email     TEXT NOT NULL
        )
    """)

def downgrade(connection):
    connection.execute("DROP TABLE users")
