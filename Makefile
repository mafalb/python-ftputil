# Copyright (C) 2003-2004, Stefan Schwarzer
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# - Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# - Neither the name of the above author nor the names of the
#   contributors to the software may be used to endorse or promote
#   products derived from this software without specific prior written
#   permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# $Id: Makefile,v 1.11 2004/02/27 23:41:46 schwa Exp $


SHELL=/bin/sh
PROJECT_DIR=/home/schwa/sd/python/ftputil
DOC_FILES=README.html ftputil.html

.PHONY: dist extdist test docs clean register patch
.SUFFIXES: .txt .html

test:
	for file in `ls _test_*.py`; \
	do \
		python $$file ; \
	done

.txt.html:
	rst2html.py \
	--stylesheet-path=/usr/opt/docutils/stylesheets/default.css \
	--embed-stylesheet $< $@

patch:
	@echo "Patching files"
	sed -i'' -E -e "s/^__version__ = '.*'/__version__ = \'`cat VERSION`\'/" ftputil.py
	sed -i'' -E -e "s/^:Version:   .*/:Version:   `cat VERSION`/" ftputil.txt
	sed -i'' -E -e "s/^:Date:      .*/:Date:      `date +"%Y-%m-%d"`/" ftputil.txt

docs: ${DOC_FILES} README.txt ftputil.txt

dist: clean patch docs
	python setup.py sdist

localcopy:
	@echo "Copying archive and documentation to local webspace"
	cp -p dist/ftputil-`cat VERSION`.tar.gz ${HOME}/www/download
	cp -p ftputil.html ${HOME}/www/python

register:
	@echo "Registering new version with PyPI"
	python setup.py register

extdist: test dist localcopy register

clean:
	rm -f ${DOC_FILES}
# use absolute path to ensure we delete the right directory
	rm -rf ${PROJECT_DIR}/build

