# The brain-likeness website. Build from the repository root:
#   docker build -f deploy/brainlike/Dockerfile -t brainlike .
#   docker run -d -p 8000:8000 -v brainlike-data:/data --name brainlike brainlike
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    BRAINLIKE_DATA=/data BRAINLIKE_WORKERS=1 BRAINLIKE_TIMEOUT=1800 BRAINLIKE_MEMORY_MB=4096
WORKDIR /app
COPY deploy/brainlike/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY pyproject.toml README.md LICENSE /app/
COPY nematica /app/nematica
COPY scripts/seed_brainlike_board.py /app/scripts/seed_brainlike_board.py
COPY deploy/brainlike/start.sh /app/start.sh
RUN useradd --create-home --uid 10001 brainlike \
    && mkdir -p /data && chown brainlike /data && chmod +x /app/start.sh
USER brainlike
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["/app/start.sh"]
