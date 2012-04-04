#!/usr/bin/env python

## NOTE: ##
## setup.py is not maintained, and is only provided for convenience.
## please see http://gfxmonk.net/dist/0install/index/ for
## up-to-date installable packages.

from setuptools import *

setup(
	name='file-finder',
	version='0.2',
	description='find and open files quickly',
	author='Tim Cuthbertson',
	author_email='tim3d.junk+findfiles@gmail.com',
	url='http://gfxmonk.net/dist/0install/file-finder.xml',
	packages=find_packages(exclude=["test"]),
	
	classifiers=[
		"License :: OSI Approved :: BSD License",
		"Programming Language :: Python",
		"Development Status :: 4 - Beta",
	],
	keywords='file find index search quick open',
	license='GPLv2',
	scripts=['finder'],
	install_requires=[
		'setuptools',
	],
)
