"""
initial migration
"""

import caribou


def upgrade(connection):
    sql = """
        CREATE TABLE scores
        ( id    NUMBER
        , value  NUMBER
        )"""
    connection.execute(sql)


def downgrade(connection):
    connection.execute("drop table scores")
