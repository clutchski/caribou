"""
this module contains super simple migrations for sqlite databases

http://en.wikipedia.org/wiki/Caribou#Migration
"""

from __future__ import with_statement

import contextlib
import glob
import imp
import os.path
import sqlite3
import traceback

# statics

VERSION_TABLE = 'migration_version'
UTC_LENGTH = 14

# errors

class Error(Exception): pass

class InvalidMigrationError(Error): pass

class InvalidNameError(InvalidMigrationError):

    def __init__(self, filename):
        msg = 'migration filenames must start with a UTC timestamp. ' \
              'the following file has an invalid name: %s' % filename
        super(InvalidNameError, self).__init__(msg)

# code

@contextlib.contextmanager
def execute(conn, sql, params=None):
    params = [] if params is None else params
    cursor = conn.execute(sql, params)
    try:
        yield cursor
    finally:
        cursor.close()

@contextlib.contextmanager
def transaction(conn):
    try:
        yield
        conn.commit()
    except Exception, error:
        conn.rollback()
        raise error

def has_method(an_object, method_name):
    return hasattr(an_object, method_name) and \
                    callable(getattr(an_object, method_name))

class Migration(object):
    """ represents one migration file """

    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.name, _ = os.path.splitext(self.filename)
        # call get_version, will assert the filename works
        self.get_version()
        try:
            self.module = imp.load_source(self.name, path)
        except:
            m = "invalid migration [%s]: %s" % (path, traceback.format_exc())
            raise InvalidMigrationError(m)
        # assert the migration has the needed methods
        missing = [m for m in ['upgrade', 'downgrade'] 
                      if not has_method(self.module, m)]
        if missing:
            m = 'migration [%s] is missing required methods: %s' % (
                    self.path, ', '.join(missing))
            raise InvalidMigrationError(m)

    def get_version(self):
        if len(self.filename) < UTC_LENGTH:
            raise InvalidNameError(self.filename)
        timestamp = self.filename[:UTC_LENGTH]
        if not timestamp.isdigit():
            raise InvalidNameError(self.filename)
        return timestamp

    def upgrade(self, conn):
        self.module.upgrade(conn)

    def downgrade(self, conn):
        self.module.downgrade(conn)

    def __cmp__(self, other):
        # compare by version number
        cmp(self.get_version(), other.get_version())

    def __repr__(self):
        return 'Migration(%s)' % self.filename


def get_migrations(directory, reverse=False):
    """ return the migrations in the directory, sorted by age"""
    wildcard = os.path.join(directory, '*.py')
    migration_files = glob.glob(wildcard)
    migrations = [Migration(f) for f in migration_files]
    return sorted(migrations, key=lambda x: x.get_version(), reverse=reverse)
    
def get_version(conn):
    """ return the database's version, or None if it is not versioned """
    sql = "SELECT version FROM %s" % VERSION_TABLE
    try:
        with execute(conn, sql) as cursor:
            return cursor.fetchall()[0][0]
    except sqlite3.OperationalError:
        return None

def is_version_controlled(conn):
    sql = """SELECT *
               FROM sqlite_master
              WHERE type = 'table'
                AND name = :1"""
    with execute(conn, sql, [VERSION_TABLE]) as cursor:
        return bool(cursor.fetchall())

def update_version(conn, version):
    sql = 'update %s set version = :1' % VERSION_TABLE
    with transaction(conn):
        conn.execute(sql, [version])

def add_version_control(conn):
    sql = """
        CREATE TABLE IF NOT EXISTS %s
        ( version TEXT )""" % VERSION_TABLE
    with transaction(conn):
        conn.execute(sql)
        conn.execute('insert into %s values (0)' % VERSION_TABLE)

def upgrade(db_url, migration_dir, version=None):
    conn = sqlite3.connect(db_url)
    if not is_version_controlled(conn):
        add_version_control(conn)
    current_version = get_version(conn)
    migrations = get_migrations(migration_dir)
    for migration in migrations:
        if migration.get_version() <= current_version:
            continue
        if version and migration.get_version() > version:
            break
        migration.upgrade(conn)
        update_version(conn, migration.get_version())


def downgrade(db_url, migration_dir, version):
    conn = sqlite3.connect(db_url)
    if not is_version_controlled(conn):
        raise Error("%s is not under version control" % db_url)
    current_version = get_version(conn)
    migrations = get_migrations(migration_dir, reverse=True)
    for i, migration in enumerate(migrations):
        if migration.get_version() > current_version:
            continue
        if migration.get_version() <= version:
            break
        migration.downgrade(conn)
        # set the version to the one below on the queue, or 0 if 
        # this is the last
        next_version = 0
        next_i = i + 1
        if next_i < len(migrations):
            next_migration = migrations[next_i]
            next_version = next_migration.get_version()
        update_version(conn, next_version)

