SHELL := /bin/bash

GO ?= go

ROOT := $(CURDIR)
TOOLS_DIR := $(ROOT)/.tools

GOCACHE ?= $(TOOLS_DIR)/gocache
GOPATH ?= $(TOOLS_DIR)/gopath
GOMODCACHE ?= $(GOPATH)/pkg/mod
GOBIN ?= $(TOOLS_DIR)/bin

export GOCACHE
export GOPATH
export GOMODCACHE
export GOBIN

SERVICES := gateway ingest agent model-gateway

.PHONY: help env fmt tidy vet test check build clean run-gateway run-ingest run-agent run-model-gateway

help:
	@echo "GroundedKB Go services"
	@echo "  make env        print Go environment exports"
	@echo "  make fmt        run gofmt on all packages"
	@echo "  make tidy       run go mod tidy"
	@echo "  make vet        run go vet"
	@echo "  make test       run go test"
	@echo "  make check      run vet + test"
	@echo "  make build      build service binaries into bin/"
	@echo "  make run-gateway / run-ingest / run-agent / run-model-gateway"
	@echo "  make clean      remove bin/"

env:
	@echo "export GOCACHE=$(GOCACHE)"
	@echo "export GOPATH=$(GOPATH)"
	@echo "export GOMODCACHE=$(GOMODCACHE)"
	@echo "export GOBIN=$(GOBIN)"

fmt:
	$(GO) fmt ./...

tidy:
	$(GO) mod tidy

vet:
	$(GO) vet ./...

test:
	$(GO) test ./...

check: vet test

build:
	@mkdir -p bin
	@for svc in $(SERVICES); do \
		echo "building $$svc"; \
		$(GO) build -trimpath -o bin/$$svc ./services/$$svc/cmd/$$svc || exit 1; \
	done

run-gateway:
	$(GO) run ./services/gateway/cmd/gateway

run-ingest:
	$(GO) run ./services/ingest/cmd/ingest

run-agent:
	$(GO) run ./services/agent/cmd/agent

run-model-gateway:
	$(GO) run ./services/model-gateway/cmd/model-gateway

clean:
	rm -rf bin
