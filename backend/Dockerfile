FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system app && adduser --system --ingroup app app

COPY --chown=app:app app ./app
RUN mkdir -p /app/reports && chown -R app:app /app/reports

ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1

USER app
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
