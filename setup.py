#!/usr/bin/env python

import sys
import os.path
from distutils.core import setup

NAME = 'caribou'
VERSION = '0.1'
DESC = "python migrations for sqlite databases"
LONG_DESC = DESC
AUTHOR = 'clutchski'
EMAIL = 'clutchski@gmail.com'
URL = 'http://github.com/clutchski/caribou'
LICENSE = 'Public Domain'

if sys.version_info < (2,5):
    raise NotImplementedError("Sorry, you need at least Python 2.5 to use caribou")

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
