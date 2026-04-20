FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN addgroup --system app && adduser --system --ingroup app app
USER app

CMD ["python", "-m", "albion_analytics.scripts.collect_events"]
