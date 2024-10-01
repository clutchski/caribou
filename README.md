Caribou SQLite Migrations
=========================

<div style="left: right; padding: 0px 0px 2em 2em">
    <img src="http://imgur.com/DySrz.jpg" alt="Caribou" />
</div>

Caribou is a small, simple [SQLite][sqlite] database [migrations][rails]
library for [Python][python], built primarily to manage the evoluton of client
side databases over multiple releases of an application.

  [rails]:http://guides.rubyonrails.org/migrations.html
  [python]: http://python.org/
  [sqlite]: https://sqlite.org/

Example
-------

Here is a simple example illustrating how to use Caribou to manage your SQLite
schema:

#### Create a Migration

Use Caribou's command line tool to create your first migration:

```bash
$ caribou create my_first_migration
created migration ./20091115140758_my_first_migration.py
```

#### Edit Your Migration

Let's create a table with some data in the upgrade step and reverse the changes
in the downgrade step.

```python
"""
An example of a Caribou migration file.
"""

def upgrade(connection):
    # connection is a plain old sqlite3 database connection
    sql = """
        create table animals
        ( name     TEXT
        , status   TEXT
        ) """
    connection.execute(sql)

    animals = [ ('caribou', 'least concerned')
              , ('bengal tiger', 'threatened')
              , ('eastern elk', 'extinct')
              ]
    sql = 'insert into animals values (:1, :2)'
    for name, status in animals:
        connection.execute(sql, [name, status])

    connection.commit()

def downgrade(connection):
    connection.execute('drop table animals')
```

Caribou migrations are flexible because they are plain Python files. Feel free
to add logging, DDL transactions, anything at all.

#### Run Your Migration:

Caribou migrations can be run with the command line tool:

```
$ caribou upgrade db.sqlite .
upgrading db [db.sqlite] to most recent version
upgraded [db.sqlite] successfully to version [20091115140758]

# if you want to revert your changes, uses the downgrade command:

$ caribou downgrade db.sqlite . 0
downgrading db [db.sqlite] to version [0]
downgraded [db.sqlite] successfully to version [0]
```

Since Caribou is built to manage client side SQLite databases, it can also be
run programmatically from within your application:

```python
"""
An example illustrating how to run a migration programmatically.
"""

import caribou

db = 'db.sqlite'
migrations_dir = '/path/to/migrations/dir'
version = '20091115140758'

# upgrade to most recent version
caribou.upgrade(db, migrations_dir)

# upgrade to a specific version
caribou.upgrade(db, migrations_dir, version)

# downgrade to a specific version
caribou.downgrade(db, migrations_dir, version)
```

That's it. You're rolling.

Installation
------------

    pip install caribou

Licence
--------

    Caribou is in the public domain.

Development
-----------

Things to know, before you start hacking Caribou:

#### Unit Tests

The unit test suite uses pytest and tox. To install and run:

    pip install tox pytest
    tox

Appendix
--------

Haven't got enough?

* [Additional Reading][migration]
* [Additional Listening][music]

[migration]: http://en.wikipedia.org/wiki/Caribou#Migration
[music]: http://www.myspace.com/cariboumanitoba

