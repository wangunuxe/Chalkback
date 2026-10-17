# 老师控制台（负责人 C）——只用于开发和联调，数据是 contracts/examples 的 mock。
# 真实部署时控制台直接跑在老师电脑上：它要读 ~/.chalkback/、调用本机 screenpipe，并且只对本机开放老师页面。
# 构建上下文是仓库根目录：docker compose build console
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CHALKBACK_HOME=/data
WORKDIR /app

COPY console/requirements.txt console/requirements.txt
RUN pip install --no-cache-dir -r console/requirements.txt

# seed_mock_home.py 需要 contracts/examples、game.html 模板和 build_game.py
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
CMD ["sh", "-c", "python /app/tools/seed_mock_home.py --home \"$CHALKBACK_HOME\" --hub-url \"$HUB_URL\" --if-empty && exec uvicorn app.main:app --host 0.0.0.0 --port 4000 --ssl-keyfile key.pem --ssl-certfile cert.pem"]
