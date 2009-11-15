Caribou SQLite Migrations
====================

<div style="left: right; padding: 0px 0px 2em 2em">
    <img src="http://imgur.com/DySrz.jpg" alt="Caribou" />
</div>

Caribou is a simple [Python][python] library for library for [SQLite][sqlite]
database [migrations][rails]. built primarily to manage the evoluton of client
side databases over multiple releases of an application.

  [rails]:http://guides.rubyonrails.org/migrations.html 
  [python]: http://python.org/
  [sqlite]: http://sqlite.ord

Example
-------

#### Create a migration

run from the command line:

    > caribou create [-d DIRECTORY] my_first_migration
    "created migration 20091114190521_my_first_migration.py"

#### update your newly created migration file 

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

#### Run your migrations:

    """
    an example illustrating how to run a migration programmatically.
    """
    
    import caribou
    
    db_path = '/path/to/db.sqlite3'
    migrations_path = '/path/to/migrations/dir'
    version = '20091114132332'
    
    # upgrade to most recent version
    caribou.upgrade(db_version, migrations_path)
    
    # upgrade to a specific version
    caribou.upgrade(db_path, migrations_path, version)
    
    # downgrade to a specific version
    caribou.downgrade(db_path, migrations_path, version)

That's it.

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

Appendix
--------

* [Additional Reading][migration]
* [Additional Listening][music]

[migration]: http://en.wikipedia.org/wiki/Caribou#Migration
[music]: http://www.myspace.com/cariboumanitoba

