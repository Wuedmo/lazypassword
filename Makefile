.PHONY: build install test clean

BINARY=lazypassword
PREFIX=/usr/local/bin

build:
	go build -o $(BINARY) .

install: build
	cp $(BINARY) $(PREFIX)/

test:
	go test ./...

clean:
	rm -f $(BINARY)
