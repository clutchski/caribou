import contextlib
import datetime
import glob
import os.path
import sqlite3
import traceback
import importlib.util

# statics

VERSION_TABLE = "migration_version"
UTC_LENGTH = 14

# errors


class Error(Exception):
    """Base class for all Caribou errors."""

    pass


class InvalidMigrationError(Error):
    """Thrown when a client migration contains an error."""

    pass


class InvalidNameError(Error):
    """Thrown when a client migration has an invalid filename."""

    def __init__(self, filename):
        msg = (
            "Migration filenames must start with a UTC timestamp. "
            f"The following file has an invalid name: {filename}"
        )
        super().__init__(msg)


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
    except Exception:
        conn.rollback()
        raise


def has_method(an_object, name):
    return callable(getattr(an_object, name, None))


def is_directory(path):
    return os.path.exists(path) and os.path.isdir(path)


class Migration:
    """This class represents a migration version."""

    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.module_name, _ = os.path.splitext(self.filename)
        self.get_version()  # will assert the filename is valid
        self.name = self.module_name[UTC_LENGTH:]
        while self.name.startswith("_"):
            self.name = self.name[1:]
        try:
            spec = importlib.util.spec_from_file_location(self.module_name, path)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
        except Exception:
            msg = f"Invalid migration {path}: {traceback.format_exc()}"
            raise InvalidMigrationError(msg)
        # assert the migration has the needed methods
        targets = ["upgrade", "downgrade"]
        missing = [m for m in targets if not has_method(self.module, m)]
        if missing:
            msg = (
                f"Migration {self.path} is missing required"
                f" methods: {', '.join(missing)}."
            )
            raise InvalidMigrationError(msg)

    def get_version(self):
        if len(self.filename) < UTC_LENGTH:
            raise InvalidNameError(self.filename)
        timestamp = self.filename[:UTC_LENGTH]
        # FIXME: is this test sufficient?
        if not timestamp.isdigit():
            raise InvalidNameError(self.filename)
        return timestamp

    def upgrade(self, conn):
        self.module.upgrade(conn)

    def downgrade(self, conn):
        self.module.downgrade(conn)

    def __repr__(self):
        return f"Migration({self.filename})"


class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = sqlite3.connect(db_url)

    def close(self):
        self.conn.close()

    def is_version_controlled(self):
        sql = """select *
                   from sqlite_master
                  where type = 'table'
                    and name = ?"""
        with execute(self.conn, sql, [VERSION_TABLE]) as cursor:
            return bool(cursor.fetchall())

    def upgrade(self, migrations, target_version=None):
        if target_version:
            _assert_migration_exists(migrations, target_version)

        migrations.sort(key=lambda x: x.get_version())
        database_version = self.get_version()

        for migration in migrations:
            current_version = migration.get_version()
            if current_version <= database_version:
                continue
            if target_version and current_version > target_version:
                break
            migration.upgrade(self.conn)
            new_version = migration.get_version()
            self.update_version(new_version)

    def downgrade(self, migrations, target_version):
        if target_version not in (0, "0"):
            _assert_migration_exists(migrations, target_version)

        migrations.sort(key=lambda x: x.get_version(), reverse=True)
        database_version = self.get_version()

        for i, migration in enumerate(migrations):
            current_version = migration.get_version()
            if current_version > database_version:
                continue
            if current_version <= target_version:
                break
            migration.downgrade(self.conn)
            next_version = 0
            # if an earlier migration exists, set the db version to
            # its version number
            if i < len(migrations) - 1:
                next_migration = migrations[i + 1]
                next_version = next_migration.get_version()
            self.update_version(next_version)

    def get_version(self):
        """Return the database's version, or None if it is not under version
        control.
        """
        if not self.is_version_controlled():
            return None
        sql = f"select version from {VERSION_TABLE}"
        with execute(self.conn, sql) as cursor:
            result = cursor.fetchall()
            return result[0][0] if result else 0

    def update_version(self, version):
        sql = f"update {VERSION_TABLE} set version = ?"
        with transaction(self.conn):
            self.conn.execute(sql, [version])

    def initialize_version_control(self):
        sql = f""" create table if not exists {VERSION_TABLE}
                  ( version text ) """
        with transaction(self.conn):
            self.conn.execute(sql)
            self.conn.execute(f"insert into {VERSION_TABLE} values (0)")

    def __repr__(self):
        return f'Database("{self.db_url}")'


def _assert_migration_exists(migrations, version):
    if version not in (m.get_version() for m in migrations):
        raise Error(f"No migration with version {version} exists.")


def load_migrations(directory):
    """Return the migrations contained in the given directory."""
    if not is_directory(directory):
        raise Error(f"{directory} is not a directory.")
    wildcard = os.path.join(directory, "*.py")
    migration_files = glob.glob(wildcard)
    return [Migration(f) for f in migration_files]


def upgrade(db_url, migration_dir, version=None):
    """Upgrade the given database with the migrations contained in the
    migrations directory. If a version is not specified, upgrade
    to the most recent version.
    """
    with contextlib.closing(Database(db_url)) as db:
        db = Database(db_url)
        if not db.is_version_controlled():
            db.initialize_version_control()
        migrations = load_migrations(migration_dir)
        db.upgrade(migrations, version)


def downgrade(db_url, migration_dir, version):
    """Downgrade the database to the given version with the migrations
    contained in the given migration directory.
    """
    with contextlib.closing(Database(db_url)) as db:
        if not db.is_version_controlled():
            raise Error(f"The database {db_url} is not version controlled.")
        migrations = load_migrations(migration_dir)
        db.downgrade(migrations, version)


def get_version(db_url):
    """Return the migration version of the given database."""
    with contextlib.closing(Database(db_url)) as db:
        return db.get_version()


def create_migration(name, directory=None):
    """Create a migration with the given name. If no directory is specified,
    the current working directory will be used.
    """
    directory = directory if directory else "."
    if not is_directory(directory):
        raise Error(f"{directory} is not a directory.")

    now = datetime.datetime.now()
    version = now.strftime("%Y%m%d%H%M%S")

    contents = MIGRATION_TEMPLATE % {"name": name, "version": version}

    name = name.replace(" ", "_")
    filename = f"{version}_{name}.py"
    path = os.path.join(directory, filename)
    with open(path, "w") as migration_file:
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
