FROM python:3.12-slim
WORKDIR /app
COPY requirements-dev.lock pyproject.toml ./
RUN python -m pip install --no-cache-dir -r requirements-dev.lock
COPY radar ./radar
COPY migrations ./migrations
COPY alembic.ini ./
RUN python -m pip install --no-deps --no-build-isolation .
RUN useradd --create-home radar && mkdir -p /app/data /app/backups && chown -R radar:radar /app
USER radar
EXPOSE 8000
CMD ["sh", "-c", "python -m radar.cli init-db && python -m uvicorn radar.main:app --host 0.0.0.0 --port 8000"]
