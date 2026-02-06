"""
Old-style migration (timestamp-first filename).
"""


def upgrade(connection):
    connection.execute("CREATE TABLE old_table (id NUMBER, name TEXT)")


def downgrade(connection):
    connection.execute("DROP TABLE old_table")
