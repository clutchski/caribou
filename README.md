Caribou SQLite Migrations
====================

Caribou is a simple [Python][python] [migrations][rails] library for [SQLite][sqlite]
databases. It is built to manage the evoluton of client side databases over
multiple releases of an application.

  [rails]:http://guides.rubyonrails.org/migrations.html 
  [python]: http://python.org/
  [sqlite]: http://sqlite.ord

Example
-------

#### Create a migration

caribou create [-d DIRECTORY] MIGRATION_NAME

#### Add your schema changes

    """
    an example of a caribou migration file
    """
    
    def upgrade(connection):
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
        sql = 'insert into animals values (:1, :2)
        for name, status in animals:
            connection.execute(sql, [name, status])
    
        connection.commit()
    
    def downgrade(connection):
        connection.execute('drop table animals')

#### Run your migrations:

    """
    an example illustrating how to run a caribou migration
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

or, to install trunk:

    sudo python setup.py install

Licence
-------------

    Caribou is in the public domain.

