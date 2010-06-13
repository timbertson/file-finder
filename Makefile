VERSION=0.1.11
NAME=file-finder
BUILD=0inst

package:
	tar czf $(BUILD)/$(NAME)-$(VERSION).tgz finder file_finder
	0publish-gfxmonk $(NAME) $(VERSION)

pypi:
	sed -e 's/__version__/$(VERSION)/' setup.py > setup_versioned.py
	python ./setup_versioned.py sdist upload
	rm ./setup_versioned.py

