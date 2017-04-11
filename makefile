.PHONY: test install clean

test:
	python -m unittest discover -s test/ -v

install:
	cp -r stengel/ ~/.local/lib/python2.7/site-packages

clean:
	rm -r ~/.local/lib/python2.7/site-packages/stengel
