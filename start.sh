#!/bin/sh

# Exit on error
set -e

# Start the Tailscale daemon in the background
tailscaled &

# Bring the Tailscale interface up and log in.
# The TS_AUTHKEY is passed in as an environment variable from the docker run command.
tailscale up --authkey=${TS_AUTHKEY} --hostname=tess-classifier-prod --accept-routes

# Start the Tailscale Funnel to expose port 8000
tailscale funnel 8000 &

# Start the Waitress server in the foreground
echo "Starting Waitress server..."
waitress-serve --host=0.0.0.0 --port=8000 tess_classifier.wsgi:application