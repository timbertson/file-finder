package:
	mkzero-gfxmonk -p finder -p file_finder -v `cat VERSION` file-finder.xml

pypi:
	python ./setup.py sdist upload

