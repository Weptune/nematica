#!/bin/sh
# Serves the NEMATICA research site at http://localhost:8642 (or the port given as $1),
# with the brain-likeness test at /test/.
cd "$(dirname "$0")/.." || exit 1
PORT="${1:-8642}"
if python3 -c "import fastapi, uvicorn, scipy, onnxruntime" 2>/dev/null; then
  exec python3 -m nematica.brainlike.web.site "$PORT"
fi
echo "The brain-likeness test needs a few packages: python3 -m pip install -r deploy/brainlike/requirements.txt"
echo "Serving the research site without the test for now."
exec python3 -m http.server "$PORT" -d web
