#!/bin/sh
# Serves the NEMATICA research site at http://localhost:8000
cd "$(dirname "$0")" && python3 -m http.server 8000
