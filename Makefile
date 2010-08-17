# Copyright (C) 2003-2010, Stefan Schwarzer <sschwarzer@sschwarzer.net>
# See the file LICENSE for licensing terms.

SHELL=/bin/sh
PROJECT_DIR=/home/schwa/sd/python/ftputil
TEST_DIR=${PROJECT_DIR}/test
VERSION=$(shell cat VERSION)
DEBIAN_DIR=${PROJECT_DIR}/debian
DOC_FILES=README.html ftputil.html ftputil_ru.html
TMP_LS_FILE=tmp_ls.out
STYLESHEET_PATH=default.css
WWW_DIR=${HOME}/www
SED=sed -i'' -r -e
PYTHONPATH=${PROJECT_DIR}:${TEST_DIR}
#TODO some platforms call that script rst2html.py - allow both
RST2HTML=rst2html
CHECK_FILES=ftp_error.py ftp_file.py ftp_path.py ftp_stat_cache.py \
			ftp_stat.py ftputil.py ftputil_version.py __init__.py \
			find_deprecated_code.py
# name test files; make sure the long-running tests come last
TEST_FILES=$(shell ls -1 ${TEST_DIR}/test_*.py | \
			 grep -v "test_real_ftp.py" | \
			 grep -v "test_public_servers.py" ) \
		   ${TEST_DIR}/test_real_ftp.py \
		   ${TEST_DIR}/test_public_servers.py

.PHONY: dist extdist test pylint docs clean register patch debdistclean debdist
.SUFFIXES: .txt .html

test:
	@echo "=== Running tests for ftputil ${VERSION} ===\n"
	if which python2.4; then \
		PYTHONPATH=${PYTHONPATH} python2.4 ${TEST_DIR}/test_python2_4.py; \
	else \
		echo "Tests specific for Python 2.4 have been skipped."; \
	fi
	for file in $(TEST_FILES); \
	do \
		echo $$file ; \
		PYTHONPATH=${PYTHONPATH} python $$file ; \
	done

pylint:
	pylint --rcfile=pylintrc ${CHECK_FILES} | less

ftputil_ru.html: ftputil_ru_utf8.txt
	${RST2HTML} --stylesheet-path=${STYLESHEET_PATH} --embed-stylesheet \
		--input-encoding=utf-8 $< $@

.txt.html:
	${RST2HTML} --stylesheet-path=${STYLESHEET_PATH} --embed-stylesheet $< $@

patch:
	@echo "Patching files"
	${SED} "s/^__version__ = '.*'/__version__ = \'`cat VERSION`\'/" \
		ftputil_version.py
	${SED} "s/^:Version:   .*/:Version:   ${VERSION}/" ftputil.txt
	${SED} "s/^:Date:      .*/:Date:      `date +"%Y-%m-%d"`/" ftputil.txt
	#TODO add rules for Russian translation
	${SED} "s/^Version: .*/Version: ${VERSION}/" PKG-INFO
	${SED} "s/(\/wiki\/Download\/ftputil-).*(\.tar\.gz)/\1${VERSION}\2/" \
		PKG-INFO

docs: ${DOC_FILES} README.txt ftputil.txt ftputil_ru_utf8.txt

manifestdiff: MANIFEST
	@ls -1 | grep -v .pyc | grep -v ${TMP_LS_FILE} > ${TMP_LS_FILE}
	-diff -u MANIFEST ${TMP_LS_FILE}
	@rm ${TMP_LS_FILE}

dist: clean patch test pylint docs
	python setup.py sdist

debdistclean:
	cd ${DEBIAN_DIR} && rm -rf `ls -1 | grep -v "^custom$$"`

debdist: debdistclean
	cp dist/ftputil-${VERSION}.tar.gz \
	   ${DEBIAN_DIR}/ftputil-${VERSION}.orig.tar.gz
	tar -x -C ${DEBIAN_DIR} -zf ${DEBIAN_DIR}/ftputil-${VERSION}.orig.tar.gz
	cd ${DEBIAN_DIR}/ftputil-${VERSION} && \
	  echo "\n" | dh_make --copyright bsd --single --cdbs && \
	  cd debian && \
	  rm *.ex *.EX README.Debian
	# copy custom files (control, rules, copyright, changelog, maybe others)
	cp -r ${DEBIAN_DIR}/custom/* ${DEBIAN_DIR}/ftputil-${VERSION}/debian
	cd ${DEBIAN_DIR}/ftputil-${VERSION} && \
	  dpkg-buildpackage -us -uc
	# put the Debian package beneath the .tar.gz files
	cp ${DEBIAN_DIR}/python-ftputil_${VERSION}_all.deb dist
	# final check (better than nothing)
	lintian --info ${DEBIAN_DIR}/python-ftputil_${VERSION}_all.deb

localcopy:
	@echo "Copying archive and documentation to local webspace"
	cp -p dist/ftputil-${VERSION}.tar.gz ${WWW_DIR}/download
	cp -p ftputil.html ${WWW_DIR}/python
	touch ${WWW_DIR}/python/python_software.tmpl

register:
	@echo "Registering new version with PyPI"
	python setup.py register

extdist: test dist debdist localcopy register

clean:
	rm -f ${DOC_FILES}
# use absolute path to ensure we delete the right directory
	rm -rf ${PROJECT_DIR}/build

