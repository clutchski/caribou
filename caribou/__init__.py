"""
Caribou is a simple SQLite database migrations library, built
to manage the evoluton of client side databases over multiple releases
of an application.
"""

__version__ = "0.4.1"


# public API
from .migrate import (
    Error,
    InvalidMigrationError,
    InvalidNameError,
    upgrade,
    downgrade,
)

# things that probably shouldn't exist but are here for backwards compatiblity
from .migrate import (
    create_migration,
    execute,
    get_version,
    load_migrations,
    Migration,
    transaction,
)
