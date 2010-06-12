VERSION=0.1.11
NAME=file-finder
BASE=http://gfxmonk.net/dist/0install/$(NAME)
feed=$(NAME).xml
WEBDEST=~/Sites/gfxmonk/dist/0install/
BUILD=0inst

package:
	tar czf $(BUILD)/$(NAME)-$(VERSION).tgz finder file_finder
	if fgrep '$(VERSION)' $(feed) | fgrep 'archive'; then echo "need a new version?"; exit 1; fi
	0publish $(feed) \
		--set-version=$(VERSION) \
		--archive-url="$(BASE)/$(NAME)-$(VERSION).tgz" \
		--archive-file="$(BUILD)/$(NAME)-$(VERSION).tgz" \
		--set-released=today

copy:
	mkdir -p $(WEBDEST)/$(NAME)
	cp $(feed) $(WEBDEST)/
	cp $(BUILD)/$(NAME)-$(VERSION).tgz $(WEBDEST)/$(NAME)/
	0publish $(WEBDEST)/$(feed) --xmlsign
	make sync

upload:
	make sync
	(cd ~/Sites/gfxmonk && make upload)

sync:
	(cd ~/Sites/gfxmonk && rsync -r --delete dist _site/)

pypi:
	sed -e 's/__version__/$(VERSION)/' setup.py > setup_versioned.py
	python ./setup_versioned.py sdist upload
	rm ./setup_versioned.py

0: package copy upload
