VERSION=0.0.0
BUILD=1

PYTHON=$(shell which python2.7 || which python27 || which python2.6 || which python26 || which python)
PYTHON_VERSION=$(shell ${PYTHON} -c "from distutils.sysconfig import get_python_version; print(get_python_version())")

prefix=/usr/local
bindir=${prefix}/bin
libdir=${prefix}/lib
pydir=$(shell ${PYTHON} pydir.py ${libdir})
mandir=${prefix}/share/man

all:

clean:
	rm -rf \
		control *.deb \
		setup.py build dist *.egg *.egg-info \
		blueprint/**.pyc \
		man/man*/*.html

install: install-lib install-man

install-lib:
	install -d $(DESTDIR)$(pydir)/blueprint_io
	install -m644 \
		blueprint_io/__init__.py \
		$(DESTDIR)$(pydir)/blueprint_io
	PYTHONPATH=$(DESTDIR)$(pydir) $(PYTHON) -mcompileall \
		$(DESTDIR)$(pydir)/blueprint_io

install-man:
	install -d $(DESTDIR)$(mandir)/man7
	install -m644 man/man7/blueprint-io.7 $(DESTDIR)$(mandir)/man7/

uninstall: uninstall-lib uninstall-man

uninstall-lib:
	rm -f \
		$(DESTDIR)$(pydir)/blueprint_io/__init__.py \
		$(DESTDIR)$(pydir)/blueprint_io/__init__.pyc \
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(pydir)/blueprint_io

uninstall-man:
	rm -f $(DESTDIR)$(mandir)/man7/blueprint-io.7
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(mandir)/man7

build:
	sudo make deb
	make pypi

deb:
	[ "$$(whoami)" = "root" ] || false
	m4 \
		-D__PYTHON__=python$(PYTHON_VERSION) \
		-D__VERSION__=$(VERSION)-$(BUILD) \
		control.m4 >control
	debra create debian control
	make install prefix=/usr DESTDIR=debian
	chown -R root:root debian
	debra build debian blueprint-io_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb
	debra destroy debian

setup.py:
	m4 -D__VERSION__=$(VERSION) setup.py.m4 >setup.py

pypi: setup.py
	$(PYTHON) setup.py bdist_egg

deploy: deploy-deb deploy-pypi

deploy-deb:
	scp -i ~/production.pem blueprint-io_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb ubuntu@packages.devstructure.com:
	make deploy-deb-$(PYTHON_VERSION)
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "rm blueprint_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"

deploy-deb-2.6:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight add blueprint-io_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb apt/lucid apt/maverick apt/squeeze && sudo freight cache apt/lucid apt/maverick apt/squeeze"

deploy-deb-2.7:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight add blueprint-io_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb apt/natty && sudo freight cache apt/natty"

deploy-pypi:
	$(PYTHON) setup.py sdist upload

man:
	find man -name \*.ronn | xargs -n1 ronn \
		--manual="Blueprint I/O" --organization=DevStructure --style=toc

gh-pages: man
	mkdir -p gh-pages
	find man -name \*.html | xargs -I__ mv __ gh-pages/
	git checkout -q gh-pages
	cp -R gh-pages/* ./
	rm -rf gh-pages
	git add .
	git commit -m "Rebuilt manual."
	git push origin gh-pages
	git checkout -q master

.PHONY: all build clean install install-lib install-man uninstall uninstall-lib uninstall-man deb deploy deploy-deb deploy-deb-2.6 deploy-deb-2.7 deploy-pypi man gh-pages
