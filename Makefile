
.PHONY: *

check:	clean fmtcheck lint test

deps:
	# install build dependences
	pip install tox flake8 black

test:
	tox
	./tests/test_cli.sh

clean:
	rm -rf build dist __pycache__

flake8:
	flake8 caribou tests

lint: flake8

build:
	flit build

install:
	flit install

publish: check
	flit publish

fmt:
	black caribou tests

fmtcheck:
	black --check caribou tests
