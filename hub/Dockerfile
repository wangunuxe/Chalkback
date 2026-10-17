# 学校 Hub（负责人 D）。构建上下文是仓库根目录：docker compose build hub
FROM python:3.13-slim

# 不设置 HUB_MOCK_AUTH：镜像默认是正式模式（不接受 mock token、没有 DEMO-* 邀请码，邀请码用 HUB_INVITES 设置）。
# 本机联调由 docker-compose.yml 打开联调模式。
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HUB_DB=/data/chalkback.db
WORKDIR /app

COPY hub/requirements.txt hub/requirements.txt
RUN pip install --no-cache-dir -r hub/requirements.txt

# app/mock.py 在 TD1 阶段读取 contracts/examples
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
