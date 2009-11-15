"""
nose unit tests for caribou migrations
"""

from __future__ import with_statement

import glob
import os
import shutil
import sqlite3
import traceback

import caribou

TEST_DB = 'test.sqlite3'
MIGRATIONS_DIR = 'migrations'
INVALID_MIGRATIONS = 'invalid_migrations'
INVALID_CODE = os.path.join(INVALID_MIGRATIONS, 'code')
INVALID_NAMES = os.path.join(INVALID_MIGRATIONS, 'names')

def get_this_dir():
    return os.path.abspath(os.path.dirname(__file__))

class TestCaribouMigrations(object):

    def __init__(self):
        this_dir = get_this_dir()
        self.db_url = os.path.join(this_dir, TEST_DB)
        self.migrations_path = os.path.join(this_dir, MIGRATIONS_DIR)

    def setUp(self):
        pass

    def tearDown(self):
        if os.path.exists(self.db_url):
            os.remove(self.db_url)

    @staticmethod
    def _table_exists(conn, table_name):
        sql = """
            SELECT *
              FROM sqlite_master
             WHERE type = 'table'
               AND name = :1
               """
        with caribou.execute(conn, sql, [table_name]) as cursor:
            return bool(cursor.fetchall())

    def test_invalid_migration_filenames(self):
        """
        assert we can't load migrations with invalid version names
        """
        # assert we test invalid version names
        invalid_names = os.path.join(get_this_dir(), INVALID_NAMES, '*.py')
        for filename in glob.glob(invalid_names):
            try:
                migration = caribou.Migration(filename)
                migration.get_version()
            except caribou.InvalidNameError:
                pass
            else:
                assert False, filename


    def test_valid_migration_filenames(self):
        """ assert we can parse the versions from migration files """
        # test some valid versions
        for version, suffix in [ ('20091112130101', '__migration_one.py')
                               , ('20091112150200', '__migration_two.py')
                               , ('20091112150205', '_migration_three.py')
                               ]:
            path = os.path.join(self.migrations_path, version + suffix)
            migration = caribou.Migration(path)
            actual_version = migration.get_version()
            assert actual_version == version, '%s != %s' % (
                            actual_version, version)

    def test_invalid_migraton_code(self):
        filenames = [ '20091112130101_syntax_error.py'
                    , '20091112150200_missing_upgrade.py'
                    , '20091112150205_missing_downgrade.py'
                    ]
        code_dir = os.path.join(get_this_dir(), INVALID_CODE)
        # assert we can't load a directory containing invalid migrations
        try:
            caribou.get_migrations(code_dir)
        except caribou.InvalidMigrationError:
            pass
        else:
            assert False, 'loaded a dir with invalid migrations'
        # assert we can't load invalid migrations one by one
        migrations = [os.path.join(code_dir, f) for f in filenames]
        for migration in migrations:
            try:
                caribou.Migration(migration)
            except caribou.InvalidMigrationError:
                pass
            else:
                assert False, 'loaded invalid migration [%s]' % migration

    def test_unknown_migration(self):
        """ assert we can't target an unknown migration or non existant dirs"""
        db_url = self.db_url
        migrations_path = self.migrations_path
        for v in ['asdf', '22341', 'asdfasdfasdf', '----']:
            for func in [caribou.upgrade, caribou.downgrade]:
                try:
                    func(db_url, migrations_path, v)
                except caribou.Error:
                    pass
                else:
                    assert False, 'ran an unknown migration'
        # assert we can't run non-existant migrations
        path = '/path/to/nowhereski/whoop'
        for func, args in [ (caribou.upgrade, (db_url, path, None))
                          , (caribou.downgrade, (db_url, path, 0))
                          ]:
            try:
                func(*args)
            except caribou.Error:
                pass
            else:
                assert False, '%s %s' % (func, str(args))

    def test_migration(self):
        # assert migrations haven't been run
        db_url = self.db_url
        conn = sqlite3.connect(db_url)
        assert not self._table_exists(conn, 'games')
        assert not self._table_exists(conn, 'players')
        assert caribou.get_version(db_url) == None

        # assert that the first migration has been run successfully
        # and that subsequent runs have no effect 

        v1 = '20091112130101' 
        v2 = '20091112150200'
        v3 = '20091112150205'

        for _ in range(3):
            caribou.upgrade(db_url, self.migrations_path, v1)
            assert self._table_exists(conn, 'games')
            assert self._table_exists(conn, 'players')
            actual_version = caribou.get_version(self.db_url)
            assert actual_version == v1, '%s != %s' % (actual_version, v1)
            # make sure none of the other migrations run
            assert not self._table_exists(conn, 'scores')

        # run the 2nd migration
        for _ in range(3):
            caribou.upgrade(db_url, self.migrations_path, v2)
            tables = ['games', 'players', 'scores']
            assert all((self._table_exists(conn, t) for t in tables))
            actual_version = caribou.get_version(db_url)
            assert actual_version == v2, '%s != %s' % (actual_version, v2)

        # downgrade the second migration
        for _ in range(3):
            caribou.downgrade(db_url, self.migrations_path, v1)
            assert self._table_exists(conn, 'games')
            assert self._table_exists(conn, 'players')
            actual_version = caribou.get_version(db_url)
            assert actual_version == v1, '%s != %s' % (actual_version, v1)
            # make sure none of the other migrations run
            assert not self._table_exists(conn, 'scores')

        # upgrade all the way 
        for _ in range(3):
            caribou.upgrade(db_url, self.migrations_path)
            tables = ['games', 'players', 'scores', 'jams']
            assert all((self._table_exists(conn, t) for t in tables))
            actual_version = caribou.get_version(db_url)
            assert actual_version == v3, '%s != %s' % (actual_version, v3)

        # downgrade all the way 
        for _ in range(3):
            caribou.downgrade(db_url, self.migrations_path, 0)
            tables = ['games', 'players', 'scores', 'jams']
            assert all((not self._table_exists(conn, t) for t in tables))
            actual_version = caribou.get_version(db_url)
            assert actual_version == '0'

        # upgrade all the way again
        for _ in range(3):
            caribou.upgrade(db_url, self.migrations_path)
            tables = ['games', 'players', 'scores', 'jams']
            assert all((self._table_exists(conn, t) for t in tables))
            actual_version = caribou.get_version(db_url)
            assert actual_version == v3, '%s != %s' % (actual_version, v3)

    def test_create_migration(self):
        """ assert we can create migration templates """
        for name, directory in [ ('tc_1', None), ('tc_2', 'test_create__')]:
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            path = caribou.create_migration(name, directory)
            try:
                assert os.path.exists(path)
                # assert it is a valid migration
                caribou.Migration(path)
            finally:
                # remove compiled test migration as well
                for path in [path, path + 'c']:
                    if os.path.exists(path):
                        os.remove(path)
                if directory and os.path.exists(directory):
                    shutil.rmtree(directory)
        # assert we can't create migrations in a directoin that doesn't exist
        try:
            caribou.create_migration('adsf', '/path/to/nowhereski')
        except caribou.Error:
            pass
        else:
            assert False

