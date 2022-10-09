PYTHON := python3
current_dir := $(shell pwd)

check: check-coding-standards check-tests

check-coding-standards: check-pycodestyle check-pylint-main

check-pycodestyle: venv
	venv/bin/python -m pycodestyle sylli_crawl crawl

check-pylint-main: venv
	venv/bin/python -m pylint sylli_crawl crawl

check-tests: venv
	venv/bin/python -m pytest -v

requirements.txt: | requirements.in
	$(PYTHON) -m piptools compile --output-file $@ $<

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	test -d venv || $(PYTHON) -m venv venv
	# we need this version of pip to work with piptools
	venv/bin/python -m pip install pip==20.0.2
	# install piptools
	venv/bin/python -m pip install pip-tools
	venv/bin/python -m pip install -r $< --progress-bar off
	touch $@

.PHONY: check check-coding-standards check-pylint-main check-tests venv
