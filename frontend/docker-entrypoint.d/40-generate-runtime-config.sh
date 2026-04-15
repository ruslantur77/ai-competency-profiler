#!/bin/sh
set -eu

API_BASE_URL="${FRONTEND_API_BASE_URL:-/api/v1}"
export API_BASE_URL

envsubst '${API_BASE_URL}' \
  < /etc/nginx/templates/config.js.template \
  > /usr/share/nginx/html/config.js
