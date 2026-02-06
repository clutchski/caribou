"""
New-style migration (v-prefix filename).
"""


def upgrade(connection):
    connection.execute(
        "CREATE TABLE new_table (id NUMBER, name TEXT)"
    )


def downgrade(connection):
    connection.execute("DROP TABLE new_table")
