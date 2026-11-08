#!/bin/sh
# Put the calibration references on the board (idempotent: rewrites the reference entries each start), then serve.
set -e
BRAINLIKE_NO_QUEUE=1 python /app/scripts/seed_brainlike_board.py /app/nematica/brainlike/calibration
exec uvicorn nematica.brainlike.web.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" --workers 1
