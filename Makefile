
.PHONY: *

test:
	tox
	./tests/test_cli.sh

clean:
	rm -rf build dist __pycache__

lint:
	flake8 caribou

build:
	flit build

install:
	flit install

publish:
	flit publish

all:	clean test lint
