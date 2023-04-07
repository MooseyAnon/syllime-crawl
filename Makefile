PYTHON := python3
current_dir := $(shell pwd)

check: check-coding-standards check-tests

check-coding-standards: check-pycodestyle check-pylint-main

check-pycodestyle: venv
	venv/bin/python -m pycodestyle sylli_crawl crawl

check-pylint-main: venv
	venv/bin/python -m pylint sylli_crawl crawl

check-isort: venv
	venv/bin/python -m isort sylli_crawl crawl --check --diff --skip venv

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

.PHONY: check check-coding-standards check-pylint-main check-isort \
	check-tests venv
