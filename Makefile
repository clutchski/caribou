
test:
	tox

.PHONY: clean
clean:
	rm -rf build dist __pycache__

build:
	flit build

install:
	flit install

.PHONY: test_shell
test_cli:
	flit install --symlink
	./tests/test_cli.sh


.PHONY: all
all:	clean test_cli test 

publish:
	flit publish
