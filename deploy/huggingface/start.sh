#!/bin/bash
# Starts the gateway, the console and the proxy; the Space stops when any of them stops, so
# Hugging Face restarts it instead of serving a half-working platform.
set -e

cd /platform/server
node dist/main.js &

cd /platform/collateral-engine
# The Space serves the app inside an iframe, where Streamlit's XSRF cookie breaks photo uploads.
streamlit run app/platform_app.py --server.port=8501 --server.address=127.0.0.1 \
    --server.enableXsrfProtection=false &

nginx -e /dev/stderr -c /etc/nginx/space.conf -g 'daemon off;' &

wait -n
exit 1
