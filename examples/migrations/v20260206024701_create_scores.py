"""
This module contains a Caribou migration.

Migration Name: create_scores
Migration Version: v20260206024701
"""

def upgrade(connection):
    connection.execute("""
        CREATE TABLE scores
        ( id       INTEGER PRIMARY KEY
        , user_id  INTEGER NOT NULL REFERENCES users(id)
        , value    INTEGER NOT NULL
        )
    """)

def downgrade(connection):
    connection.execute("DROP TABLE scores")
