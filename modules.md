# Module-Based Migration Support

## Context

Caribou currently discovers migrations by scanning a filesystem directory for `.py` files. This breaks when apps are bundled with PyInstaller, Poetry, or similar tools (GitHub issue #13). We're adding support for passing already-imported Python modules directly to `upgrade()` and `downgrade()`.

The existing naming convention (`20091112130101_name.py`) can't be imported as a Python module because identifiers can't start with digits. We'll support a new `v`-prefix convention (`v20091112130101_name.py`) that is both importable and sortable, while keeping the old convention working.

## User-facing API

```python
import caribou
from myapp.migrations import v20240101120000_create_users, v20240215090000_add_scores

# New: pass a list of modules
caribou.upgrade("my.db", [v20240101120000_create_users, v20240215090000_add_scores])
caribou.downgrade("my.db", [v20240101120000_create_users, v20240215090000_add_scores], version="0")

# Existing: pass a directory path (still works)
caribou.upgrade("my.db", "./migrations")
```

Migration files with the new convention:

```python
# v20240101120000_create_users.py  (v-prefix -- importable and sortable!)
def upgrade(connection):
    connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

def downgrade(connection):
    connection.execute("DROP TABLE users")
```

## Files to modify

- `caribou/migrate.py` -- Core changes
- `tests/test_caribou.py` -- New tests
- `tests/mixed_migrations/` -- New test fixture directory
- `README.md` -- Documentation

No changes to `caribou/__init__.py` or `caribou/cli.py`.

## Implementation (TDD)

### Step 1: Update `Migration.get_version()` to support v-prefix

Currently extracts version from `filename[:14]`. Update to also try `filename[1:15]` when the filename starts with `v`. Try bare digits first for backward compat, then v-prefix.

`caribou/migrate.py` -- `Migration.get_version()` (line 98):

```python
def get_version(self):
    if hasattr(self, "_version"):
        return self._version
    # Try start of filename (existing: 20091112130101_name.py)
    if len(self.filename) >= UTC_LENGTH:
        timestamp = self.filename[:UTC_LENGTH]
        if timestamp.isdigit():
            return timestamp
    # Try v-prefix (new: v20091112130101_name.py)
    if len(self.filename) >= UTC_LENGTH + 1 and self.filename[0] == "v":
        timestamp = self.filename[1 : 1 + UTC_LENGTH]
        if timestamp.isdigit():
            return timestamp
    raise InvalidNameError(self.filename)
```

### Step 2: Update `Migration.__init__` name extraction

Currently `self.name` strips from position `UTC_LENGTH` onward. For v-prefix files, strip from `1 + UTC_LENGTH`. Update to handle both:
- `20091112130101__migration_one` -> name = `migration_one` (existing)
- `v20091112130101_migration_one` -> name = `migration_one` (new)

```python
# in __init__, after get_version():
if self.module_name[0] == "v" and self.module_name[1 : 1 + UTC_LENGTH].isdigit():
    self.name = self.module_name[1 + UTC_LENGTH:]
else:
    self.name = self.module_name[UTC_LENGTH:]
while self.name.startswith("_"):
    self.name = self.name[1:]
```

### Step 3: Add `Migration.from_module()` classmethod

New classmethod on `Migration` class:
- Creates instance via `cls.__new__(cls)`
- Extracts version from `module.__name__`: tries digits at start, then v-prefix
- Falls back to `module.VERSION` attribute if module name doesn't contain version
- Validates `upgrade`/`downgrade` callables exist
- Sets `self.path`, `self.filename`, `self.module_name`, `self.name`, `self.module`, `self._version`

### Step 4: Update `Migration.__repr__`

Handle `self.filename` being `None` for module-based migrations -- use `self.module_name` instead.

### Step 5: Add `_migrations_from_modules(modules)` helper

Private function parallel to `load_migrations()`. Returns `[Migration.from_module(m) for m in modules]`.

### Step 6: Modify `upgrade()` and `downgrade()`

Detect type of second argument:
- `isinstance(migrations, str)` -> directory path, call `load_migrations()` (existing behavior)
- Otherwise -> list of modules, call `_migrations_from_modules()`

### Step 7: Update `create_migration()` to generate v-prefix filenames

Add a `VERSION_PREFIX = "v"` constant. Change `create_migration()` to generate `v20091112130101_name.py` instead of `20091112130101_name.py`. Update `MIGRATION_TEMPLATE` to include the `v` prefix in the version comment.

```python
VERSION_PREFIX = "v"

# in create_migration():
filename = "%s%s_%s.py" % (VERSION_PREFIX, version, name)

# in MIGRATION_TEMPLATE:
# Migration Version: v%(version)s
```

### Step 8: Update `InvalidNameError` message

Current message says "must start with a UTC timestamp" -- update to also mention v-prefix.

### Step 9: Add migration guide to README

Document:
- The new v-prefix convention (`v20091112130101_name.py`)
- How to use `upgrade()`/`downgrade()` with a module list
- Converting existing files (just add `v` prefix)

## Test plan

All in `tests/test_caribou.py`. Uses existing helper:

```python
def _make_migration_module(name, upgrade_fn, downgrade_fn):
    mod = types.ModuleType(name)
    mod.upgrade = upgrade_fn
    mod.downgrade = downgrade_fn
    return mod
```

Test fixture files in `tests/mixed_migrations/`:
- `20091112130101__old_style.py` -- timestamp-first (existing), creates `old_table`
- `v20091112150200_new_style.py` -- v-prefix (new), creates `new_table`

Tests (TDD order):
1. `test_v_prefix_migration_filenames` -- v-prefix files parse version and name correctly
2. `test_mixed_directory` -- directory with both conventions loads and runs correctly; ordering by version works
3. `test_migration_from_module` -- `Migration.from_module()` works with v-prefix module name
4. `test_migration_from_module_with_version_attr` -- falls back to `module.VERSION`
5. `test_migration_from_module_missing_version` -- raises `InvalidMigrationError`
6. `test_migration_from_module_missing_methods` -- raises `InvalidMigrationError`
7. `test_upgrade_with_modules` -- full integration: upgrade with module list
8. `test_downgrade_with_modules` -- full integration: downgrade with module list
9. All existing tests pass unchanged

## Verification

```bash
python -m pytest tests/test_caribou.py -v
```
