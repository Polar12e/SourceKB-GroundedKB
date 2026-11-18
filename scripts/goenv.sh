#!/usr/bin/env bash
# Source this file from anywhere in the repo to keep Go caches inside the workspace.
# Usage: source scripts/goenv.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export GOCACHE="${GOCACHE:-$ROOT/.tools/gocache}"
export GOPATH="${GOPATH:-$ROOT/.tools/gopath}"
export GOMODCACHE="${GOMODCACHE:-$GOPATH/pkg/mod}"
export GOBIN="${GOBIN:-$ROOT/.tools/bin}"
export PATH="$GOBIN:$PATH"
