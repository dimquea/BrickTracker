#!/usr/bin/env bash

set -a
source .env
set +a

gunicorn --bind "0.0.0.0:3334" "wsgi:application" --worker-class "gevent" --workers 1 --reload "$@"
