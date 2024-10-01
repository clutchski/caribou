import contextlib
import glob
import os
import shutil
import sqlite3
import pytest

import caribou

TEST_DB = "test.sqlite3"
MIGRATIONS_DIR = "migrations"
INVALID_MIGRATIONS = "invalid_migrations"
INVALID_CODE = os.path.join(INVALID_MIGRATIONS, "code")
INVALID_NAMES = os.path.join(INVALID_MIGRATIONS, "names")


def get_this_dir():
    return os.path.abspath(os.path.dirname(__file__))


def get_migrations_path():
    return os.path.join(get_this_dir(), MIGRATIONS_DIR)


def test_transaction_context_manager():
    """Assert the transaction context manager commits properly."""

    with contextlib.closing(sqlite3.connect(":memory:")) as conn:

        conn.execute("create table animals ( name TEXT)")

        def _count():
            return conn.execute("select count(*) from animals").fetchone()[0]

        # assert that once a transaction is commited, its locked in
        assert _count() == 0
        with caribou.transaction(conn):
            conn.execute("insert into animals values ('bear')")
        assert _count() == 1
        conn.rollback()
        assert _count() == 1
        # assert it will rollback transactions with errors
        try:
            with caribou.transaction(conn):
                conn.execute("insert into animals values ('wolf')")
                raise Exception()
        except Exception:
            pass
        else:
            assert 0  # should fail
        assert _count() == 1


@pytest.fixture
def sqlite_test_path():
    this_dir = get_this_dir()
    db_path = os.path.join(this_dir, TEST_DB)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def _table_exists(conn, table_name):
    sql = """
        SELECT *
          FROM sqlite_master
         WHERE type = 'table'
           AND name = :1
           """
    with caribou.execute(conn, sql, [table_name]) as cursor:
        return bool(cursor.fetchall())


def test_invalid_migration_filenames():
    """
    assert we can't load migrations with invalid version names
    """
    # assert we test invalid version names
    invalid_names = os.path.join(get_this_dir(), INVALID_NAMES, "*.py")
    for filename in glob.glob(invalid_names):
        try:
            migration = caribou.Migration(filename)
            migration.get_version()
        except caribou.InvalidNameError:
            pass
        else:
            assert False, filename


def test_valid_migration_filenames():
    """assert we can parse the versions from migration files"""
    # test some valid versions
    migrations_path = get_migrations_path()
    for version, suffix in [
        ("20091112130101", "__migration_one.py"),
        ("20091112150200", "__migration_two.py"),
        ("20091112150205", "_migration_three.py"),
    ]:
        path = os.path.join(migrations_path, version + suffix)
        migration = caribou.Migration(path)
        actual_version = migration.get_version()
        assert actual_version == version


def test_invalid_migraton_code(sqlite_test_path):
    filenames = [
        "20091112130101_syntax_error.py",
        "20091112150200_missing_upgrade.py",
        "20091112150205_missing_downgrade.py",
    ]
    code_dir = os.path.join(get_this_dir(), INVALID_CODE)
    # assert we can't load a directory containing invalid migrations
    try:
        caribou.load_migrations(code_dir)
    except caribou.InvalidMigrationError:
        pass
    else:
        assert False, "loaded a dir with invalid migrations"
    # assert we can't load each invalid migration
    migrations = [os.path.join(code_dir, f) for f in filenames]
    for migration in migrations:
        try:
            caribou.Migration(migration)
        except caribou.InvalidMigrationError:
            pass
        else:
            assert False, "loaded invalid migration [%s]" % migration


def test_unknown_migration(sqlite_test_path):
    """assert we can't target an unknown migration or non existant dirs"""
    db_url = sqlite_test_path
    migrations_path = get_migrations_path()
    for v in ["asdf", "22341", "asdfasdfasdf", "----"]:
        for func in [caribou.upgrade, caribou.downgrade]:
            try:
                func(db_url, migrations_path, v)
            except caribou.Error:
                pass
            else:
                assert False, "ran an unknown migration: %s" % v
    # assert we can't run non-existant migrations
    path = "/path/to/nowhereski/whoop"
    for func, args in [
        (caribou.upgrade, (db_url, path, None)),
        (caribou.downgrade, (db_url, path, 0)),
    ]:
        try:
            func(*args)
        except caribou.Error:
            pass
        else:
            assert False, "%s %s" % (func, str(args))


def test_migration(sqlite_test_path):
    # assert migrations haven't been run
    migrations_path = get_migrations_path()
    db_url = sqlite_test_path

    conn = sqlite3.connect(db_url)
    assert not _table_exists(conn, "games")
    assert not _table_exists(conn, "players")
    assert caribou.get_version(db_url) is None

    # assert that the first migration has been run successfully
    # and that subsequent runs have no effect

    v1 = "20091112130101"
    v2 = "20091112150200"
    v3 = "20091112150205"

    for _ in range(3):
        caribou.upgrade(db_url, migrations_path, v1)
        assert _table_exists(conn, "games")
        assert _table_exists(conn, "players")
        actual_version = caribou.get_version(db_url)
        assert actual_version == v1, "%s != %s" % (actual_version, v1)
        # make sure none of the other migrations run
        assert not _table_exists(conn, "scores")

    # run the 2nd migration
    for _ in range(3):
        caribou.upgrade(db_url, migrations_path, v2)
        tables = ["games", "players", "scores"]
        assert all((_table_exists(conn, t) for t in tables))
        actual_version = caribou.get_version(db_url)
        assert actual_version == v2, "%s != %s" % (actual_version, v2)

    # downgrade the second migration
    for _ in range(3):
        caribou.downgrade(db_url, migrations_path, v1)
        assert _table_exists(conn, "games")
        assert _table_exists(conn, "players")
        actual_version = caribou.get_version(db_url)
        assert actual_version == v1, "%s != %s" % (actual_version, v1)
        # make sure none of the other migrations run
        assert not _table_exists(conn, "scores")

    # upgrade all the way
    for _ in range(3):
        caribou.upgrade(db_url, migrations_path)
        tables = ["games", "players", "scores", "jams"]
        assert all((_table_exists(conn, t) for t in tables))
        actual_version = caribou.get_version(db_url)
        assert actual_version == v3, "%s != %s" % (actual_version, v3)

    # downgrade all the way
    for _ in range(3):
        caribou.downgrade(db_url, migrations_path, "0")
        tables = ["games", "players", "scores", "jams"]
        assert all((not _table_exists(conn, t) for t in tables))
        actual_version = caribou.get_version(db_url)
        assert actual_version == "0"

    # upgrade all the way again
    for _ in range(3):
        caribou.upgrade(db_url, migrations_path)
        tables = ["games", "players", "scores", "jams"]
        assert all((_table_exists(conn, t) for t in tables))
        actual_version = caribou.get_version(db_url)
        assert actual_version == v3, "%s != %s" % (actual_version, v3)


def test_create_migration():
    """assert we can create migration templates"""
    for name, directory in [("tc_1", None), ("tc_2", "test_create__")]:
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        path = caribou.create_migration(name, directory)
        try:
            assert os.path.exists(path)
        finally:
            # remove compiled test migration as well
            for path in [path, path + "c"]:
                if os.path.exists(path):
                    os.remove(path)
            if directory and os.path.exists(directory):
                shutil.rmtree(directory)
    # assert we can't create migrations in a directoin that doesn't exist
    try:
        caribou.create_migration("adsf", "/path/to/nowhereski")
    except caribou.Error:
        pass
    else:
        assert False
