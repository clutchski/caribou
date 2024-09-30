
test:
	tox

.PHONY: clean
clean:
	rm -rf build dist __pycache__

build:
	flit build

install:
	flit install

