#!/bin/sh
set -eu
BACKEND_HOST=${BACKEND_HOST:-backend}
BACKEND_PORT=${BACKEND_PORT:-8000}
case "$BACKEND_HOST" in ''|*[!a-zA-Z0-9.-]*) echo 'Invalid BACKEND_HOST' >&2; exit 1;; esac
case "$BACKEND_PORT" in ''|*[!0-9]*) echo 'Invalid BACKEND_PORT' >&2; exit 1;; esac
[ "$BACKEND_PORT" -ge 1 ] && [ "$BACKEND_PORT" -le 65535 ] || exit 1
# Use the container's own DNS, including Railway's private resolver.
NGINX_RESOLVER=$(awk '$1 == "nameserver" { if ($2 ~ /:/) printf "[%s] ", $2; else printf "%s ", $2 }' /etc/resolv.conf)
[ -n "$NGINX_RESOLVER" ] || exit 1
export BACKEND_HOST BACKEND_PORT NGINX_RESOLVER
envsubst '${BACKEND_HOST} ${BACKEND_PORT} ${NGINX_RESOLVER}' < /etc/nginx/radar.conf.template > /etc/nginx/conf.d/default.conf
