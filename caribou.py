"""
Caribou is a simple SQLite database migrations library, built
to manage the evoluton of client side databases over multiple releases 
of an application.
"""

from __future__ import with_statement

__author__ = 'clutchski@gmail.com'

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

class Error(Exception):
    """ Base class for all Caribou errors. """
    pass

class InvalidMigrationError(Error):
    """ Thrown when a client migration contains an error. """
    pass

class InvalidNameError(Error):
    """ Thrown when a client migration has an invalid filename. """

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
        msg = "Error in transaction: %s" % traceback.format_exc()
        raise Error(msg)

def function_transaction(function):
    def decorator(conn):
        with transaction(conn):
            function(conn)
    return decorator

def has_method(an_object, method_name):
    return hasattr(an_object, method_name) and \
                    callable(getattr(an_object, method_name))

def is_directory(path):
    return os.path.exists(path) and os.path.isdir(path)

class Migration(object):
    """ This class represents one migration version. """

    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.module_name, _ = os.path.splitext(self.filename)
        self.get_version() # will assert the filename is valid
        self.name = self.module_name[UTC_LENGTH:]
        while self.name.startswith('_'):
            self.name = self.name[1:]
        try:
            self.module = imp.load_source(self.module_name, path)
        except:
            msg = "Invalid migration %s: %s" % (path, traceback.format_exc())
            raise InvalidMigrationError(msg)
        # assert the migration has the needed methods
        missing = [m for m in ['upgrade', 'downgrade'] 
                      if not has_method(self.module, m)]
        if missing:
            msg = 'Migration %s is missing required methods: %s' % (
                    self.path, ', '.join(missing))
            raise InvalidMigrationError(msg)

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

    def close(self):
        self.conn.close()

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
        """ Return the database's version, or None if it is not under version
            control.
        """
        if not self.is_version_controlled():
            return None
        sql = "SELECT version FROM %s" % VERSION_TABLE
        with execute(self.conn, sql) as cursor:
            result = cursor.fetchall()
            version = 0
            if result:
                version = result[0][0]
            return version

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
    """ Return True if one the given migrations has the given version, False
        otherwise.
    """
    version_exists = False
    for migration in migrations:
        if version == migration.get_version():
            version_exists = True
            break
    return version_exists

def get_migrations(directory, target_version=None, reverse=False):
    """ Return the migrations contained in the given directory, sorted by
        version number. If a target version is specified, assert a migration
        with that version number exists.
    """
    if not is_directory(directory):
        msg = "%s is not a directory." % directory
        raise Error(msg)
    wildcard = os.path.join(directory, '*.py')
    migration_files = glob.glob(wildcard)
    migrations = [Migration(f) for f in migration_files]
    if target_version and not migration_exists(migrations, target_version):
        msg = "No migration exists with version %s." % target_version
        raise Error(msg)
    return sorted(migrations, key=lambda x: x.get_version(), reverse=reverse)
    
def upgrade(db_url, migration_dir, version=None):
    """ Upgrade the given database with the migrations contained in the
        migrations directory. If a version is not specified, upgrade
        to the most recent version.
    """
    with contextlib.closing(Database(db_url)) as db:
        db = Database(db_url)
        if not db.is_version_controlled():
            db.initialize_version_control()
        migrations = get_migrations(migration_dir, version)
        db.upgrade(migrations, version)

def downgrade(db_url, migration_dir, version):
    """ Downgrade the database to the given version with the migrations
        contained in the given migration directory.
    """
    with contextlib.closing(Database(db_url)) as db:
        if not db.is_version_controlled():
            msg = "The database %s is not version controlled." % (db_url)
            raise Error(msg)
        target_version = None if version == '0' else version
        migrations = get_migrations(migration_dir, target_version, reverse=True)
        db.downgrade(migrations, version)

def get_version(db_url):
    """ Return the migration version of the given database.
    """
    with contextlib.closing(Database(db_url)) as db:
        return db.get_version()

def create_migration(name, directory=None):
    """ Create a migration with the given name. If no directory is specified,
        the current working directory will be used.
    """
    directory = directory if directory else '.'
    if not is_directory(directory):
        msg = '%s is not a directory.' % directory
        raise Error(msg)

    now = datetime.datetime.now()
    version = now.strftime("%Y%m%d%H%M%S")

    contents = MIGRATION_TEMPLATE % {'name':name, 'version':version}
    name = name.replace(' ', '_')
    filename = "%s_%s.py" % (version, name)
    path = os.path.join(directory, filename)
    with open(path, 'w') as migration_file:
        migration_file.write(contents)
    return path

MIGRATION_TEMPLATE = """\
\"\"\"
This module contains a Caribou migration.

Migration Name: %(name)s 
Migration Version: %(version)s
\"\"\"

def upgrade(connection):
    # add your upgrade step here
    pass

def downgrade(connection):
    # add your downgrade step here
    pass
"""

