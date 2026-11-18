# syntax=docker/dockerfile:1

FROM golang:1.27-alpine AS build

WORKDIR /src

COPY go.mod ./
RUN go mod download

COPY . .

ARG SERVICE
RUN test -n "$SERVICE" && \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" \
    -o /out/service "./services/${SERVICE}/cmd/${SERVICE}"

FROM alpine:3.20

RUN apk add --no-cache ca-certificates

COPY --from=build /out/service /service

USER 65532:65532

ENTRYPOINT ["/service"]
