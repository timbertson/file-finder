#!/usr/bin/env python

from setuptools import *

setup(
	name='file-finder',
	version='0.1.14',
	description='find and open files quickly',
	author='Tim Cuthbertson',
	author_email='tim3d.junk+findfiles@gmail.com',
	url='http://github.com/gfxmonk/find-files',
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
