# Teacher console (owner: C) -- only for development and test mode. It starts empty ("Not set up yet");
# `make mock` fills /data with the mock from contracts/examples (tools/seed_mock_home.py).
# In a real deployment the console runs directly on the teacher's computer: it reads ~/.chalkback/, calls the local screenpipe, and serves the teacher pages to this machine only.
# The build context is the repo root: docker compose build console
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CHALKBACK_HOME=/data
WORKDIR /app

COPY console/requirements.txt console/requirements.txt
RUN pip install --no-cache-dir -r console/requirements.txt

# seed_mock_home.py needs contracts/examples, the game.html template and build_game.py
COPY contracts contracts
COPY pipe/templates pipe/templates
COPY pipe/scripts pipe/scripts
COPY tools tools
COPY console console

RUN python console/generate_cert.py

RUN useradd --create-home chalkback && mkdir /data && chown -R chalkback:chalkback /app /data
USER chalkback
VOLUME /data
WORKDIR /app/console
EXPOSE 4000

ENV HUB_URL=https://hub:8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]
