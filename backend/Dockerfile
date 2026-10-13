FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY modules/2.2-collector/requirements.txt ./collector-requirements.txt
RUN pip install -r requirements.txt -r collector-requirements.txt && groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home appuser
COPY app ./app
COPY ai ./ai
COPY database ./database
COPY scraper ./scraper
COPY workers ./workers
COPY modules/2.2-collector ./modules/2.2-collector
COPY alembic.ini ./alembic.ini
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
