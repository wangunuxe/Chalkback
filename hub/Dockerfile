# 学校 Hub（负责人 D）。构建上下文是仓库根目录：docker compose build hub
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HUB_DB=/data/chalkback.db
WORKDIR /app

COPY hub/requirements.txt hub/requirements.txt
RUN pip install --no-cache-dir -r hub/requirements.txt

# app/mock.py 在 TD1 阶段读取 contracts/examples
COPY contracts contracts
COPY hub hub

RUN useradd --create-home chalkback && mkdir /data && chown chalkback /data
USER chalkback
VOLUME /data
WORKDIR /app/hub
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
