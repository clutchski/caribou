"""
a third migration
"""


def upgrade(connection):
    sql = """
        create table jams
        ( id NUMBER
        , name TEXT
        )"""
    connection.execute(sql)


def downgrade(connection):
    connection.execute("drop table jams")
