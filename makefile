.PHONY: test install clean

test:
	coverage run --include=stengel/* -m unittest discover -s test/; \
    coverage report

install:
	cp -r stengel/ ~/.local/lib/python2.7/site-packages

clean:
	rm -r ~/.local/lib/python2.7/site-packages/stengel
