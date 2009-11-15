Caribou SQLite Migrations
=========================

<div style="left: right; padding: 0px 0px 2em 2em">
    <img src="http://imgur.com/DySrz.jpg" alt="Caribou" />
</div>

Caribou is a simple [SQLite][sqlite] database [migrations][rails] 
library for [Python][python], built primarily to manage the evoluton of client
side databases over multiple releases of an application.

  [rails]:http://guides.rubyonrails.org/migrations.html 
  [python]: http://python.org/
  [sqlite]: http://sqlite.ord

Example
-------

Here is a simple example illustrating how to use Caribou to manage your SQLite
schema:

#### Create a Migration

Use Caribou's command line tool to create your first migration:
    
    clutchski@shaolin:~$ caribou create my_first_migration
    created migration ./20091115140758_my_first_migration.py

#### Edit Your Migration

Let's create a table with some data in the upgrade step and reverse the changes
in the downgrade step.

    """
    an example of a Caribou migration file
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

#### Run Your Migration:

Caribou migrations can be run with the command line tool:

    clutchski@shaolin:~$ caribou upgrade my_sqlite_db .
    upgrading db [my_sqlite_db] to most recent version
    upgraded [my_sqlite_db] successfully to version [20091115140758]

    # if you want to revert your changes, uses the downgrade command:

    clutchski@shaolin:~$ caribou downgrade my_sqlite_db . 0
    downgrading db [my_sqlite_db] to version [0]
    downgraded [my_sqlite_db] successfully to version [0]

Since Caribou is built to manage client side sqlite databases, it can also be
run programmatically from within your application:

    """
    an example illustrating how to run a migration programmatically.
    """
    
    import caribou
    
    db_path = 'my_sqlite_db' 
    migrations_path = '/path/to/migrations/dir'
    version = '20091115140758'
    
    # upgrade to most recent version
    caribou.upgrade(db_version, migrations_path)
    
    # upgrade to a specific version
    caribou.upgrade(db_path, migrations_path, version)
    
    # downgrade to a specific version
    caribou.downgrade(db_path, migrations_path, version)

That's it. You're rolling.

Installation
------------

using setuptools:

    sudo easy_install caribou

or, [download][download] and extract the most code in the repo, and
run:

    sudo python setup.py install

[download]:http://github.com/clutchski/caribou/archives/master

Licence
--------

    Caribou is in the public domain.

Development
-----------

Things to know, before you start hacking Caribou:

#### Unit Tests

The unit test suite requires the [nose][nose] unit testing library. To install:

    sudo easy_install nose

To execute the test suite, run:

    python setup.py nosetests

or simply:

    nosetests

[nose]:http://somethingaboutorange.com/mrl/projects/nose/0.11.1/

Appendix
--------

* [Additional Reading][migration]
* [Additional Listening][music]

[migration]: http://en.wikipedia.org/wiki/Caribou#Migration
[music]: http://www.myspace.com/cariboumanitoba

