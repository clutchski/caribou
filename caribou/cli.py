#!/usr/bin/env python
"""
this module contains the command line interface for the caribou
database migrations library
"""

# stdlib
import sys
import traceback

# 3p
import argparse

# project
import caribou

# statics

EXIT_SUCCESS = 0
EXIT_FAILURE = -1


def _print_error(message):
    sys.stderr.write("%s\n" % message)


def _print_info(message):
    sys.stdout.write("%s\n" % message)


def info_command(args):
    _print_info("Caribou version: %s" % caribou.__version__)


def create_migration_command(args):
    name = args.name
    directory = args.migration_dir
    path = caribou.create_migration(name, directory)
    _print_info("created migration %s" % path)


def print_version_command(args):
    db_path = args.database_path
    version = caribou.get_version(db_path)
    msg = "the db [%s] is not under version control" % db_path
    if version:
        msg = "the db [%s] is at version %s" % (db_path, version)
    _print_info(msg)


def upgrade_db_command(args):
    db_path = args.database_path
    migration_dir = args.migration_dir
    version = args.version
    msg = "upgrading db [%s] to most recent version" % db_path
    if version:
        msg = "upgrading db [%s] to version [%s]" % (db_path, version)
    _print_info(msg)
    caribou.upgrade(db_path, migration_dir, version)
    new_version = caribou.get_version(db_path)
    if version:
        assert new_version == version
    msg = "upgraded [%s] successfully to version [%s]" % (db_path, new_version)
    _print_info(msg)


def downgrade_db_command(args):
    db_path = args.database_path
    migration_dir = args.migration_dir
    version = args.version
    msg = "downgrading db [%s] to version [%s]" % (db_path, version)
    _print_info(msg)
    caribou.downgrade(db_path, migration_dir, version)
    msg = "downgraded [%s] successfully to version [%s]" % (db_path, version)
    _print_info(msg)


def list_migrations_command(args):
    migration_dir = args.migration_dir
    _print_info("Migrations in [%s]:" % migration_dir)
    _print_info("")
    migrations = caribou.load_migrations(migration_dir)
    for migration in migrations:
        version = migration.get_version()
        path = migration.path
        name = migration.name
        line = "%s\t%s\t%s" % (version, name, path)
        _print_info(line)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(help="commands")
    # add the create migration command
    create_cmd = commands.add_parser(CREATE_CMD, help=CREATE_CMD_HELP)
    create_cmd.add_argument(NAME, help=NAME_HELP)
    create_cmd.add_argument(DIR, DIR_LONG, help=DIR_HELP)
    create_cmd.set_defaults(func=create_migration_command)
    create_cmd.set_defaults(migration_dir=".")
    # add the version command
    version_cmd = commands.add_parser(VERSION_CMD, help=VERSION_CMD_HELP)
    version_cmd.add_argument(DB, help=DB_HELP)
    version_cmd.set_defaults(func=print_version_command)
    # add the upgrade command
    upgrade_cmd = commands.add_parser(UP_CMD, help=UP_CMD_HELP)
    upgrade_cmd.add_argument(DB, help=DB_HELP)
    upgrade_cmd.add_argument(DIR_ARG, help=DIR_HELP)
    upgrade_cmd.add_argument(VERSION_OPT, VERSION_OPT_LONG, help=VERSION_HELP)
    upgrade_cmd.set_defaults(version=None)
    upgrade_cmd.set_defaults(func=upgrade_db_command)
    # add the downgrade command
    upgrade_cmd = commands.add_parser(DOWN_CMD, help=DOWN_CMD_HELP)
    upgrade_cmd.add_argument(DB, help=DB_HELP)
    upgrade_cmd.add_argument(DIR_ARG, help=DIR_HELP)
    upgrade_cmd.add_argument(VERSION_ARG, help=VERSION_HELP)
    upgrade_cmd.set_defaults(func=downgrade_db_command)
    # add the migration list command
    list_cmd = commands.add_parser(LIST_CMD, help=LIST_CMD_HELP)
    list_cmd.add_argument(DIR_ARG, help=DIR_HELP)
    list_cmd.set_defaults(func=list_migrations_command)
    meta_cmd = commands.add_parser("info")
    meta_cmd.set_defaults(func=info_command)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    # call the command's func
    return_code = EXIT_FAILURE
    try:
        args.func(args)
    except caribou.InvalidMigrationError:
        # show the full trace for invalid migration errors, because they
        # are likely to include syntax errors and such
        _print_error(traceback.format_exc())
    except caribou.Error as err:
        # expected errors, only show the error string
        _print_error("")
        _print_error("Error: %s " % str(err))
    except Exception:
        _print_error("an unexpected error occured:")
        _print_error(traceback.format_exc())
    else:
        return_code = EXIT_SUCCESS
    finally:
        return return_code


# options/arguments

DIR_ARG = "migration_dir"
DIR = "-d"
DIR_LONG = "--migration-dir"
DIR_HELP = "the migration directory"

DB = "database_path"
DB_HELP = "path to the sqlite database"

NAME = "name"
NAME_HELP = "the name of migration"

VERSION_ARG = "version"
VERSION_OPT = "-v"
VERSION_OPT_LONG = "--version"
VERSION_HELP = "the target migration version"

# commands

CREATE_CMD = "create"
CREATE_CMD_HELP = "create a new migration file"

VERSION_CMD = "version"
VERSION_CMD_HELP = "return the migration version of the database"

UP_CMD = "upgrade"
UP_CMD_HELP = (
    "upgrade the db. if a version isn't specified, "
    "upgrade to the most recent version."
)

DOWN_CMD = "downgrade"
DOWN_CMD_HELP = (
    "downgrade the db to a particular version. to rollback "
    "all changes, set the version to 0"
)

LIST_CMD = "list"
LIST_CMD_HELP = "list the migration versions"

if __name__ == "__main__":
    sys.exit(main())
