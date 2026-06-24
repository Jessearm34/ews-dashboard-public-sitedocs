FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY visualize_fasthtml/requirements.txt ./visualize_fasthtml-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r visualize_fasthtml-requirements.txt

COPY src ./src
COPY config ./config
COPY visualize_fasthtml ./visualize_fasthtml
COPY refresh.py ./refresh.py
COPY database ./database
COPY startup.sh ./startup.sh

RUN mkdir -p /app/output && chmod +x /app/startup.sh

EXPOSE 5001

CMD ["/app/startup.sh"]
