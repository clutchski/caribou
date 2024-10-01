"""
a migration with a syntax error
"""

import caribou

import me_no_existy


def upgrade(connection):
    sql = """
        CREATE TABLE games
        ( id    NUMBER
        , name  TEXT
        )"""
    connection.execute(sql)

    sql = """
        CREATE TABLE players
        ( id        NUMBER
        , username  TEXT
        )"""
    connection.execute(sql)


def downgrade(connection):
    for table in ["games", "players"]:
        connection.execute("drop table %s" % table)
