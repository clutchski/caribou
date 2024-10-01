
.PHONY: *

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

publish:
	flit publish

fmt:
	black caribou tests

all:	clean test fmt lint
