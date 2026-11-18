SHELL := /bin/bash

GO ?= go
PYTHON ?= $(ROOT)/.venv/bin/python
VENV ?= $(ROOT)/.venv
PIP_INDEX_URL ?= https://mirrors.aliyun.com/pypi/simple/
PIP_CACHE_DIR ?= $(ROOT)/.tools/pip

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
export PIP_INDEX_URL
export PIP_CACHE_DIR

SERVICES := gateway ingest agent model-gateway

.PHONY: help env fmt tidy vet test check build clean run-gateway run-ingest run-agent run-model-gateway \
	py-install py-test contracts test-all check-all compose-config py-run-retrieval ci

help:
	@echo "GroundedKB development commands"
	@echo "  Go:"
	@echo "    make env        print Go environment exports"
	@echo "    make fmt        run gofmt on all packages"
	@echo "    make tidy       run go mod tidy"
	@echo "    make vet        run go vet"
	@echo "    make test       run go test"
	@echo "    make build      build service binaries into bin/"
	@echo "    make run-gateway / run-ingest / run-agent / run-model-gateway"
	@echo "  Python:"
	@echo "    make py-install install Python dev dependencies into .venv/"
	@echo "    make py-test    run retrieval worker tests"
	@echo "    make contracts  validate JSON Schema / OpenAPI examples"
	@echo "    make py-run-retrieval"
	@echo "  Combined:"
	@echo "    make test-all   go test + py-test + contracts"
	@echo "    make check-all  go vet + test-all + compose-config"
	@echo "    make compose-config  validate deploy/compose.yaml"
	@echo "  Cleanup:"
	@echo "    make clean      remove bin/"

env:
	@echo "export GOCACHE=$(GOCACHE)"
	@echo "export GOPATH=$(GOPATH)"
	@echo "export GOMODCACHE=$(GOMODCACHE)"
	@echo "export GOBIN=$(GOBIN)"
	@echo "export PIP_INDEX_URL=$(PIP_INDEX_URL)"
	@echo "export PIP_CACHE_DIR=$(PIP_CACHE_DIR)"

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

py-install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements-dev.txt

py-test:
	$(PYTHON) -m pytest workers/retrieval/tests

contracts:
	$(PYTHON) scripts/check_contracts.py

py-run-retrieval:
	$(PYTHON) -m uvicorn workers.retrieval.app:app --host 0.0.0.0 --port 8081

compose-config:
	docker compose -f deploy/compose.yaml config >/dev/null
	@echo "compose config OK"

test-all: test py-test contracts

check-all: check test-all compose-config

ci: check-all

clean:
	rm -rf bin
