# School Hub (owner: D). The build context is the repo root: docker compose build hub
FROM python:3.13-slim

# HUB_MOCK_AUTH is not set: the image defaults to production mode (no mock tokens, no DEMO-* invite codes; invite codes are set with HUB_INVITES).
# Local testing turns on test mode via docker-compose.yml.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HUB_DB=/data/chalkback.db
WORKDIR /app

COPY hub/requirements.txt hub/requirements.txt
RUN pip install --no-cache-dir -r hub/requirements.txt

# app/mock.py reads contracts/examples during the TD1 phase
COPY contracts contracts
COPY hub hub

RUN python hub/generate_cert.py

RUN useradd --create-home chalkback && mkdir /data && chown -R chalkback:chalkback /app /data
USER chalkback
VOLUME /data
WORKDIR /app/hub
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import ssl, urllib.request; ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE; urllib.request.urlopen('https://127.0.0.1:8000/docs', context=ctx)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]
