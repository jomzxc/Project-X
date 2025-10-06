#!/bin/sh

# Exit on error
set -e

echo "Running database migrations..."
python manage.py migrate

# Start the Tailscale daemon in the background.
tailscaled &

sleep 3

# Bring the Tailscale interface up and log in.
tailscale up --authkey=${TS_AUTHKEY} --hostname=tess-classifier-prod --accept-routes

TS_DNS_NAME=$(/usr/bin/tailscale status --json | jq -r .Self.DNSName | sed 's/\.$//')

CSRF_ORIGIN="https://${TS_DNS_NAME}"
export CSRF_ORIGIN


echo "Found Tailscale DNS Name: ${TS_DNS_NAME}"
echo "Setting CSRF_TRUSTED_ORIGINS to: ${CSRF_ORIGIN}"

# Start the Tailscale Funnel to expose port 8000.
tailscale funnel 8000 &

# Start the Waitress server in the foreground.
echo "Starting Waitress server on 0.0.0.0:8000"
python -m waitress --host=0.0.0.0 --port=8000 tess_classifier.wsgi:application