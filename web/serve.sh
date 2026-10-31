#!/bin/sh
# Serves the NEMATICA research site at http://localhost:8642 (or the port given as $1)
cd "$(dirname "$0")" && python3 -m http.server "${1:-8642}"
