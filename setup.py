#!/usr/bin/env python

import os.path
from setuptools import setup

NAME = 'caribou'
VERSION = '0.3.0'
DESC = "python migrations for sqlite databases"
LONG_DESC = """\
Caribou is a simple SQLite database migrations library, built primarily
to manage the evoluton of client side databases over multiple releases 
of an application.
"""
AUTHOR = 'clutchski'
EMAIL = 'clutchski@gmail.com'
URL = 'http://github.com/clutchski/caribou'
LICENSE = 'Public Domain'

setup( name = NAME
     , version = VERSION
     , description = DESC
     , long_description = LONG_DESC
     , author = AUTHOR
     , author_email = EMAIL
     , url = URL
     , license = LICENSE
     , platforms = 'any'
     , py_modules=['caribou']
     , scripts=['bin/caribou']
     , install_requires=["argparse>=1.0.0"]
     , classifiers=\
         [ 'Development Status :: 4 - Beta'
         , 'Intended Audience :: Developers'
         , 'License :: Public Domain'
         , 'Topic :: Database'
         , 'Topic :: Software Development :: Version Control'
         , 'Topic :: Software Development :: Build Tools'
         , 'Programming Language :: Python :: 2.6'
         , 'Programming Language :: Python :: 2.5'
         ]
     )
