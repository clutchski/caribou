import contextlib
import glob
import os
import pathlib
import shutil
import sqlite3
import types
import pytest

import caribou
from caribou.migrate import _parse_migration_name

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
           AND name = ?
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


def get_mixed_migrations_path():
    return os.path.join(get_this_dir(), "mixed_migrations")


def test_v_prefix_migration_filenames():
    """assert v-prefix files parse version and name correctly"""
    mixed = get_mixed_migrations_path()
    # old-style still works
    path = os.path.join(mixed, "20091112130101__old_style.py")
    m = caribou.Migration(path)
    assert m.get_version() == "20091112130101"
    assert m.name == "old_style"
    # v-prefix works
    path = os.path.join(mixed, "v20091112150200_new_style.py")
    m = caribou.Migration(path)
    assert m.get_version() == "20091112150200"
    assert m.name == "new_style"


def test_mixed_directory(sqlite_test_path):
    """assert a directory with both old-style and v-prefix migrations works"""
    db_url = sqlite_test_path
    mixed = get_mixed_migrations_path()

    caribou.upgrade(db_url, mixed)

    conn = sqlite3.connect(db_url)
    assert _table_exists(conn, "old_table")
    assert _table_exists(conn, "new_table")

    # version should be the latest migration
    assert caribou.get_version(db_url) == "20091112150200"

    # downgrade all the way
    caribou.downgrade(db_url, mixed, "0")
    assert not _table_exists(conn, "old_table")
    assert not _table_exists(conn, "new_table")
    assert caribou.get_version(db_url) == "0"
    conn.close()


def test_upgrade_with_pathlib_path(sqlite_test_path):
    """assert upgrade works when migration dir is a pathlib.Path"""
    db_url = sqlite_test_path
    mixed = pathlib.Path(get_mixed_migrations_path())

    caribou.upgrade(db_url, mixed)

    conn = sqlite3.connect(db_url)
    assert _table_exists(conn, "old_table")
    assert _table_exists(conn, "new_table")
    conn.close()


def _make_migration_module(name, upgrade_fn=None, downgrade_fn=None):
    mod = types.ModuleType(name)
    if upgrade_fn is not None:
        mod.upgrade = upgrade_fn
    if downgrade_fn is not None:
        mod.downgrade = downgrade_fn
    return mod


def _noop(conn):
    pass


def test_migration_from_module():
    """assert Migration.from_module works with v-prefix module name"""
    mod = _make_migration_module("v20240101120000_create_users", _noop, _noop)
    m = caribou.Migration.from_module(mod)
    assert m.get_version() == "20240101120000"
    assert m.name == "create_users"
    assert m.module is mod


def test_migration_from_module_dotted_name():
    """assert from_module works with dotted module names (e.g. pkg.v2024_name)"""
    mod = _make_migration_module(
        "myapp.migrations.v20240101120000_create_users", _noop, _noop
    )
    m = caribou.Migration.from_module(mod)
    assert m.get_version() == "20240101120000"
    assert m.name == "create_users"


def test_migration_from_module_with_version_attr():
    """assert from_module falls back to module.VERSION"""
    mod = _make_migration_module("create_users", _noop, _noop)
    mod.VERSION = "20240101120000"
    m = caribou.Migration.from_module(mod)
    assert m.get_version() == "20240101120000"
    assert m.name == "create_users"


def test_migration_from_module_missing_version():
    """assert from_module raises InvalidMigrationError when no version"""
    mod = _make_migration_module("no_version_here", _noop, _noop)
    with pytest.raises(caribou.InvalidMigrationError):
        caribou.Migration.from_module(mod)


def test_migration_from_module_missing_methods():
    """assert from_module raises InvalidMigrationError for missing methods"""
    mod = _make_migration_module("v20240101120000_bad")
    with pytest.raises(caribou.InvalidMigrationError):
        caribou.Migration.from_module(mod)


def test_upgrade_with_modules(sqlite_test_path):
    """assert upgrade works when given a list of modules"""
    db_url = sqlite_test_path

    def up1(conn):
        conn.execute("CREATE TABLE mod_table1 (id NUMBER)")

    def down1(conn):
        conn.execute("DROP TABLE mod_table1")

    def up2(conn):
        conn.execute("CREATE TABLE mod_table2 (id NUMBER)")

    def down2(conn):
        conn.execute("DROP TABLE mod_table2")

    modules = [
        _make_migration_module("v20240101120000_first", up1, down1),
        _make_migration_module("v20240215090000_second", up2, down2),
    ]

    caribou.upgrade(db_url, modules)

    conn = sqlite3.connect(db_url)
    assert _table_exists(conn, "mod_table1")
    assert _table_exists(conn, "mod_table2")
    assert caribou.get_version(db_url) == "20240215090000"
    conn.close()


def test_downgrade_with_modules(sqlite_test_path):
    """assert downgrade works when given a list of modules"""
    db_url = sqlite_test_path

    def up1(conn):
        conn.execute("CREATE TABLE mod_table1 (id NUMBER)")

    def down1(conn):
        conn.execute("DROP TABLE mod_table1")

    def up2(conn):
        conn.execute("CREATE TABLE mod_table2 (id NUMBER)")

    def down2(conn):
        conn.execute("DROP TABLE mod_table2")

    modules = [
        _make_migration_module("v20240101120000_first", up1, down1),
        _make_migration_module("v20240215090000_second", up2, down2),
    ]

    # upgrade first
    caribou.upgrade(db_url, modules)
    # downgrade to version 0
    caribou.downgrade(db_url, modules, "0")

    conn = sqlite3.connect(db_url)
    assert not _table_exists(conn, "mod_table1")
    assert not _table_exists(conn, "mod_table2")
    assert caribou.get_version(db_url) == "0"
    conn.close()


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


def test_parse_migration_name():
    """assert _parse_migration_name handles all naming conventions"""
    # bare digits
    assert _parse_migration_name("20091112130101_my_migration") == (
        "20091112130101",
        "my_migration",
    )
    # v-prefix
    assert _parse_migration_name("v20091112150200_new_style") == (
        "20091112150200",
        "new_style",
    )
    # double underscore stripped
    assert _parse_migration_name("20091112130101__migration_one") == (
        "20091112130101",
        "migration_one",
    )
    # v-prefix with .py extension stripped by caller, but name portion only
    assert _parse_migration_name("v20091112150200_create_users") == (
        "20091112150200",
        "create_users",
    )
    # garbage input
    assert _parse_migration_name("not_a_migration") == (None, None)
    # empty string
    assert _parse_migration_name("") == (None, None)
    # too short
    assert _parse_migration_name("12345") == (None, None)
    # v-prefix too short
    assert _parse_migration_name("v12345") == (None, None)
    # bare digits no name portion
    assert _parse_migration_name("20091112130101") == ("20091112130101", "")


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
