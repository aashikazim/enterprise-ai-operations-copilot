FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip==26.2.0 && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 copilot \
    && mkdir -p /home/copilot/.cache/huggingface \
    && chown -R copilot:copilot /app /home/copilot/.cache
ENV HF_HOME=/home/copilot/.cache/huggingface
USER copilot

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
