#!/bin/sh
# Put the calibration references on the board the first time, then serve.
set -e
if [ ! -f "$BRAINLIKE_DATA/brainlike.sqlite" ]; then
  BRAINLIKE_NO_QUEUE=1 python /app/scripts/seed_brainlike_board.py /app/nematica/brainlike/calibration
fi
exec uvicorn nematica.brainlike.web.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" --workers 1
