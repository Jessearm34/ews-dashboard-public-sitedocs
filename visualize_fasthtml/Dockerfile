FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
COPY visualize_fasthtml/requirements.txt ./visualize_fasthtml-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r visualize_fasthtml-requirements.txt

COPY src ./src
COPY config ./config
COPY visualize_fasthtml ./visualize_fasthtml
COPY refresh.py ./refresh.py
COPY database ./database
ENV PYTHONPATH=/app
EXPOSE 5001

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker visualize_fasthtml.app:app --bind 0.0.0.0:${PORT:-5001} --workers 2 --timeout 120"]
