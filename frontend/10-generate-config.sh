#!/bin/sh
set -eu

cat > /usr/share/nginx/html/config.js <<EOF
window.API_BASE = "${API_BASE:-}";
EOF