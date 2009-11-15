"""
Caribou is a simple SQLite database migrations library, built primarily
to manage the evoluton of client side databases over multiple releases 
of an application.
"""

from __future__ import with_statement

__author__ = 'clutchski'
__email__ = 'clutchski@gmail.com'

import contextlib
import datetime
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
    except:
        conn.rollback()
        m = "error in transaction: %s" % traceback.format_exc()
        raise Error(m)

def function_transaction(function):
    def _wrapped(conn):
        with transaction(conn):
            function(conn)
    return _wrapped

def has_method(an_object, method_name):
    return hasattr(an_object, method_name) and \
                    callable(getattr(an_object, method_name))

class Migration(object):
    """ represents one migration file """

    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.module_name, _ = os.path.splitext(self.filename)
        # call get_version, will assert the filename works
        self.get_version()
        self.name = self.module_name[UTC_LENGTH:]
        while self.name.startswith('_'):
            self.name = self.name[1:]
        try:
            self.module = imp.load_source(self.module_name, path)
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

class Database(object):

    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = sqlite3.connect(db_url)

    def get_version(self):
        sql = "SELECT version FROM %s" % VERSION_TABLE
        try:
            with execute(self.conn, sql) as cursor:
                return cursor.fetchall()[0][0]
        except sqlite3.OperationalError:
            return None

    def is_version_controlled(self):
        sql = """SELECT *
                   FROM sqlite_master
                  WHERE type = 'table'
                    AND name = :1"""
        with execute(self.conn, sql, [VERSION_TABLE]) as cursor:
            return bool(cursor.fetchall())

    def upgrade(self, migrations, target_version=None):
        current_version = self.get_version()
        for migration in migrations:
            if migration.get_version() <= current_version:
                continue
            if target_version and migration.get_version() > target_version:
                break
            migration.upgrade(self.conn)
            new_version = migration.get_version()
            self.update_version(new_version)

    def downgrade(self, migrations, target_version):
        current_version = self.get_version()
        for i, migration in enumerate(migrations):
            if migration.get_version() > current_version:
                continue
            if migration.get_version() <= target_version:
                break
            migration.downgrade(self.conn)
            # set the version to the one below on the queue, or 0 if 
            # this is the last
            next_version = 0
            next_i = i + 1
            if next_i < len(migrations):
                next_migration = migrations[next_i]
                next_version = next_migration.get_version()
            self.update_version(next_version)

    def get_version(self):
        """ return the database's version, or None if it is not versioned """
        sql = "SELECT version FROM %s" % VERSION_TABLE
        if not self.is_version_controlled():
            return None
        with execute(self.conn, sql) as cursor:
            return cursor.fetchall()[0][0]

    def update_version(self, version):
        sql = 'update %s set version = :1' % VERSION_TABLE
        with transaction(self.conn):
            self.conn.execute(sql, [version])

    def initialize_version_control(self):
        sql = """
            CREATE TABLE IF NOT EXISTS %s
            ( version TEXT )""" % VERSION_TABLE
        with transaction(self.conn):
            self.conn.execute(sql)
            self.conn.execute('insert into %s values (0)' % VERSION_TABLE)
    
    def __repr__(self):
        return 'Database("%s")' % self.db_url

def migration_exists(migrations, version):
    version_exists = False
    for migration in migrations:
        if version == migration.get_version():
            version_exists = True
            break
    return version_exists

def get_migrations(directory, target_version=None, reverse=False):
    """
    return the migrations in the directory, sorted by version number. if a
    target version is passed, assert a migration with that version exists
    """
    wildcard = os.path.join(directory, '*.py')
    migration_files = glob.glob(wildcard)
    migrations = [Migration(f) for f in migration_files]
    if target_version and not migration_exists(migrations, target_version):
        m = "no migration exists with version [%s]" % target_version
        raise InvalidMigrationError(m)
    return sorted(migrations, key=lambda x: x.get_version(), reverse=reverse)
    
def upgrade(db_url, migration_dir, version=None):
    db = Database(db_url)
    if not db.is_version_controlled():
        db.initialize_version_control()
    migrations = get_migrations(migration_dir, version)
    db.upgrade(migrations, version)

def downgrade(db_url, migration_dir, version):
    db = Database(db_url)
    if not db.is_version_controlled():
        m = "Can't downgrade %s because it is not version controlled." % db_url
        raise Error(m)
    target_version = version
    if version == '0':
        target_version = None
    migrations = get_migrations(migration_dir, target_version, reverse=True)
    db.downgrade(migrations, version)

def get_version(db_url):
    db = Database(db_url)
    return db.get_version()

def create_migration(name, directory=None):
    if not directory:
        directory = '.'
    def get_next_version():
        now = datetime.datetime.now()
        return now.strftime("%Y%m%d%H%M%S")
    version = get_next_version()
    contents = MIGRATION_TEMPLATE % {'name':name, 'version':version}
    name = name.replace(' ', '_')
    filename = "%s_%s.py" % (version, name)
    path = os.path.join(directory, filename)
    with open(path, 'w') as f:
        f.write(contents)
    return path

MIGRATION_TEMPLATE = """\
\"\"\"
a caribou migration

name: %(name)s 
version: %(version)s
\"\"\"

def upgrade(connection):
    # add your upgrade step here
    pass

def downgrade(connection):
    # add your downgrade step here
    pass
"""

